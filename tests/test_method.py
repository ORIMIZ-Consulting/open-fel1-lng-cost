"""Checks of each guideline step on small hand-made analog sets."""
import math

import numpy as np
import opci
import pandas as pd
import pytest
from opci.index import SUPPLY_SHOCK_NOTE

from fel1_lng_cost import (
    BrownfieldShares, Method, SiteItem, choose_base, compare_options, escalation_factor,
    escalation_source, opci_link,
    estimate, load_analogs, make_basis, tank_cost,
)
from fel1_lng_cost import factors as F
from fel1_lng_cost.analogs import check_analogs

BASE_ROW = dict(
    id="a1", project="Analog 1", country="USA", region="North America", location_code="US-GC",
    facility_type="onshore_liquefaction", site_type="greenfield", trains=1,
    capacity_mtpa=5.0, train_size_mtpa="", fid_year=2020, cost_year=2020, cost_amount_million=5000,
    currency="USD", fx_to_usd=1.0, cost_basis="budget", scope="plant_only",
    plant_only_amount_million="", split_source="", liquids_scope="lean", gas_adjust="yes",
    co2_sequestration="no", process_family="c3mr", epc_contractor="Builder", contracting_basis="lump_sum",
    contingency_status="budget", data_quality="A", source_url="https://example.com", notes="",
)


def analogs(tmp_path, *overrides):
    rows = []
    for i, o in enumerate(overrides):
        row = dict(BASE_ROW, id=f"a{i + 1}", project=f"Analog {i + 1}")
        row.update(o)
        rows.append(row)
    path = tmp_path / "private_test.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return load_analogs(path, include_public=False)


def basis(**kw):
    kw.setdefault("estimate_date", "2020")
    kw.setdefault("min_count_stop", 1)
    kw.setdefault("min_count_warn", 1)
    kw.setdefault("definition_growth", (0.0, 0.0))
    return make_basis(**kw)


def central_unit(res):
    return res.central / res.basis.capacity_mtpa


# ------------------------------------------------------------- Step 2
def test_filters_record_a_reason(tmp_path):
    df = analogs(tmp_path, {}, {"fid_year": 2000, "cost_year": 2000}, {"capacity_mtpa": 20.0},
                 {"scope": "integrated_upstream"}, {"scope": "integrated_upstream", "plant_only_amount_million": 4000})
    res = estimate(df, basis())
    notes = dict(zip(res.pool["id"], res.pool["selection_note"]))
    assert notes["a1"] == ""
    assert notes["a2"].startswith("FID before")
    assert notes["a3"].startswith("Train size outside")
    assert notes["a4"].startswith("Scope")
    assert notes["a5"] == ""  # integrated, but a plant split exists


def test_cluster_rule_for_large_trains(tmp_path):
    df = analogs(tmp_path, {"capacity_mtpa": 7.0}, {"capacity_mtpa": 5.0})
    res = estimate(df, basis(train_size_mtpa=7.5))
    notes = dict(zip(res.pool["id"], res.pool["selection_note"]))
    assert notes["a1"] == "" and "cluster" in notes["a2"]
    assert any("outside 1 to 6 MTPA" in w for w in res.warnings)


def test_minimum_count_stops(tmp_path):
    df = analogs(tmp_path, {})
    with pytest.raises(ValueError, match="minimum"):
        estimate(df, basis(min_count_stop=3))


# ------------------------------------------------------------- Step 4
def opci_ratio(base, target, release=None, freq="annual", base_freq="annual"):
    def rows(f):
        return {r["period"]: r["value"] for r in opci.read_release(release or opci_link.latest_release(), f)["rows"]}
    return rows(freq)[str(target)] / rows(base_freq)[str(base)]


def test_escalation_methods():
    b = make_basis(escalation_rate=0.03, cost_index={2015: 100.0, 2025: 150.0})
    assert escalation_factor(2015, 2017, "constant", b) == pytest.approx(1.03 ** 2)
    assert escalation_factor(2015, 2025, "index", b) == pytest.approx(1.5)
    assert escalation_factor(2015, 2025, "opci", b) == pytest.approx(opci_ratio(2015, 2025))
    with pytest.raises(ValueError):
        escalation_factor(2015, 2025, "index", make_basis())
    with pytest.raises(ValueError):
        escalation_factor(2015, 2025, "damped", b)  # half-change low case retired


