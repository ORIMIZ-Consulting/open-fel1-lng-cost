# FEL 1 LNG Capital Cost Estimating Guideline

**Analog-based Class 5 estimating for liquefied natural gas (LNG) plants: any location, capacity or technology**

Version 0.2, 24 October 2026. Author: Syed Zia Haider, ORIMIZ Consulting. Draft for tool development.

**What changed from version 0.1:** escalation and location now come from the Open Plant Cost Index (OPCI), a free index built from public domain data (decisions D1 to D5, 24 October 2026). The estimate date is entered by the user, usually the expected FID date, and any part beyond published data is shown as a projection. The two escalation cases are replaced by one data-based case with a band. Storage and marine default split, a weights flag, a saving cap and a class-band tolerance are added.

## Decisions behind version 0.2

The owner agreed these decisions on 24 October 2026.

| # | Decision |
| --- | --- |
| D1 | OPCI installed as `opci>=1.0,<2.0`; latest data release stamped on every result; freeze switch; Dependabot weekly; user index file overrides; location factors from OPCI only |
| D2 | Single escalation case (full OPCI change); back-test band ±5.5% (±9% for 2021 and 2022 analogs); half-change low case retired; review with OPCI LNG weights (version 1.1) |
| D3 | Estimate date input with a final investment decision (FID) prompt; published data then labelled projection; split shown; reference line in today's money; spend profile parked for FEL 2 and Class 3 |
| D4 | Projection rates from data held in OPCI (International Monetary Fund (IMF) forecast plus OPCI real escalation), labelled stopgap until then, user override |
| D5 | Only the target location range is added to the estimate range; single-analog warning |

---

## 1. Purpose and scope

This guideline sets out how to build a front-end loading (FEL) 1 capital cost estimate for an LNG liquefaction plant from public analog projects. FEL 1 normally produces an AACE International Class 5 estimate: good for screening ideas, comparing concepts and supporting a Gate 1 decision, not for a budget or a final investment decision (FID).

**Covered:** onshore liquefaction capital cost (capex), from the plant inlet fence to the loading arm, plus owner's costs.

**Not covered yet:** floating LNG (FLNG), regasification, operating cost (opex), schedule, and upstream or pipeline costs. Section 18 shows where an FLNG module plugs in.

**Tool:** the FEL1 LNG Cost tool in this repository implements every step. This public copy leaves out the project-specific worked example.

## 2. Design principles

1. **Every method choice is a switch, not a fixed rule.** Each switch has options, a default and a source for the default. The user decides case by case.
2. **Every switch is logged,** defaults included, with its setting, the default, the reason and the date.
3. **Public data only.** No company-internal data. Every analog figure and every factor carries a source.
4. **Normalize before you compare.** A raw cost per tonne is meaningless until scope, site, gas, location and date are aligned.
5. **Evidence first, judgment second.** Where public evidence exists, it sets the number. Where it does not, judgment is allowed but labelled as judgment.
6. **At least two independent methods,** and the gap between them explained in writing.
7. **No double counting.** In particular, do not add contingency to analog figures that already contain it.

## 3. Units, conventions and terms

| Term | Meaning |
| --- | --- |
| MTPA | Million tonnes per annum of LNG |
| USD/tpa | US dollars per tonne per annum of capacity (unit cost) |
| Train | One liquefaction unit; capacity is entered per train |
| Greenfield | New plant on a new site, with its own tanks, jetty and utilities |
| Brownfield | A train added to an existing site, sharing tanks, jetty or utilities |
| EPC | Engineering, procurement and construction contract value |
| Owner's costs | Owner's team, consultants, permits, land, insurance and similar, outside the EPC contract |
| Normalization | Adjusting an analog's cost to the target's basis, one factor at a time |
| Analog | A past project with a published cost |
| CEPCI | Chemical Engineering Plant Cost Index |
| OPCI | Open Plant Cost Index, the free plant cost index this guideline uses for escalation and location (github.com/ORIMIZ-Consulting/open-plant-cost-index, DOI 10.5281/zenodo.23615226) |
| Data release | One monthly OPCI data set, named by its last month of data, for example data-2026-09 |
| Projection | The part of an escalation factor beyond the latest published OPCI quarter, built from forecast rates |
| FID | Final investment decision |
| OIES | Oxford Institute for Energy Studies |
| AACE | Association for the Advancement of Cost Engineering (AACE International) |

