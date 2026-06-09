# EAVS Data Reference

Sources: 2022 EAVS Codebook, EAVS Time Series User Guide v1.1, 2022/2024 EAVS FINAL PDFs,
`timeseries.parquet` column list confirmed by inspection.

Column names below are snake_case as they appear in `data/cleaned/timeseries.parquet`.
Value ranges are jurisdiction-level from the 2022 codebook.
Sentinel codes: `-88` = Does Not Apply, `-99` = Data Not Available.
Always run `pd.to_numeric(df[col], errors='coerce')` before any aggregation.

---

## 1. Identifiers

| parquet column | EAVS item | Description |
|---|---|---|
| `fips_code` | FIPSCode | 5-digit Census FIPS. PA maps 1:1 to 67 counties (verified). |
| `state` | State_Full | ALL CAPS. Join to CVAP via explicit name bridge — do NOT use `.str.title()` (produces "District Of Columbia"). |
| `state_abbr` | State_Abbr | 2-letter abbreviation. |
| `jurisdiction_name` | Jurisdiction_Name | Local election jurisdiction. |
| `year` | Year | Integer: 2004, 2006, … 2022. |

---

## 2. Section A — Voter Registration

All dashboard-relevant A-section columns have **identical names in 2020 and 2022**.
Major renames happened at the 2016–2018 boundary; the timeseries handles those transparently.

| parquet column | EAVS item | Range (2022 jur.) | Description | Notes |
|---|---|---|---|---|
| `registered_eligible_voters` | A1a | 0–7,412,146 | **Total registered and eligible voters** (active + inactive). | Rates >100% of CVAP = stale rolls — flag, do not suppress. |
| `active_voters` | A1b | 0–5,618,825 | **Active voters — EAC-preferred registration denominator.** | 6 states don't distinguish active/inactive: ID, MN, NH, ND, Guam, PR — A1b may repeat A1a or be null. |
| `inactive_voters` | A1c | 0–1,793,321 | Inactive voters — require address verification under NVRA before voting. | |
| `total_registrations_received` | A3a | 0–2,267,552 | Total registration transactions received (cycle denominator). | |
| `new_valid_registrations` | A3b | 0–662,109 | New valid registrations (excl. under-18 pre-reg). | |
| `duplicate_registrations` | A3d | 0–1,594,277 | Duplicate transactions. | |
| `rejected_registrations` | A3e | 0–86,221 | **Invalid/rejected transactions. Numerator for rejection rate.** | KY ~24% = duplicate counting methodology. Negative after aggregation = sentinel artifact — null out. |
| `intrajurisdiction_registration_updates` | A3f | 0–969,032 | Address/name updates within same jurisdiction. | |
| `interjurisdiction_registration_updates` | A3g | 0–411,356 | Address changes crossing jurisdiction border. | |
| `total_forms_mail_fax_email` | A4a | 0–212,267 | Registration forms by mail/fax/email. | |
| `total_forms_in_person` | A4b | 0–132,009 | Forms received in person. | |
| `total_forms_online` | A4c | 0–457,248 | Forms via online registration. | |
| `total_forms_dmv` | A4d | 0–1,214,547 | Forms via DMV / motor voter / automatic reg. | |
| `total_forms_mandatory_nvra` | A4e | 0–122,326 | Forms via NVRA-mandated public assistance offices. | |
| `total_forms_disability_agency` | A4f | 0–12,480 | Forms via state-funded disability services agencies. | |
| `total_forms_armed_forces` | A4g | 0–3,149 | Forms via armed forces recruitment offices. | |
| `total_forms_discretionary_nvra` | A4h | 0–185,491 | Forms via other state-designated agencies (not NVRA-mandated). | |
| `total_forms_advocacy_groups` | A4i | 0–120,309 | Forms via advocacy group / political party drives. | |
| `confirmation_notices_sent_total` | A8a | 0–1,621,375 | Confirmation notices sent to verify continued eligibility. | |
| `confirmation_notices_undeliverable` | A8d | 0–170,798 | Notices returned undeliverable — stale rolls indicator. | |
| `voters_removed_total_2020_2022` | A9a | 0–340,855 | **Total voters removed from rolls (cycle). Numerator for purge rate.** | |
| `A9b` | A9b | 0–94,228 | Removed: confirmed moved. | |
| `A9c` | A9c | 0–97,491 | Removed: confirmed deceased. | |
| `voters_removed_felony` | A9d | 0–8,634 | Removed: felony conviction. | |
| `voters_removed_nonresponse` | A9e | 0–145,092 | Removed: failed confirmation + no vote in 2 federal elections (NVRA). | |
| `A9g` | A9g | 0–77,691 | Removed: voter's own request. | |