def test_opci_single_case_is_default(tmp_path):
    df = analogs(tmp_path, {"cost_year": 2015, "fid_year": 2015})
    res = estimate(df, basis(estimate_date="2025"))
    assert list(res.cases["case"]) == ["OPCI"]
    assert central_unit(res) == pytest.approx(1000 * opci_ratio(2015, 2025))
    assert escalation_source(res.basis) == opci_link.stamp_label()
    assert any("constant" in s for s in res.sensitivities["sensitivity"])


def test_user_index_overrides_opci(tmp_path):
    df = analogs(tmp_path, {"cost_year": 2015, "fid_year": 2015})
    res = estimate(df, basis(estimate_date="2025", cost_index={2015: 100.0, 2025: 150.0}))
    assert len(res.cases) == 1
    assert central_unit(res) == pytest.approx(1500)
    assert any("in place of OPCI" in w for w in res.warnings)
    assert "replaces OPCI" in escalation_source(res.basis)


def test_user_index_projects_from_its_last_period(tmp_path):
    df = analogs(tmp_path, {"cost_year": 2015, "fid_year": 2015})
    idx = {2015: 100.0, 2024: 140.0, 2025: 150.0}
    res = estimate(df, basis(estimate_date="2029Q4", cost_index=idx))
    p = res.escalation["projection"]
    years = 2029.875 - 2025.5  # middle of 2029 Q4 less the middle of 2025
    assert p["from"] == "2025" and p["years"] == pytest.approx(years)
    assert p["mid"] == pytest.approx(1.04 ** years)  # same stopgap rates as OPCI
    j = res.journey.iloc[0]
    assert j["f_published"] == pytest.approx(1.5) and j["f_projection"] == pytest.approx(p["mid"])
    assert central_unit(res) == pytest.approx(1500 * p["mid"])
    assert res.escalation["reference_date"] == "2025"
    assert res.escalation["reference_central"] == pytest.approx(res.central / p["mid"])
    assert "projection, not data" in " ".join(res.escalation["lines"])
    inside = estimate(df, basis(estimate_date="2024", cost_index=idx))
    assert inside.escalation["projection"] is None
    assert inside.escalation["reference_central"] == pytest.approx(inside.central * 150 / 140)
    flat = estimate(df, basis(estimate_date="2029Q4", escalation_mode="constant"))
    assert flat.escalation["projection"] is None and flat.escalation["reference_central"] is None
    assert flat.journey["f_projection"].eq(1.0).all()


def test_freeze_reproduces_named_release(tmp_path):
    df = analogs(tmp_path, {"cost_year": 2015, "fid_year": 2015}, {"cost_year": 2019, "fid_year": 2019})
    name = opci_link.releases()[0]
    frozen = estimate(df, basis(estimate_date="2025", opci_release=name, weighting="equal"))
    again = estimate(df, basis(estimate_date="2025", opci_release=name, weighting="equal"))
    assert frozen.central == again.central
    expected = 500 * (opci_ratio(2015, 2025, name) + opci_ratio(2019, 2025, name))
    assert central_unit(frozen) == pytest.approx(expected, rel=1e-12)
    assert "(frozen)" in escalation_source(frozen.basis)
    with pytest.raises(ValueError, match="not installed"):
        estimate(df, basis(estimate_date="2025", opci_release="data-1999-01"))