All costs are in USD unless stated. Convert other currencies at the cost-year average rate before escalation.

## 4. Process overview

| Step | Name | Output |
| --- | --- | --- |
| 1 | Key inputs | Basis of estimate |
| 2 | Analog selection | Filtered analog list |
| 3 | Adjustment method | Multiply, add or hybrid |
| 4 | Escalation | Factor to the estimate date: published OPCI data, then a projection where needed |
| 5 | Location | OPCI location factor and range for the target and each analog |
| 6 | Scope and complexity | Each analog on the target's scope |
| 7 | Size scaling | Each analog at the target train size |
| 8 | Combining | One central value |
| 9 | Site-specific items | Base adders, risks and opportunities |
| 10 | Variants and methods | A base for each option, with its range of methods |
| 11 | Cost blocks | Split by area and by cost type |
| 12 | Range | Low, base and high; correlated comparison of options |
| 13 | Outputs and audit trail | Tables, charts, decision log, references |

---

## 5. Step 1. Key inputs

Purpose comes first, because it sets the effort the rest deserves. A quick screen can run on defaults. A Gate 1 estimate should make the user review every switch.

| # | Input | Required? | Options | Default |
| --- | --- | --- | --- | --- |
| 1.1 | Purpose of the estimate | Required | Screen an idea; compare options; Gate 1 | None |
| 1.2 | Facility type | Required | Onshore liquefaction (FLNG to follow) | None |
| 1.3 | Capacity per train and number of trains | Required | MTPA per train × trains | None |
| 1.4 | Site type | Required | Greenfield; brownfield train addition; conversion (FLNG) | None |
| 1.5 | Location | Required | A location from the OPCI table; factor, range and source shown; user can override | None |
| 1.6 | Estimate date and currency | Required | Any quarter. Prompt: "Usually the expected FID date, for example 2029 Q4." USD or local | Latest published OPCI quarter, USD |
| 1.7 | Feed gas | Optional | Lean; rich (LPG, condensate); high CO2 | Lean |
| 1.8 | Process family | Optional | C3MR; DMR; Optimized Cascade; SMR; nitrogen expander; not yet chosen | Not yet chosen |
| 1.9 | Battery limits | Optional | Tick list: trains, utilities, tanks, jetty and marine, site works, owner's costs, upstream, pipeline | All except upstream and pipeline |
| 1.10 | Accuracy target | Optional | Any range | AACE Class 5, −30% / +50% |

**Why capacity per train:** scaling a multi-train plant on its total capacity overstates the economy of scale. Asking for train size and train count up front avoids the error at source.

**Process family abbreviations:** C3MR, propane pre-cooled mixed refrigerant; DMR, dual mixed refrigerant; SMR, single mixed refrigerant. At FEL 1 the process family is a cost archetype, not a decision. Public data gives no reliable capex factor between cycles (OIES notes only that cascade is slightly cheaper to build and dearer to run than C3MR), so technology is carried as a ±5% sensitivity, not a factor.

## 6. Step 2. Analog selection

Each filter can be tightened, loosened or switched off.

| Filter | Options | Default | Reason |
| --- | --- | --- | --- |
| Facility type | Same type only; include others | Same type only | Onshore and FLNG costs are not comparable |
| Train size | Any band around the target train | 0.5 to 2 times the target train | Keeps the exponent's effect within about ±20% |
| FID date | Any cut-off | Last 15 years | Older costs need large, uncertain escalation |
| Scope quality | Plant-only; plant plus pipeline; integrated with upstream; unclear | Plant-only and plant plus pipeline; others only where a published plant split exists (for example OIES) | A number without a stated scope cannot be normalized |
| Site type | Greenfield; brownfield; both | Both, adjusted to the target's site type (Step 6) | More data points, with the adjustment logged |
| Region | Any; priority region | All, with the target's region flagged as preferred | Location factor handles cost; preference shows in weights |
| Process family | Same family only; any | Any, flagged where different | No reliable capex factor between cycles |
| Minimum count | Any | Warn below 5; stop below 3 | Too few points give false confidence |

**Record for each analog:** project, country, site type, number of trains, train size, FID year, published figure, currency, what the figure covers, source link, contingency status (Step 12) and a data quality note.

