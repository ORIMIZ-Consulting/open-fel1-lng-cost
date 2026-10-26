"""Link to the Open Plant Cost Index (OPCI), the source of escalation and location.

Guideline v0.2, Step 4: every result carries the OPCI version and data release,
for example "OPCI 1.0.0, data-2026-09". The latest data release is used by
default; the freeze switch names a release so an old estimate can be
reproduced exactly. The escalation band and the supply-shock note are read
from OPCI, not written into this tool.
"""
from __future__ import annotations

from functools import lru_cache

import opci
from opci import paths
from opci.calibrate import backtest
from opci.index import SUPPLY_SHOCK_YEARS, supply_shock_warning
from opci.locations import load_factors
from opci.locations import version as location_version
from opci.release import list_releases

from . import factors as F
from .factors import OPCI_URL  # noqa: F401  (re-exported for the app)


def releases() -> list[str]:
    """Names of the installed OPCI data releases, oldest first."""
    return [p.name for p in list_releases()]


def latest_release() -> str:
    """Name of the newest OPCI data release, for example "data-2026-09"."""
    names = releases()
    if not names:
        raise RuntimeError("OPCI has no data release installed. Reinstall the opci package.")
    return names[-1]


def resolve(release: str | None) -> str:
    """The release to use: the named one (freeze), else the latest."""
    if release is None:
        return latest_release()
    if release not in releases():
        raise ValueError(f"OPCI data release '{release}' is not installed. "
                         f"Installed: {', '.join(releases()) or 'none'}.")
    return release


@lru_cache(maxsize=None)
def _release(release: str, freq: str) -> dict:
    return opci.read_release(release, freq=freq)


def meta(release: str | None = None, freq: str = "annual") -> dict:
    return _release(resolve(release), freq)["meta"]


def table(release: str | None = None, freq: str = "annual") -> dict[str, dict]:
    """OPCI rows by period ("2015" or "2015Q2") for one data release."""
    return {r["period"]: r for r in _release(resolve(release), freq)["rows"]}


def first_year(release: str | None = None) -> int:
    return int(min(table(release)))


def last_year(release: str | None = None) -> int:
    return int(max(table(release)))


@lru_cache(maxsize=None)
def _band(release: str) -> dict:
    m = meta(release)
    snap = next((d / m["snapshot"] for d in paths.snapshot_dirs() if (d / m["snapshot"]).exists()), None)
    if snap is None:
        raise RuntimeError(f"OPCI snapshot {m['snapshot']} for {release} is not installed, "
                           "so the escalation band cannot be read.")
    bt = backtest(productivity=m["productivity"], investment=m["investment"], snapshot=snap)
    return {"normal": bt["worst"], "shock": bt["watch_worst"],
            "source": f"OPCI back-test against public CEPCI ({release})"}


def band(release: str | None = None) -> dict:
    """Escalation band: worst back-test error on normal and on supply-shock years."""
    return _band(resolve(release))


def is_shock_year(year: int) -> bool:
    return int(year) in SUPPLY_SHOCK_YEARS


def supply_shock_note(base, target) -> str | None:
    """OPCI's note when the base or target date falls in a supply-shock year."""
    return supply_shock_warning(base, target)


def stamp(release: str | None = None) -> dict:
    """OPCI version and data release used for this result."""
    return {"version": opci.__version__, "data_release": resolve(release), "frozen": release is not None}


def stamp_label(release: str | None = None) -> str:
    s = stamp(release)
    return f"OPCI {s['version']}, {s['data_release']}" + (" (frozen)" if s["frozen"] else "")


# ---------------------------------------------------------------- periods and projection
def parse_period(text) -> str:
    """'2029 Q4', '2029q4' or '2029Q4' -> '2029Q4'; '2029' -> '2029'."""
    t = str(text).strip().upper().replace(" ", "")
    if len(t) == 4 and t.isdigit():
        return t
    if len(t) == 6 and t[:4].isdigit() and t[4] == "Q" and t[5] in "1234":
        return t
    raise ValueError(f"'{text}' is not a quarter. Use the form 2029 Q4.")


def show_period(period: str) -> str:
    return period.replace("Q", " Q")


def quarter_number(period: str) -> int:
    """Quarters since year 0, for counting the time between two quarters."""
    return int(period[:4]) * 4 + int(period[5]) - 1


def latest_quarter(release: str | None = None) -> str:
    """Latest published OPCI quarter (a full quarter, not a part one)."""
    return [p for p, r in table(release, "quarterly").items() if not r["part"]][-1]


def value(period, release: str | None = None) -> dict:
    """OPCI row for a year ('2015') or a quarter ('2015Q2')."""
    period = str(period)
    return table(release, "quarterly" if "Q" in period else "annual").get(period)


def projection_defaults() -> dict:
    """Projection rates: data-based defaults from OPCI when it holds them.

    OPCI 1.0 holds no projection rates yet (decision D4), so the labelled
    stopgap from factors.py is used.
    """
    return {"inflation": F.STOPGAP_INFLATION, "real": F.STOPGAP_REAL_ESCALATION,
            "source": "stopgap", "note": F.STOPGAP_SOURCE}


# ---------------------------------------------------------------- location (guideline Step 5)
NOT_SET = "not_set"  # preview facility types: no location adjustment


def locations() -> dict[str, dict]:
    """The OPCI location table by code: factor, low, high, confidence, method, source."""
    return load_factors()


def location(code: str) -> dict:
    """OPCI location factor for a code, against the US Gulf Coast (1.00)."""
    if code == NOT_SET:
        return {"factor": 1.0, "low": 1.0, "high": 1.0, "confidence": "-", "to": NOT_SET,
                "to_name": "Not set (no location adjustment)", "method": "-", "source": "-",
                "as_of": None, "notes": {}, "location_version": location_version()}
    if code not in locations():
        raise ValueError(f"Unknown OPCI location code '{code}'. New locations are added to OPCI, "
                         f"not to this tool. Known codes: {', '.join(locations())}.")
    return opci.location(to=code)


def location_label(code: str) -> str:
    loc = location(code)
    if code == NOT_SET:
        return loc["to_name"]
    return f"{loc['to_name']} ({code}) {loc['factor']:.2f} ({loc['low']:.2f} to {loc['high']:.2f})"