def test_band_and_supply_shock_note_from_opci(tmp_path):
    bd = opci_link.band()
    assert bd["normal"] == pytest.approx(0.055, abs=0.005)
    assert bd["shock"] == pytest.approx(0.09, abs=0.005)
    df = analogs(tmp_path, {"cost_year": 2015, "fid_year": 2015}, {"cost_year": 2021, "fid_year": 2021})
    res = estimate(df, basis(estimate_date="2025", fid_window_years=None))
    band = res.journey.set_index("id")["esc_band"]
    assert band["a1"] == bd["normal"] and band["a2"] == bd["shock"]
    assert SUPPLY_SHOCK_NOTE in res.notes
    calm = estimate(analogs(tmp_path, {"cost_year": 2015, "fid_year": 2015}), basis(estimate_date="2025"))
    assert SUPPLY_SHOCK_NOTE not in calm.notes
    to_shock = estimate(analogs(tmp_path, {"cost_year": 2015, "fid_year": 2015}), basis(estimate_date="2021"))
    assert SUPPLY_SHOCK_NOTE in to_shock.notes
    assert to_shock.journey["esc_band"].iloc[0] == bd["shock"]  # estimate date in 2021 widens it too


def test_no_projection_up_to_latest_quarter(tmp_path):
    df = analogs(tmp_path, {"cost_year": 2015, "fid_year": 2015})
    latest = opci_link.latest_quarter()
    for date in (None, latest, "2024Q2"):
        res = estimate(df, basis(estimate_date=date))
        assert res.escalation["projection"] is None
        assert res.journey["f_projection"].eq(1.0).all()
        assert not any("rojection" in line for line in res.escalation["lines"])
    res = estimate(df, basis(estimate_date="2024Q2"))
    assert central_unit(res) == pytest.approx(1000 * opci_ratio(2015, "2024Q2", freq="quarterly"))
    assert res.escalation["reference_date"] == latest
    assert res.escalation["reference_central"] == pytest.approx(
        res.central * opci_ratio("2024Q2", latest, freq="quarterly", base_freq="quarterly"))


def test_projection_beyond_latest_quarter(tmp_path):
    df = analogs(tmp_path, {"cost_year": 2015, "fid_year": 2015})
    latest = opci_link.latest_quarter()
    res = estimate(df, basis(estimate_date="2029 Q4"))
    p = res.escalation["projection"]
    years = (2029 * 4 + 3 - opci_link.quarter_number(latest)) / 4
    assert p["from"] == latest and p["to"] == "2029Q4" and p["years"] == years
    assert p["mid"] == pytest.approx((1 + 0.025 + 0.015) ** years)
    assert p["low"] == pytest.approx(1.025 ** years) and p["high"] == pytest.approx(1.06 ** years)
    j = res.journey.iloc[0]
    assert j["f_published"] == pytest.approx(opci_ratio(2015, latest, freq="quarterly"))
    assert j["f_esc"] == pytest.approx(j["f_published"] * p["mid"])
    text = " ".join(res.escalation["lines"])
    assert "projection, not data" in text and "stopgap" in text.lower()
    assert res.escalation["reference_central"] == pytest.approx(res.central / p["mid"])
    sens = " ".join(res.sensitivities["sensitivity"])
    assert "Projection low" in sens and "Projection high" in sens
    own = estimate(df, basis(estimate_date="2029Q4", projection_inflation=0.02, projection_real=(0.0, 0.01, 0.02)))
    assert own.escalation["projection"]["mid"] == pytest.approx(1.03 ** years)
    assert "stopgap" not in " ".join(own.escalation["lines"]).lower()
    with pytest.raises(ValueError, match="Enter a quarter"):
        estimate(df, basis(estimate_date="2029"))
    with pytest.raises(ValueError, match="not a quarter"):
        estimate(df, basis(estimate_date="Q4 2029"))


def test_analog_before_opci_data_is_filtered(tmp_path):
    df = analogs(tmp_path, {}, {"cost_year": 2005, "fid_year": 2005})
    res = estimate(df, basis(fid_window_years=None))
    notes = dict(zip(res.pool["id"], res.pool["selection_note"]))
    assert notes["a2"].startswith("Cost year before OPCI data")