**Capacity extremes:** below about 1 MTPA per train (modular, small-scale) and above about 6 MTPA per train (very large trains such as AP-X), the analog pool changes. Use a separate cluster rather than stretching the exponent.

## 7. Step 3. Adjustment method

| Option | How it works | Strength | Weakness |
| --- | --- | --- | --- |
| A. Multiply (default) | Unit cost × factor | Simple; matches OIES factors | Treats tanks and jetty as if they scale with tonnes |
| B. Add blocks | Add a cost per item (per tank, per marine set) | Matches step behaviour of infrastructure | Needs block costs; thin in public data |
| C. Hybrid | Multiply for process items (gas, location); add blocks for step items (tanks, jetty, marine) | Closest to reality | Needs both factor and block libraries |

**Default:** A at Class 5. **Switch trigger:** the tool warns the user to switch to C when the target's infrastructure differs from the analogs by more than the materiality threshold (Step 9). Examples: one tank shared by two trains; a 3 km trestle.

## 8. Step 4. Escalation

**Default: OPCI, single case.** Escalation factor = OPCI(estimate date) ÷ OPCI(analog cost date). OPCI is built from 12 US Bureau of Labor Statistics price and wage series, weighted like the published CEPCI components, and checked against public CEPCI values.

| Option | How it works | Source | Note |
| --- | --- | --- | --- |
| A. OPCI (default) | OPCI(target) ÷ OPCI(cost date) | OPCI, latest data release | Free, public domain data, refreshed monthly |
| B. User index (override) | User loads index values; they replace OPCI | Private CEPCI subscription; S&P Global UCCI or DCCI; Nelson-Farrar | Licensed data stays on the user's machine; never published |
| C. Constant rate | (1 + r) ^ (years) | User sets r | Sensitivity only |

**Data release.** The tool uses the latest OPCI data release by default and stamps the OPCI version and data release on every result, for example "OPCI 1.0.0, data-2026-09". A freeze switch fixes a named release, so an old estimate can be reproduced exactly.

**Escalation band.** The factor carries a band from OPCI's back-test against public CEPCI: about ±5.5% for normal years and about ±9% when the analog's cost date falls in 2021 or 2022 (supply-shock years). The tool reads these limits from OPCI. The band enters the range as a named uncertainty (Step 12).

**Supply-shock note.** When an analog's cost date or the estimate date falls in 2021 or 2022, the tool carries OPCI's note: escalation from those dates may be somewhat overstated, and escalation to them somewhat understated.

**Estimate date after the latest published quarter.** The factor is split into two parts, both shown:

1. **Published part:** OPCI from the analog's cost date to the latest published quarter.
2. **Projection:** from the latest published quarter to the estimate date, at (1 + inflation + real escalation) per year, with low, mid and high cases. Labelled "projection".

Example: "Published data to 2026 Q3: ×1.53. Projection 2026 Q3 to 2029 Q4: ×1.13 (low 1.08, high 1.20)."

| Projection rate | Default source | Stopgap until OPCI holds the data |
| --- | --- | --- |
| Inflation | Latest IMF World Economic Outlook forecast for US consumer prices, stored in OPCI | 2.5% a year |
| Real escalation, low | OPCI history: long-run average from 2008 | 0% |
| Real escalation, mid | OPCI history: last ten years | +1.5% |
| Real escalation, high | OPCI history: highest five-year stretch | +3.5% |

The user can override any rate. Every result states the source of each rate, and stopgap values are labelled "stopgap".