---

## 3. Section C — Mail / Absentee Voting

**Structural change warning:** The mail section was significantly restructured between 2018 and 2020.
The 2020 and 2022 names are identical — safe to aggregate.
Do not join pre-2018 mail data to 2020/2022 without the User Guide crosswalk.

| parquet column | EAVS item | Range (2022 jur.) | Description | Notes |
|---|---|---|---|---|
| `mail_transmitted_total` | C1a | 0–5,747,701 | **Total mail ballots transmitted. Denominator for mail return rate.** | |
| `mail_returned_by_voters` | C1b | 0–2,054,175 | **Mail ballots returned by voters. Denominator for mail rejection rate.** | Use as 2020 proxy for C8a where null. |
| `mail_returned_undeliverable` | C1c | 0–80,000 | Returned undeliverable — address / stale rolls indicator. | |
| `mail_voided` | C1d | 0–136,905 | Voided (e.g. voter requested replacement). | |
| `mail_voted_in_person` | C1e | 0–6,930 | Requested mail ballot but voted in person. **NOT total in-person votes.** | Only 1,476 jurisdictions reported. |
| `mail_unreturned` | C1f | 0–3,502,991 | Transmitted but not returned. | |
| `transmitted_permanent_mail_total` | C2a | 0–1,919,043 | Permanent mail voter transmissions. Subset of C1a. | |
| `drop_boxes_total` | C3a | 0–400 | Total drop boxes. | **New in 2022 — null for 2020.** |
| `mail_ballots_counted` | C8a | 0–1,961,748 | **Mail ballots counted. Component of F1a.** | Many jurisdictions null in 2020 — use C1b as proxy. |
| `mail_ballots_rejected_total` | C9a | 0–92,427 | **Total mail ballots rejected. Numerator for mail rejection rate.** | Null for many states in 2020. |
| `mail_ballots_rejected_late` | C9b | 0–14,538 | Rejected: arrived after deadline. | |
| `mail_ballots_rejected_missing_voter_signature` | C9c | 0–3,268 | Rejected: missing voter signature. | |
| `mail_ballots_rejected_missing_witness_signature` | C9d | 0–687 | Rejected: missing witness/notary signature. | |
| `mail_ballots_rejected_non_matching_voter_signature` | C9e | 0–10,217 | Rejected: non-matching signature. | |
| `mail_ballots_rejected_no_secrecy_envelope` | C9h | 0–1,820 | Rejected: missing secrecy envelope. | |
| `mail_ballots_rejected_voter_already_voted` | C9n | 0–2,428 | Rejected: already voted. | |
| `mail_ballots_rejected_voter_not_eligible` | C9p | 0–3,628 | Rejected: not eligible in jurisdiction. | |

---

## 4. Section E — Provisional Ballots

**Rename warning:** Detailed provisional rejection subcategories (E3b–E3n) were called E2b–E2n
in 2020 and E3b–E3n in 2022. The timeseries handles this transparently.
Use E1d (not E3a) as the primary rejection total — it is stable across all years and has fewer anomalies.