def test_calibration_pair_is_report_only(tmp_path):
    df = analogs(tmp_path, {"cost_year": 2015, "fid_year": 2015}, {"cost_year": 2023, "fid_year": 2023,
                                                                  "cost_amount_million": 5500})
    b = basis(estimate_date="2025", cost_index={2015: 100.0, 2023: 140.0, 2025: 150.0}, fid_window_years=None)
    res = estimate(df, b)
    assert len(res.calibration) == 1
    assert res.calibration.loc[0, "f"] == pytest.approx((1.1 - 1) / (1.4 - 1))
    on_opci = estimate(df, basis(estimate_date="2025", fid_window_years=None))
    idx = opci_ratio(2015, 2023)
    assert on_opci.calibration.loc[0, "f"] == pytest.approx((1.1 - 1) / (idx - 1))
    assert central_unit(on_opci) == pytest.approx(
        np.average([1000 * opci_ratio(2015, 2025), 1100 * opci_ratio(2023, 2025)],
                   weights=on_opci.weights.set_index("id").loc[["a1", "a2"], "weight"]))


# ------------------------------------------------------------- Step 5
def test_location_full_and_construction_share(tmp_path):
    df = analogs(tmp_path, {})
    remote = opci.location(to="REMOTE")["factor"]
    full = estimate(df, basis(location_code="REMOTE"))
    assert central_unit(full) == pytest.approx(1000 * remote)
    split = estimate(df, basis(location_code="REMOTE", location_method="construction_share"))
    assert central_unit(split) == pytest.approx(1000 * (1 + 0.32 * (remote - 1)))
    own = estimate(df, basis(location_code="REMOTE", location_factor=1.20))
    assert central_unit(own) == pytest.approx(1200)
    log = own.log.set_index("switch")
    assert log.loc["User location factor (overrides OPCI)", "changed"]
    assert any("replaces OPCI" in line for line in own.location["lines"])


def test_location_comes_from_opci_only(tmp_path):
    assert not hasattr(F, "LOCATION_GROUPS") and not hasattr(F, "LOCATION_STEP")
    res = estimate(load_analogs(), make_basis(location_code="ID-KAL"))
    j = res.journey
    for code, factor in zip(j["loc_analog_code"], j["loc_analog"]):
        assert factor == opci.location(to=code)["factor"]
    target = opci.location(to="ID-KAL")
    assert j["loc_target"].eq(target["factor"]).all()
    assert res.location["low"] == target["low"] and res.location["high"] == target["high"]
    assert res.location["confidence"] == target["confidence"] and res.location["source"] == target["source"]
    sens = dict(zip(res.sensitivities["sensitivity"], res.sensitivities["central"]))
    assert f"Target location low ({target['low']:.2f}, OPCI range)" in sens
    with pytest.raises(ValueError, match="not in the OPCI location table"):
        analogs(tmp_path, {"location_code": "MARS"})


def test_former_stand_ins_use_their_own_opci_codes():
    df = load_analogs().set_index("id")
    codes = {"nlng_t7": "NG-BON", "mozambique_lng": "MZ-AFU", "angola_lng": "AO-SOY",
             "donggi_senoro": "ID-SUL", "tangguh_t3": "ID-PAP"}
    for aid, code in codes.items():
        assert df.loc[aid, "location_code"] == code
        assert opci.location(to=code)["factor"] > 0
        assert "stand-in" not in df.loc[aid, "notes"]


# ------------------------------------------------------------- Step 6
def test_scope_factors(tmp_path):
    df = analogs(
        tmp_path,
        {"cost_basis": "epc", "contingency_status": "epc_only"},
        {"site_type": "brownfield"},
        {"trains": 2, "capacity_mtpa": 10.0},
        {"liquids_scope": "rich"},
        {"co2_sequestration": "yes"},
        {"scope": "integrated_upstream", "plant_only_amount_million": 2500},
    )
    res = estimate(df, basis(weighting="equal"))
    j = res.journey.set_index("id")
    assert j.loc["a1", "f_owner"] == pytest.approx(1.09)
    assert j.loc["a2", "f_site"] == pytest.approx(1.5)
    assert j.loc["a3", "f_multi"] == pytest.approx(1.15)
    assert j.loc["a4", "f_gas"] == pytest.approx(1 / 1.10)
    assert j.loc["a5", "co2_adj"] == pytest.approx(-95)
    assert j.loc["a6", "f_split"] == pytest.approx(0.5)
    assert j.loc["a3", "u_scoped"] == pytest.approx(500 * 1.15)  # 5000 over 10 MTPA, to one train