**Reference line.** Every result also shows the cost at the latest published quarter (today's money), so estimates made for different FID dates can be compared.

**Out of scope at FEL 1:** spend profile and escalation to mid-construction. These belong to FEL 2 and Class 3.

**Calibration diagnostic (report only):** where the analog set holds a clean pair (same scope and site type, similar contractor and region, built years apart), the tool reports how much of the index change real LNG costs followed: f = (actual cost ratio − 1) ÷ (index ratio − 1). It does not change the estimate. It feeds the review of LNG-specific escalation planned with OPCI's LNG weights (version 1.1). In a test case, Corpus Christi (2015) and Rio Grande (2023) gave real cost movement between −13% and +22% while the index rose 43%.

**Context:** the Gas Exporting Countries Forum (GECF, May 2026) reports that proposed projects cost about 45 to 55% more, in levelized terms, than existing and under-construction ones. This argues against damping escalation for a new greenfield project.

## 9. Step 5. Location

**Default: OPCI location table.** Each analog is moved to the target's location with factor(target) ÷ factor(analog). Each factor in the table has a central value, a range, a confidence level, a method, a source and an as-of year.

| Option | How it works | Source | Note |
| --- | --- | --- | --- |
| A. OPCI location table (default) | Factors and ranges from OPCI, for example US Gulf Coast 1.00; North West Australia 1.72 (1.55 to 1.98); East Kalimantan 1.20 (1.08 to 1.38) | OIES NG137 group factors plus OPCI's written step rule | One shared table for all tools; the step trail for each factor is in its notes |
| B. User factor | User sets target and analog factors | Judgment | Logged as an override |
| C. Split by cost type | Apply the factor only to the local share (construction, about 32%) | OIES cost split | A 1.50 labour factor then moves the total by about 16% |
| D. Published country factor sets | Process plant factors by country | Compass International; Richardson (paid) | Wide coverage; not LNG-specific |

**Step rule.** New locations are added to OPCI, not to this tool. OPCI starts from the nearest published group and moves in steps of 0.10, one step for each clear difference (existing hub, local yards, skilled labour, remoteness, climate), and records each step.

**Range in the estimate.** Only the **target** location range enters the estimate range, as its own named uncertainty (Step 12). Errors in the analog location factors are not added again: they show up as scatter between the normalized analogs, which the analog spread already covers. When a cost moves between two places that are both not the reference, OPCI combines their ranges by root sum of squares.

## 10. Step 6. Scope and complexity

Factors that put each analog on the target's scope. Each is a switch.

| Factor | Default | Source | When it applies |
| --- | --- | --- | --- |
| Owner's costs on EPC-only figures | × 1.09 (editable 1.08 to 1.12) | User input; OIES uses 10% | Analog figure is an EPC contract value |
| Remove upstream | Use a published plant-only split | OIES Appendix 1 | Analog figure includes upstream |
| Brownfield to greenfield | × 1.50; partial cases × 1.25 | OIES; partial by judgment | Analog and target differ in site type. Reverse (÷) for a brownfield target |
| Partly brownfield site | × 1.15 | OIES group adjustment | Greenfield analog built on an existing industrial site |
| Multi-train to one train | × 1.15 (range 1.10 to 1.20) | OIES, Queensland plants | Analog shares tanks and jetty across trains; target is one train |
| Gas complexity, option A (default) | Rich gas × 1.10 (÷ 1.10 to remove) | OIES | Analog and target differ in gas richness |
| Gas complexity, option B | LPG recovery 1.14; condensate recovery 1.31; sulphur recovery 1.52 (lean = 1.00) | KBR, adjusted by OIES to a whole-plant basis | Target's liquids scope is known and large |
| CO2 removal and sequestration | + USD 60 to 130 per tonne per annum | OIES: Snøhvit, Gorgon | Target or analog has sequestration |

OIES notes that the KBR graded factors run higher than its own, probably because the projects it analysed removed condensate upstream.

**Contracting basis:** lump-sum and reimbursable figures are not directly comparable. Record the basis; no default factor.

## 11. Step 7. Size scaling

**Formula (total cost):**

New cost = Analog cost × (Target train size ÷ Analog train size) ^ n

**Formula (unit cost):**

New unit cost = Analog unit cost × (Target train size ÷ Analog train size) ^ (n − 1)

| Item | Default | Options |
| --- | --- | --- |
| Scaling unit | Train size | Plant size only for single-train analogs (the same thing) |
| Exponent n | 0.7, editable | Fitted value shown with its fit quality (R²), used only if the user chooses |
| Sensitivity | Always show n = 0.6 and n = 0.8 | |
| Extrapolation warning | Target train more than 1.5 times beyond the largest or smallest analog train | |

**Do not derive n from a small analog set.** In a test case, seven analogs gave n of about 0.59 with all included and about 1.0 with Rio Grande removed. Take n from practice; let the analogs set the level.

**Multi-train targets:**

| Option | How it works |
| --- | --- |
| A. Reverse the one-train factor (default) | Unit cost of one train with its own infrastructure ÷ 1.15 |
| B. Build up by train | First train with infrastructure, plus each later train at a repeat cost. OIES: Nigeria LNG trains 4 and 5 roughly halved the unit cost of the added capacity. Use for phased developments |
| C. Scale on plant capacity | Whole plant as one unit with n = 0.7. Kept for comparison only; overstates the economy of scale |

## 12. Step 8. Combining the analogs

| Option | How it works |
| --- | --- |
| A. Equal | Every analog one vote |
| B. Size similarity | Weight = smaller train ÷ larger train |
| C. Rubric only | Points for set criteria |
| D. Judgment prompted by the rubric (default) | Tool shows rubric points; user sets each weight (1, 2 or 3); a reason is required wherever the two differ |

**Rubric (one point each):** same region as the target; a published plant-only figure with no assumed split; train size within 1.5 times the target; two or fewer scope adjustments; FID within 10 years.

**Warning from a test case:** the rubric ranked Rio Grande and Tangguh highest, nearly the reverse of the judgment weights. A rubric is good at prompting the right questions and poor at weighing the answers. Hence option D.

**Weights flag:** any weight that still equals the rubric suggestion and has not been reviewed by the user is flagged "rubric, not reviewed" in the weights panel and the decision log.

**Always show three results side by side:** weighted mean, simple mean and median. If they differ by more than about 5%, the weights are doing a lot of work and deserve a second look.

**Outlier flag:** any analog more than about 30% from the median after normalization is flagged. The user keeps or drops it, with a reason.

**Weighted mean:** sum of (value × weight) ÷ sum of weights.

## 13. Step 9. Site-specific items

**Rule:** the normalized analog level is the base. Site items travel as risks or opportunities, unless the analogs lack the item and it is material.

**Decision tree:**

1. Do the analogs already carry this item in a typical form? If yes, carry only the difference from typical, as a risk or opportunity.
2. If no, is it material? If yes, add it to the base. If no, note it and move on.

**Materiality threshold:** default 1% of the base estimate; user can override.

**Item library:**

| Item | Driver | Public reference point |
| --- | --- | --- |
| Marine works | Trestle length; dredging volume | PNG LNG 2.4 km jetty about USD 258 million (2010); Costa Norte 216 m import jetty about USD 39 million (2016); dredging about USD 15 to 30 per m3 (Cuyutlán, Soyo); Gorgon jetty USD 1.4 billion (extreme) |
| Storage | Tank count and size | About USD 200 million per 180,000 m3 full containment tank (GATE Rotterdam, EUR 160 million; Ruwais, two tanks at USD 250 to 500 million); exponent about 0.6. Norm: one tank per 4 to 5 MTPA train (OIES) |
| Site preparation | Soil; piling; reclamation | OIES: Nigeria LNG preloaded swamp for 18 months; Peru LNG blasted rock terraces |
| Power | Self-generation or grid import | Judgment until data |
| CO2 handling | Sequestration | OIES: USD 60 to 130 per tonne per annum |

## 14. Step 10. Variants and choice of base

Where an option (for example a brownfield variant) can be priced several ways, record each method and its number of judgment calls on top of the shared inputs.

| Option | Rule |
| --- | --- |
| A. Fewest judgment calls | Method with the fewest assumptions |
| B. Middle of the spread | Method nearest the middle |
| C. Most conservative | Highest result. Use when the decision turns on the difference between two options |
| D. Combined rule (default) | Among methods with the fewest judgment calls, prefer one not at either end; the ends set the range |

**Standing rules:**

- At least two independent methods, with the gap explained in writing.
- Switch the base when data arrives: a method whose judgment calls can be replaced with site facts becomes the base once those facts exist.

## 15. Step 11. Cost blocks

Always produce both views.

**By cost type (OIES Table 5):** owner's costs 10%; engineering and project management 8%; equipment 30%; bulk materials 20%; construction 32%. Only construction is truly local, which is why location factors move the total less than labour rates suggest.

**By area:**

| Block | Default | Basis |
| --- | --- | --- |
| Process train (inlet, pre-treatment, liquefaction, refrigerant) | 50% of EPC | OIES |
| Storage and marine | From the Step 9 item library (about 8% in a test case). Default split within the block: one third tank, two thirds jetty and marine | Public references; split by judgment, labelled |
| Utilities and offsites | 60% of the remainder | Judgment, labelled |
| Site works and infrastructure | 40% of the remainder | Judgment, labelled |

For a brownfield variant, price block by block: process train at 100%; then the share of utilities, site works and storage the existing site does not provide, plus tie-ins. Each share is a judgment call until site data exists.

## 16. Step 12. Range

| Option | How it works |
| --- | --- |
| A. Class band | Base × (1 + low) and × (1 + high) |
| B. Analog spread | Weighted P10 and P90 of normalized analogs |
| C. Built from named uncertainties (default) | Analog spread, definition growth, site risks, escalation band, projection and target location range |
| D. Probabilistic | Monte Carlo on cost blocks and risks; for FEL 2 |

**Default:** C, checked against A. If C is narrower than the class band by more than 2 percentage points at either end, the tool warns; the user widens it or records why the project is better defined than a typical Class 5. The tolerance avoids warnings on rounding.

**Building C:**

- **Central:** the normalized analog level, escalated with the single OPCI case (and the mid projection where the estimate date is beyond published data), moved to the target location.
- **Low and high:** the central value combined with each named uncertainty below, by root sum of squares, plus site opportunities (low) and site risks (high) from Step 9.

| Allowance | Default | Evidence |
| --- | --- | --- |
| Analog spread | From the normalized analogs (a test case gave −15% / +20%) | Spread at the target train size |
| Definition growth | 0 / +15% | Donggi-Senoro's estimate rose 40% just before FID; PNG LNG rose from USD 15.7 to 19 billion after sanction |
| Site risks | From Step 9 | Item library |
| Escalation band | About ±5.5%; about ±9% for analogs dated 2021 or 2022 | OPCI back-test against public CEPCI |
| Projection | Low and high projection cases (only when the estimate date is beyond published data) | Step 4 rates |
| Target location | The OPCI range of the target location factor | OPCI location table |

**Contingency flag per analog:** sanctioned budget (contains contingency); EPC only (no owner's contingency); unknown. Add no contingency line when most of the weight sits on budgets. Otherwise add one for the missing share only.

**Correlated comparison of options:** when two options are compared, range the difference separately, holding shared drivers (escalation, location, analog level) together. Two overlapping ranges do not mean the saving might be zero. **Saving cap:** the high end of a saving is capped at the saving given by the variant's most optimistic method (Step 10), so the range never claims more than any single method supports.

**Accuracy reference (AACE 18R-97, process industries):**

| Class | Project definition | Typical method | Typical range |
| --- | --- | --- | --- |
| 5 | 0% to 2% | Capacity factoring, analog curves | Low −20% to −50%; high +30% to +100% |
| 4 | 1% to 15% | Equipment factoring, parametric models | Low −15% to −30%; high +20% to +50% |
| 3 | 10% to 40% | Semi-detailed unit costs | Low −10% to −20%; high +10% to +30% |

The result is a set of reasoned bounds, not a statistical P10 and P90.

## 17. Step 13. Outputs and audit trail

All on by default.

| Output | Content |
| --- | --- |
| Summary | Base, low and high; unit cost; class and accuracy; estimate date; OPCI version and data release; reference line in today's money |
| Analog journey table | Each analog's value after every step, with factor and source |
| Journey chart | Every analog across the steps, one colour each |
| Escalation panel | Factor per analog, split into published part and projection, with the band and any supply-shock note |
| Size curve | Analogs against train size, with the curve and the target |
| Weights panel | Rubric points, chosen weights and reasons; weighted mean, simple mean and median |
| Cost blocks | By area and by cost type |
| Risk and opportunity register | Site items with ranges and status |
| Range chart | Low, base and high per option, plus the difference where options are compared |
| Decision log | Every switch: setting, default, reason, date. Defaults included. OPCI version, data release and freeze setting recorded |
| References | Source of every analog figure and every factor |
| Export | Spreadsheet with all of the above; charts as images |

**Why log defaults too:** a reviewer then sees the full basis in one place, including what the user accepted without thinking about it. That is often where questions should start.

## 18. Module slots: FLNG (to follow)

The 13 steps stay the same. The FLNG module changes:

- **Step 2:** newbuild and conversion as separate clusters (public unit costs run from about USD 500 per tonne for a conversion to about USD 2,100 for a full newbuild development).
- **Step 6:** scope traps are worse: vessel only, vessel plus subsea, and full development all appear as headline numbers. A leased vessel moves capex to opex for the gas owner.
- **Step 7:** scaling on topsides weight (USD per tonne of steel) and hull, not only on LNG capacity.
- **Step 9:** turret and mooring, metocean and offloading uptime join the item library.

## 19. Known limits

- Location factors and escalation move every analog together. They are the largest single drivers and must always be shown, with their sources and ranges.
- OPCI uses US prices. Other countries are handled through location factors, which are judgment based. OPCI tracks CEPCI closely but is not CEPCI.
- Projections beyond the latest published quarter are forecasts, not data.
- Public figures rarely state their full scope. Read each source before using a number.
- Most figures are announced at FID. Final costs are often higher.
- Contractor markets move in cycles that no index captures well.
- Factors from OIES reflect 2014 to 2018 conditions and a limited project set.

## 20. References

**Estimating practice**

- AACE International, Recommended Practice 17R-97, Cost Estimate Classification System.
- AACE International, Recommended Practice 18R-97, Cost Estimate Classification System as Applied in Engineering, Procurement and Construction for the Process Industries.
- AACE International, Recommended Practice 40R-08, Contingency Estimating: General Principles.

**LNG cost studies**

- Songhurst, B. (2018). LNG Plant Cost Reduction 2014–18. OIES Paper NG137. https://www.oxfordenergy.org/wpcms/wp-content/uploads/2018/10/LNG-Plant-Cost-Reduction-2014–18-NG137.pdf
- Songhurst, B. (2014). LNG Plant Cost Escalation. OIES Paper NG83. https://www.oxfordenergy.org/?p=27433
- Songhurst, B. (2016). Floating Liquefaction (FLNG): Potential for Wider Deployment. OIES Paper NG107.
- KBR (2007). LNG Liquefaction: Not All Plants Are Created Equal.
- Fazeliyanova, G. (2026). Rising Marginal Costs in LNG Liquefaction. GECF Expert Commentary. https://www.gecf.org/Portals/0/xBlog/uploads/2026/5/7/2026-05-04MarginalcostliquefactionECFINAL.pdf
- Wood Mackenzie (2023). US could see USD 100 billion of new LNG projects in the next five years.

**Cost indices**

- Haider, S. Z. (2026). Open Plant Cost Index (OPCI), version 1.0.0. ORIMIZ Consulting. DOI 10.5281/zenodo.23615226. https://github.com/ORIMIZ-Consulting/open-plant-cost-index
- US Bureau of Labor Statistics, Producer Price Index and Current Employment Statistics, via FRED, Federal Reserve Bank of St. Louis. https://fred.stlouisfed.org
- International Monetary Fund, World Economic Outlook (inflation forecasts for projections).
- Chemical Engineering Plant Cost Index (CEPCI), Chemical Engineering magazine. https://www.chemengonline.com/pci (used by OPCI for validation only; private override in this tool)
- S&P Global capital costs indices (formerly IHS Markit).

**Analog project sources**

- Donggi-Senoro: Mitsubishi Corporation, first shipment release (2015).
- Bintulu Train 9: JGC EPCC award (2013); Offshore Technology, Petronas Bintulu LNG Complex.
- Tangguh Train 3: Indonesian Ministry of Energy and Mineral Resources, FID release (2016).
- PNG LNG: Santos release (2014); Offshore Technology project page.
- Ichthys: Hydrocarbon Processing, JKC EPC award (2012).
- Corpus Christi Trains 1-2: OIES NG137, Appendix 1.
- Rio Grande LNG Phase 1: NextDecade 8-K (July 2023) and quarterly updates.
- Nigeria LNG Train 7: Riviera; SPE (EPC award, 2020).

**Site item sources**

- PNG LNG jetty: Offshore Energy (2010). Costa Norte jetty: Hydrocarbon Engineering (2016).
- Cuyutlán dredging: Dredging Today (2010). Soyo dredging: SWZ Maritime (2010).
- GATE terminal tank: VINCI (2023). Ruwais LNG tanks: CB&I (2025).

*All factors and figures are indicative. Confirm sources before relying on any number for a real project.*