| parquet column | EAVS item | 2020 raw | 2022 raw | Range (2022 jur.) | Description | Notes |
|---|---|---|---|---|---|---|
| `provisional_ballots_cast_total` | E1a | E1a | E1a | 0–16,324 | **Total provisional ballots cast. Denominator for provisional rejection rate.** | |
| `provisional_ballots_fully_counted` | E1b | E1b | E1b | 0–12,161 | **Fully counted. Component of F1a.** | |
| `provisional_ballots_partially_counted` | E1c | E1c | E1c | 0–4,769 | Partially counted. | |
| `provisional_ballots_rejected_total` | E1d | E1d | E1d | 0–5,504 | **Total rejected. Numerator for provisional rejection rate. USE THIS.** | ME 2020 and SD 2022 anomalous — null out. |
| `provisional_ballots_rejected_total_2` | E3a | E2a | E3a | 0–67,796 | Restatement of E1d with different question framing. **Use E1d instead.** | Renamed between 2020 and 2022. |
| `provisional_ballots_cast_voter_not_on_list` | E2a | E2a | E2a | 0–9,687 | Cast: not found on poll list. | |
| `provisional_ballots_cast_voter_lacked_id` | E2b | E2b | E2b | 0–772 | Cast: lacked required ID. | |
| `provisional_ballots_cast_registration_not_updated` | E2f | E2f | E2f | 0–2,057 | Cast: registration not updated in time. | |
| `provisional_ballots_rejected_not_registered` | E3b | E2b | E3b | 0–2,556 | Rejected: not registered. | |
| `provisional_ballots_rejected_wrong_jurisdiction` | E3c | E2c | E3c | 0–1,064 | Rejected: wrong jurisdiction. | |
| `provisional_ballots_rejected_wrong_precinct` | E3d | E2d | E3d | 0–920 | Rejected: wrong precinct. | |
| `provisional_ballots_rejected_no_id` | E3e | E2e | E3e | 0–352 | Rejected: no ID. | |
| `provisional_ballots_rejected_incomplete` | E3f | E2f | E3f | 0–461 | Rejected: incomplete/unsigned envelope. | |

---

## 5. Section F — Voter Turnout ★

**CRITICAL: F1a definition changed at the 2018–2020 boundary.**
- 2004–2018: "ballots cast" (regardless of whether counted)
- 2020–2022: "ballots cast AND COUNTED"
- **Do not compare F1a across the 2018–2020 boundary without adjustment.**
- Within 2020 and 2022 the definition is identical — comparisons are valid.
- All F-section column names are stable and identical in 2020 and 2022.

| parquet column | EAVS item | Range (2022 jur.) | Description | Notes |
|---|---|---|---|---|
| `F1a` | F1a | 0–2,456,701 | **TOTAL ballots cast and counted — all modes, all voter types. PRIMARY TURNOUT NUMERATOR. Use directly; do not construct from components.** | Verified: 2022 national sum = 112,053,409 vs EAC ~112M (<0.05%). |
| `F1b` | F1b | 0–426,224 | Election Day in-person. Excl. provisional and mail dropped off at polls. | |
| `F1c` | F1c | 0–10,565 | UOCAVA (military/overseas) absentee + FWAB. | |
| `F1d` | F1d | 0–1,307,815 | Mail ballots counted (non-universal-mail jurisdictions). | |
| `F1e` | F1e | 0–13,620 | Provisional ballots counted (fully or partially). | |
| `F1f` | F1f | 0–687,869 | In-person early voting. | PA cannot report F1f — not tracked separately. F1a still complete for PA. |
| `F1g` | F1g | 0–1,961,748 | Mail ballots in universal vote-by-mail jurisdictions (OR, WA, CO, HI, UT). | Only 645 jurisdictions reported. |
| `F1h` | F1h | 0–239,979 | Other ballot types. | |

---

## 6. Sentinel / Missing Value Codes

| Code | Meaning | pandas handling |
|---|---|---|
| `-88` or `-888888` | Does Not Apply | `pd.to_numeric(errors='coerce')` → NaN |
| `-99` or `-999999` | Data Not Available | `pd.to_numeric(errors='coerce')` → NaN |
| `-55` | Not covered in Policy Survey year | `pd.to_numeric(errors='coerce')` → NaN |
| `-77` | Valid skip | `pd.to_numeric(errors='coerce')` → NaN |

**Always** apply conversion before any `.sum()`, `.mean()`, or rate calculation.
Negative values after aggregation = sentinels not filtered — null out the result.

---

## 7. Derived Rates for Dashboard