def test_brownfield_target_and_graded_gas(tmp_path):
    df = analogs(tmp_path, {})
    bf = estimate(df, basis(site_type="brownfield"))
    assert central_unit(bf) == pytest.approx(1000 / 1.5)
    rich = estimate(df, basis(feed_gas="condensate", gas_method="graded"))
    assert central_unit(rich) == pytest.approx(1310)


# ------------------------------------------------------------- Step 7
def test_size_scaling_on_unit_cost(tmp_path):
    df = analogs(tmp_path, {})
    res = estimate(df, basis(train_size_mtpa=6.0, exponent=0.7))
    assert central_unit(res) == pytest.approx(1000 * (6 / 5) ** (0.7 - 1))


def test_multi_train_target_methods(tmp_path):
    df = analogs(tmp_path, {})
    rev = estimate(df, basis(trains=2))
    assert central_unit(rev) == pytest.approx(1000 / 1.15)
    build = estimate(df, basis(trains=2, multi_train_method="build_up"))
    assert central_unit(build) == pytest.approx(1000 * 0.75)


def test_fitted_exponent_is_reported(tmp_path):
    df = analogs(tmp_path, {"capacity_mtpa": 4.0, "cost_amount_million": 4000 * (4 / 5) ** -0.4},
                 {"capacity_mtpa": 5.0}, {"capacity_mtpa": 6.5, "cost_amount_million": 6500 * (6.5 / 5) ** -0.4})
    res = estimate(df, basis())
    assert res.fitted_exponent["n"] == pytest.approx(0.6, abs=1e-6)
    assert res.exponent == pytest.approx(0.7)


# ------------------------------------------------------------- Step 8
def test_rubric_and_judgment_weights(tmp_path):
    df = analogs(tmp_path, {"region": "Southeast Asia"}, {"cost_amount_million": 6000})
    res = estimate(df, basis(target_region="Southeast Asia"))
    w = res.weights.set_index("id")
    assert w.loc["a1", "rubric_points"] == 5 and w.loc["a1", "suggested_weight"] == 3
    assert w.loc["a2", "rubric_points"] == 4
    res2 = estimate(df, basis(target_region="Southeast Asia", weights={"a2": 1}))
    assert any("reason is required" in x for x in res2.warnings)
    assert central_unit(res2) == pytest.approx((1000 * 3 + 1200 * 1) / 4)


def test_unreviewed_rubric_weights_are_flagged(tmp_path):
    df = analogs(tmp_path, {"region": "Southeast Asia"}, {"cost_amount_million": 6000}, {"cost_amount_million": 5200})
    res = estimate(df, basis(target_region="Southeast Asia", weights={"a2": 1}, weight_reasons={"a2": "Older scope"},
                             weights_reviewed=("a3",)))
    flag = res.weights.set_index("id")["weight_flag"]
    assert flag["a1"] == "rubric, not reviewed"  # still at the rubric weight, not reviewed
    assert flag["a2"] == ""  # changed by the user, with a reason
    assert flag["a3"] == ""  # kept at the rubric weight on purpose
    log = res.log.set_index("switch")
    assert log.loc["Weight for a1", "reason"] == "rubric, not reviewed"
    assert log.loc["Weight for a3", "reason"] == "Reviewed; rubric weight kept"
    assert log.loc["Weight for a2", "reason"] == "Older scope"
    equal = estimate(df, basis(weighting="equal"))
    assert equal.weights["weight_flag"].eq("").all()  # no rubric weights to flag
    gate = estimate(df, basis(purpose="gate1"))
    assert any("not reviewed" in w for w in gate.warnings)


