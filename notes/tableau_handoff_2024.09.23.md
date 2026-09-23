# Tableau handoff — 2024 EAVS (jurisdiction level)

Sep 23, 2026 · @mayia li

## File and structure

The handoff file is `2024_tableau_long_candidate.xlsx`: 2024 only, 6,461 jurisdictions, same Sheet1/Sheet2 shape as the previous delivery.

| Item | Detail |
| --- | --- |
| Built by | `scripts/create_2024_tableau_long_candidate.py` (branch `work/2024-dashboard-candidate`) |
| Input | `data/cleaned/2024_dashboard_candidate.csv` |
| Sheet1 (counts) | Long format: `Metric` / `Count` (reason or source) / `Value`. 47 rows per jurisdiction (303,667 rows). |
| Sheet2 (rates) | `Metric` / `Numerator` / `Denominator`. 5 rows per jurisdiction (32,305 rows). |

Compute rates in Tableau as `SUM([Numerator]) / SUM([Denominator])`. Do not average jurisdiction rates: that gives a small county the same weight as Los Angeles.

## Metrics

New since the last delivery: Registrations Rejected, Mail Rejected and Provisional Rejected blocks, plus Mail, Provisional and Purged (EAC) rates.

| Metric | Breakdown (Sheet1) | Rate (Sheet2) |
| --- | --- | --- |
| Applicants | Registration forms by source (9) | Rejected / total received |
| Registrations Rejected | Total + 9 sources. By source, not reason: EAVS does not collect rejection reasons for registrations. | None |
| Mail Rejected | Total + 13 reasons + Other (C9r+s+t summed) | Rejected (C9a) / returned (C1b). Matches EAC dashboard. |
| Provisional Rejected | Total + 9 reasons (E3b–E3j) | Rejected (E1d) / cast (E1a). Matches EAC dashboard. |
| Purged | Total, Felony, No Response | Removed / (registered + removed). CLC logic, as in previous delivery. |
| Purged (EAC) | None | Removed (A12a) / registered (A1a). Matches EAC dashboard. |

## Verification

CA and VA match the EAC 2024 Data Interactive exactly on every measure checked. WI differs by single digits, and national totals are within 0.01%.

Internal checks: row counts verified (47 × 6,461 and 5 × 6,461), no negative values, no metric entirely blank, and reasons never exceed totals.

| Measure | State | EAC dashboard | This file | Difference |
| --- | --- | --- | --- | --- |
| Mail returned (C1b) | CA | 13,185,566 | 13,185,566 | 0 |
|  | VA | 479,139 | 479,139 | 0 |
|  | WI | 575,256 | 575,257 | +1 |
|  | National | 47,957,036 | 47,957,093 | +57 |
| Mail rejected (C9a) | CA | 123,248 | 123,248 | 0 |
|  | VA | 4,807 | 4,807 | 0 |
|  | WI | 2,824 | 2,823 | −1 |
|  | National | 584,408 | 584,463 | +55 |
| Mail rejection rate | CA / VA / WI / National | 0.9 / 1.0 / 0.5 / 1.2% | 0.9 / 1.0 / 0.5 / 1.2% | 0 |
| Provisional cast (E1a) | CA | 327,003 | 327,003 | 0 |
|  | VA | 119,249 | 119,249 | 0 |
|  | WI | 653 | 661 | +8 |
|  | National | 1,736,202 | 1,736,209 | +7 |
| Provisional rejected (E1d) | CA | 37,312 | 37,312 | 0 |
|  | VA | 7,859 | 7,859 | 0 |
|  | WI | 501 | 509 | +8 |
|  | National | 436,251 | 436,258 | +7 |
| Provisional rejection rate | CA | 11.4% | 11.4% | 0 |
|  | VA | 6.6% | 6.6% | 0 |
|  | WI | 76.7% | 77.0% | +0.3 pts |
|  | National | 25.1% | 25.1% | 0 |
| Voters removed (A12a) | CA | 3,177,057 | 3,177,057 | 0 |
|  | VA | 784,573 | 784,573 | 0 |
|  | WI | 280,744 | 280,746 | +2 |
| Purge rate, Purged (EAC) | CA / VA / WI | 12.4 / 12.3 / 7.1% | 12.4 / 12.3 / 7.1% | 0 |
| Purge rate, Purged (CLC) | CA / VA / WI | 12.4 / 12.3 / 7.1% | 11.0 / 10.9 / 6.7% | Different formula by design |

Not checked: national purge totals and rates, and registration rejections. The cause of the WI gap is unknown; its +8 appears on both cast and rejected provisional ballots.

## Caveats

- **Total rows:** each Metric includes a `Total` row. Summing `Value` across all Counts double-counts, so filter Total out or use it alone.
- **Reasons don't sum to totals:** nationally, mail 96%, provisional 83%, registrations 78%. Some jurisdictions don't report breakdowns, and some "other" categories are omitted (provisional E3k–n; registration source "Other" A7j–l). Don't show "total minus reasons" as a category.
- **Blanks are non-reporting, not zeros:** up to 81% blank in rare categories.
- **Two purge rates:** `Purged` keeps the previous CLC formula so existing views still work. `Purged (EAC)` matches the EAC dashboard and runs about 0.4–1.4 points higher.
- **Mail rate denominator:** the CLC spec's headline row lists C1a (transmitted). This file uses C1b (returned), matching the EAC.

## Open questions for Nathan

- [ ] This file is 2024 only. Do you also need 2020 and 2022 in this format, or are you pulling those from the timeseries?
- [ ] Should the dashboard show `Purged`, `Purged (EAC)`, or both?
- [ ] Was C1a (transmitted) intended as the mail rate denominator, or is C1b (returned) right?