| Rate | Formula (parquet column names) | Notes |
|---|---|---|
| Registration rate (total) | `registered_eligible_voters / cvap_est` | Current dashboard. Rates >100% = stale rolls — flag, do not suppress. |
| **Registration rate (active)** | `active_voters / cvap_est` | EAC-preferred. 6 states can't report A1b separately. |
| Turnout rate | `F1a / registered_eligible_voters` | Use F1a directly. Verified against EAC 2022 report. |
| Registration rejection rate | `rejected_registrations / total_registrations_received` | KY ~24% = duplicate counting. Negative = sentinel artifact, null out. |
| Purge rate | `voters_removed_total_2020_2022 / registered_eligible_voters` | |
| Mail rejection rate | `mail_ballots_rejected_total / mail_returned_by_voters` | C9a / C1b. Null for many states in 2020. |
| Provisional rejection rate | `provisional_ballots_rejected_total / provisional_ballots_cast_total` | E1d / E1a. ME and SD anomalous — null out. |
| Mail return rate | `mail_returned_by_voters / mail_transmitted_total` | C1b / C1a. |

---

## 8. External Join — ACS CVAP (State.csv)

File: `data/external/CVAP_2020-2024_ACS_csv_files/State.csv`

| column | Description |
|---|---|
| `geoname` | Full state name, title case. Join key after name bridge from EAVS ALL CAPS. |
| `lntitle` | Race/ethnicity group. Filter `'Total'` for overall CVAP. |
| `cvap_est` | CVAP point estimate. Denominator for registration and turnout rates. |
| `cvap_moe` | Margin of error. |

**Name bridge required:** EAVS `state` = ALL CAPS → CVAP `geoname` = title case.
**Do NOT use `.str.title()`** — produces "District Of Columbia" (wrong). Use an explicit mapping dict.

**CVAP vintage:** State.csv = ACS 2018–2022 5-year estimates applied to both cycles.
EAC 2022 report uses 1-year ACS. 5-year estimates are an acceptable approximation for the dashboard.

**Race categories in `lntitle` (for Page 2):**
`Total` · `White Alone` · `Black or African American Alone` · `Hispanic or Latino` ·
`Asian Alone` · `American Indian or Alaska Native Alone` ·
`Native Hawaiian or Other Pacific Islander Alone` ·
`Remainder of Two or More Race Responses`

---

## 9. Known Data Quality Issues

| Issue | Affected | Action |
|---|---|---|
| Registration rate >100% | DC, AK, IL, MI, KY, CA, CO, MD, ME | Flag "stale rolls" in UI — do not suppress |
| Negative rejection rates after aggregation | WI, CT, AR, OR, SC, MO | Null out — sentinel codes summed to negative |
| KY registration rejection ~24% | KY | Flag "duplicate counting methodology" — not true rejections |
| ME provisional rejection rate | ME 2020 (~−2187), ME 2022 (~62) | Null out both values |
| SD provisional rejection rate | SD 2022 (~−17) | Null out |
| ND — no voter registration | ND | A1a, A1b null; display "No registration" label |
| Active/inactive not distinguished | ID, MN, NH, ND, Guam, PR | A1b may repeat A1a or be null; fall back to A1a with caveat |
| PA F1f not tracked separately | PA | F1f null for PA; F1a still complete and correct |
| C8a (mail counted) null in 2020 | Most states | Use C1b (mail returned) as 2020 proxy |
| C3a (drop boxes) not in 2020 | All states | First collected 2022; expect null for 2020 |
| F1a definition changed in 2020 | All pre-2020 years | Pre-2020 = ballots cast (not counted) — do not compare across 2018/2020 boundary |
| E1d vs E3a duplication | All | Both = provisional rejected total; use E1d only |
| CVAP vintage mismatch | All states | 2018–2022 ACS applied to both cycles — acceptable approximation |

---

## 10. State-Level Data Structure Notes (from Timeseries User Guide)

| State/Region | Issue | Years affected |
|---|---|---|
| **Wisconsin** | Reported county-level (2004–2010), ward-level (2012–2014), jurisdiction-level (2016–2022) | Pre-2016 not comparable to 2020/2022 |
| **CT, ME, MA, NH, RI, VT** | Township-level all years except 2006 (county). 2006 not disaggregatable. | 2006 only |
| **New York** | State-level in 2008; NYC as single jurisdiction in 2004–2006 | 2004–2008 |
| **North Dakota** | No voter registration system — A1a and A1b always null | All years |
| **Various WI jurisdictions** | Towns incorporated into villages — names standardised to most recent in timeseries | Pre-rename years |