def test_outlier_flag_and_drop(tmp_path):
    df = analogs(tmp_path, {}, {"cost_amount_million": 5100}, {"cost_amount_million": 9000})
    res = estimate(df, basis(weighting="equal"))
    assert res.weights.set_index("id").loc["a3", "outlier"]
    dropped = estimate(df, basis(weighting="equal", drop_reasons={"a3": "Scope unclear"}))
    assert central_unit(dropped) == pytest.approx(1010)


def test_stats_gap_warning(tmp_path):
    df = analogs(tmp_path, {}, {"cost_amount_million": 7000})
    res = estimate(df, basis(weighting="judgment", weights={"a1": 3, "a2": 1},
                             weight_reasons={"a1": "x", "a2": "y"}))
    assert any("second look" in x for x in res.warnings)


# ------------------------------------------------------------- Step 9
def test_site_item_decision_tree(tmp_path):
    df = analogs(tmp_path, {})
    items = [
        SiteItem("Trestle", "marine", True, 0, -200, 300),
        SiteItem("Power", "power", False, 100, 80, 150),
        SiteItem("Small", "other", False, 10, 5, 20),
    ]
    res = estimate(df, basis(site_items=items))
    reg = res.site_register.set_index("item")
    assert reg.loc["Trestle", "base_adder"] == 0 and reg.loc["Trestle", "risk"] == 300
    assert reg.loc["Power", "base_adder"] == 100
    assert reg.loc["Small", "base_adder"] == 0  # 10 is below 1% of 5000
    assert res.central == pytest.approx(5100)


def test_tank_library():
    assert tank_cost(180_000) == pytest.approx(200)
    assert tank_cost(220_000) == pytest.approx(200 * (220 / 180) ** 0.6)


# ------------------------------------------------------------- Step 10
def test_choose_base_rules():
    # A and B have the fewest calls; neither is at an end; A is nearer the middle (5.15).
    ms = [Method("A", 5.1, 1), Method("B", 5.6, 1), Method("C", 6.1, 5), Method("D", 4.9, 2)]
    assert choose_base(ms, "combined")[0].name == "A"
    assert choose_base(ms, "conservative")[0].name == "C"
    assert choose_base(ms, "fewest")[0].name == "A"
    assert choose_base(ms, "middle")[0].name == "A"
    ms2 = [Method("Lo", 4.0, 1), Method("Mid", 5.0, 1), Method("Hi", 6.0, 3)]
    assert choose_base(ms2, "combined")[0].name == "Mid"


def test_brownfield_block_method(tmp_path):
    df = analogs(tmp_path, {})
    b = basis(site_type="brownfield", brownfield_shares=BrownfieldShares(0.5, 0.5, 0.0, 0.0))
    res = estimate(df, b)
    blocks = res.methods.set_index("name")
    # Greenfield 5000: EPC 4500, process 2250, storage/marine 360, utilities 1134, site works 756
    expected = (2250 + 0.5 * 1134 + 0.5 * 756) / 0.9
    assert blocks.loc["Block by block", "value"] == pytest.approx(expected)
    assert blocks.loc["Block by block", "judgment_calls"] == 4


# ------------------------------------------------------------- Step 11
def test_blocks_add_up(tmp_path):
    df = analogs(tmp_path, {})
    res = estimate(df, basis(site_items=[SiteItem("Power", "power", False, 100, 80, 150)]))
    assert res.blocks_by_area["usd_million"].sum() == pytest.approx(res.central)
    assert res.blocks_by_type["share"].sum() == pytest.approx(1.0)


def test_battery_limits_remove_blocks(tmp_path):
    df = analogs(tmp_path, {})
    res = estimate(df, basis(battery_limits=("trains", "utilities", "site_works", "owners_costs")))
    # Storage and marine (8% of EPC = 7.2% of total) removed
    assert res.central == pytest.approx(5000 * (1 - 0.072))


def test_storage_and_marine_split_one_third_tank(tmp_path):
    df = analogs(tmp_path, {})
    full = estimate(df, basis()).blocks_by_area.set_index("block").loc["Storage and marine", "usd_million"]
    assert full == pytest.approx(5000 * 0.9 * 0.08)  # 8% of EPC
    all_in = ("trains", "utilities", "tanks", "marine", "site_works", "owners_costs")
    no_tank = estimate(df, basis(battery_limits=tuple(x for x in all_in if x != "tanks")))
    no_marine = estimate(df, basis(battery_limits=tuple(x for x in all_in if x != "marine")))
    assert no_tank.central == pytest.approx(5000 - full / 3)
    assert no_marine.central == pytest.approx(5000 - full * 2 / 3)


# ------------------------------------------------------------- Step 12
def test_built_range_is_root_sum_of_squares(tmp_path):
    df = analogs(tmp_path, {}, {"cost_amount_million": 5500})
    res = estimate(df, basis(definition_growth=(0.0, 0.15), weighting="equal", location_code="ID-KAL"))
    p = res.range_parts
    band = opci_link.band()["normal"]
    loc = opci.location(to="ID-KAL")
    assert p["escalation_band_low"] == pytest.approx(-band) and p["escalation_band_high"] == pytest.approx(band)
    assert p["target_location_low"] == pytest.approx(loc["low"] / loc["factor"] - 1)
    assert p["target_location_high"] == pytest.approx(loc["high"] / loc["factor"] - 1)
    assert "projection_low" not in p  # no projection up to the latest quarter
    lows = [p["analog_spread_low"], 0.0, -band, p["target_location_low"]]
    highs = [p["analog_spread_high"], 0.15, band, p["target_location_high"]]
    assert res.low == pytest.approx(res.central * (1 - math.sqrt(sum(x * x for x in lows))))
    assert res.high == pytest.approx(res.central * (1 + math.sqrt(sum(x * x for x in highs))))
    # the target location range enters once; analog location ranges do not
    assert [k for k in p if "location" in k] == ["target_location_low", "target_location_high"]
    wide = estimate(df, basis(widen_to_class_band=True, weighting="equal"))
    assert wide.low == pytest.approx(wide.central * 0.7) and wide.high == pytest.approx(wide.central * 1.5)


def test_projection_cases_enter_the_range(tmp_path):
    df = analogs(tmp_path, {"cost_year": 2015, "fid_year": 2015})
    res = estimate(df, basis(estimate_date="2029Q4"))
    pr = res.escalation["projection"]
    assert res.range_parts["projection_low"] == pytest.approx(pr["low"] / pr["mid"] - 1)
    assert res.range_parts["projection_high"] == pytest.approx(pr["high"] / pr["mid"] - 1)


def test_single_analog_uses_default_spread(tmp_path):
    res = estimate(analogs(tmp_path, {}), basis())
    assert any("Only one analog" in w for w in res.warnings)
    assert res.range_parts["analog_spread_low"] == F.DEFAULT_ANALOG_SPREAD[0]
    assert res.range_parts["analog_spread_high"] == F.DEFAULT_ANALOG_SPREAD[1]


def test_class_band_warning_tolerance(tmp_path):
    df = analogs(tmp_path, {})
    first = estimate(df, basis(definition_growth=(0.0, 0.15)))
    lo, hi = first.low / first.central - 1, first.high / first.central - 1

    def warned(class_low, class_high):
        r = estimate(df, basis(definition_growth=(0.0, 0.15), class_low=class_low, class_high=class_high))
        return any("narrower than the class band" in w for w in r.warnings)

    assert not warned(lo - 0.015, hi + 0.015)  # within 2 points at both ends
    assert warned(lo - 0.025, hi)  # low end more than 2 points narrower
    assert warned(lo, hi + 0.025)  # high end more than 2 points narrower


def test_contingency_only_for_missing_share(tmp_path):
    df = analogs(tmp_path, {"cost_basis": "epc", "contingency_status": "epc_only"})
    res = estimate(df, basis(apply_owner_costs=False))
    assert res.contingency["applies"]
    assert res.central == pytest.approx(5000 * 1.15)
    df2 = analogs(tmp_path, {})
    assert not estimate(df2, basis()).contingency["applies"]


def test_correlated_comparison(tmp_path):
    df = analogs(tmp_path, {}, {"cost_amount_million": 5500})
    a = estimate(df, basis(weighting="equal"))
    b = estimate(df, basis(weighting="equal", site_type="brownfield", option_name="B"))
    c = compare_options(a, b)
    assert c["central_difference"] == pytest.approx(b.central - a.central)
    assert c["low"] <= c["central_difference"] <= c["high"]
    assert c["high"] < 0  # brownfield is cheaper in every shared case


def test_saving_cap_at_most_optimistic_method(tmp_path):
    df = analogs(tmp_path, {}, {"cost_amount_million": 5500})
    a = estimate(df, basis(weighting="equal"))
    shares = BrownfieldShares(0.5, 0.5, 0.0, 0.0)
    b = estimate(df, basis(weighting="equal", site_type="brownfield", option_name="B",
                           brownfield_shares=shares, method_gap_note="x"))
    assert len(b.methods) == 2
    c = compare_options(a, b)
    best = a.central - b.methods["value"].min()  # saving from B's most optimistic method
    assert c["saving_cap"] == pytest.approx(-best)
    assert -c["low"] <= best + 1e-9  # the largest saving never exceeds it


# ------------------------------------------------------------- Step 13
def test_decision_log_includes_defaults(tmp_path):
    df = analogs(tmp_path, {})
    res = estimate(df, basis(reasons={"step:7": "Practice value"}))
    log = res.log.set_index("switch")
    assert log.loc["Size exponent n", "reason"] == "Practice value"
    assert log.loc["Weighting method", "reason"] == "Default accepted"
    assert (log["date"] != "").all()


def test_escalation_panel_split_band_and_shock(tmp_path):
    df = analogs(tmp_path, {"cost_year": 2015, "fid_year": 2015}, {"cost_year": 2021, "fid_year": 2021})
    res = estimate(df, basis(estimate_date="2029Q4", fid_window_years=None))
    p = res.escalation_panel().set_index("cost_year")
    proj = res.escalation["projection"]
    assert p.loc[2015, "f_esc"] == pytest.approx(p.loc[2015, "f_published"] * proj["mid"])
    assert p.loc[2015, "projection_part"] == pytest.approx(p.loc[2015, "f_esc"] - p.loc[2015, "f_published"])
    bd = opci_link.band()
    assert p.loc[2015, "esc_band"] == bd["normal"] and p.loc[2021, "esc_band"] == bd["shock"]
    assert p.loc[2021, "supply_shock"] and not p.loc[2015, "supply_shock"]
    assert p.loc[2021, "band_high"] == pytest.approx(p.loc[2021, "f_esc"] * (1 + bd["shock"]))
    notes = res.escalation_panel_notes()
    assert any("back-test" in n for n in notes) and SUPPLY_SHOCK_NOTE in notes


def test_decision_log_records_opci(tmp_path):
    df = analogs(tmp_path, {})
    log = estimate(df, basis()).log.set_index("switch")
    assert log.loc["OPCI version", "setting"] == opci.__version__
    assert log.loc["OPCI data release used", "setting"] == opci_link.latest_release()
    assert log.loc["OPCI data release (freeze switch)", "setting"] == "Latest"
    name = opci_link.releases()[0]
    frozen = estimate(df, basis(opci_release=name)).log.set_index("switch")
    assert frozen.loc["OPCI data release (freeze switch)", "setting"] == name
    assert frozen.loc["OPCI data release used", "reason"] == "Frozen on a named release"


def test_guideline_labels_are_v02():
    assert F.GUIDE.endswith("v0.2")


def test_preview_types_switch_off_liquefaction_factors():
    df = load_analogs()
    res = estimate(df, make_basis("flng", train_size_mtpa=2.5, site_type="conversion"))
    assert res.journey["f_site"].eq(1).all() and res.journey["f_gas"].eq(1).all()
    assert any("Preview" in w for w in res.warnings)


def test_check_catches_bad_rows(tmp_path):
    df = pd.DataFrame([dict(BASE_ROW, facility_type="spaceport")])
    assert not check_analogs(df).ok
