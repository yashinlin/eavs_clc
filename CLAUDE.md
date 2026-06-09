# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install/sync dependencies
uv sync

# Download raw EAVS data (requires network; saves to data/raw/)
uv run -m eavs.download

# Run the full cleaning pipeline
uv run -m eavs.clean

# Run the full pipeline (clean → aggregate → CPS → dashboard)
uv run run_pipeline.py

# Run individual pipeline stages
uv run -m eavs.clean_timeseries
uv run -m eavs.aggregate
uv run -m eavs.clean_cps
uv run -m eavs.build_dashboard
uv run -m eavs.build_dashboard_p2

# Lint and format
just lint       # ruff format --check && ruff check
just format     # ruff format && ruff check --fix

# Run tests
uv run pytest

# Launch Jupyter for notebooks
uv run jupyter lab
```

## Architecture

### Pipeline stages (in order)

1. **`eavs/download.py`** — Downloads raw EAVS `.xlsx` files from the EAC website using a manifest (`eavs/assets/manifest.jsonl`). Verifies SHA256 checksums. Saves to `data/raw/{year}/{version}/`.

2. **`eavs/clean.py`** — Loads raw xlsx for each survey year (2020, 2022, 2024), renames columns using year-specific YAML mappings in `eavs/assets/column_mappings/`, converts sentinel negatives to `NaN`, and saves per-year and combined cleaned parquets to `data/cleaned/`. Also triggers `clean_timeseries`.

3. **`eavs/clean_timeseries.py`** — Cleans the pre-built EAVS time-series dataset (`data/raw/timeseries/1.0/`). Uses `eavs/assets/column_mappings/timeseries.yaml` (falls back to aggregating all year YAMLs). Validates against `eavs/assets/timeseries_process_schema.yaml` and saves `data/cleaned/timeseries.parquet`.

4. **`eavs/aggregate.py`** — Reads `data/cleaned/timeseries.parquet` and an external CVAP file (`data/external/CVAP_2020-2024_ACS_csv_files/State.csv`), aggregates to state level, computes registration and turnout rates, saves to `data/processed/state_rates.parquet`. Currently filters to years 2020/2022 only.

5. **`eavs/clean_cps.py`** — Reads CPS Voting Supplement xlsx files from `data/external/CPS_voting/`, harmonizes demographic labels across years, and saves to `data/processed/cps_voting_clean.parquet`.

6. **`eavs/build_dashboard.py`** — Reads `data/processed/state_rates.parquet`, renders a self-contained HTML dashboard (Page 1: voter registration/turnout by state) to `data/processed/eavs_dashboard_page1.html`.

7. **`eavs/build_dashboard_p2.py`** — Produces Page 2 of the dashboard.

### Column mapping system

Each survey year has a YAML file in `eavs/assets/column_mappings/` that maps raw EAVS question codes (e.g. `A1a`, `C9b`) to harmonized project variable names. Each entry requires `raw_name`, `name`, and `dtype`.

**Active mapping files:**
- `2020.yaml`, `2022.yaml` — canonical, used by the pipeline
- `timeseries.yaml` — for the cross-year timeseries dataset
- `2024_3_corrected_expanded_no_derived.yaml` — the authoritative 2024 mapping (149 columns). The others (`2024_1_original.yaml`, `2024_2_clc_subset.yaml`) are retained for provenance only.

**Important:** The pipeline `clean.py` currently loads by filename convention (`{year}.yaml`), so there is no `2024.yaml` wired in yet. 2024 candidate work should happen via one-off scripts or notebooks reading `2024_3_corrected_expanded_no_derived.yaml` directly — do not edit pipeline files to point at it without explicit instruction.

### FIPS code handling

Raw EAVS `FIPSCode` is a **10-digit composite** (2-digit state + 3-digit county + 5-digit sub-county). The current `clean.py` truncates to 5 digits, which destroys sub-county identity. Any work requiring sub-county granularity (New England, MI, MN, WI) must read raw data with `dtype=str` + `zfill(10)` rather than going through the cleaned pipeline output.

### Sentinel values

EAVS uses negative sentinels: `-99` (not available), `-88` (not applicable), `-77` (valid skip), `-66` (not in survey year). The cleaning pipeline converts these to `NaN`. When computing rates: sum raw counts to the target aggregation level first, then compute ratios — never average per-jurisdiction rates.

### Data directories

```
data/
  raw/           # Immutable source files (gitignored)
  cleaned/       # Outputs of clean.py and clean_timeseries.py
  processed/     # Outputs of aggregate.py, clean_cps.py, build_dashboard.py
  external/      # External reference data (CVAP, CPS)
```

### `eavs/config.py`

Defines all path constants (`PROJ_ROOT`, `DATA_DIR`, `RAW_DATA_DIR`, `CLEANED_DATA_DIR`, `PROCESSED_DATA_DIR`, `EXTERNAL_DATA_DIR`, `CPS_DATA_DIR`). Import from here rather than constructing paths ad-hoc.

### Scripts vs. pipeline

`scripts/` contains one-off analysis scripts for 2024 dashboard candidates. These are not part of the main pipeline and are run directly with `uv run scripts/<name>.py`. Finalized transformations should be promoted to `eavs/` modules.

### Current branch context

Branch `work/2024-dashboard-candidate` is actively developing 2024 dashboard output via the scripts in `scripts/`. The canonical pipeline (`run_pipeline.py`) has not been updated to include 2024 yet.

## Dashboard architecture

**Page 1** (built, `data/processed/eavs_dashboard_page1.html`): Administrative barriers — EAVS only, no race breakdown. Registration rate, turnout rate by state. Story: "Where are administrative processes creating barriers?"

**Page 2** (not yet built): Participation equity by race. Data source: CPS Voting Supplement Table 4b × ACS CVAP. Race-disaggregated registration and turnout rates. EAVS administrative rates shown as context only. Story: "Where are racial participation gaps largest?"

These pages use **different data sources** and EAVS does NOT break down by race — CPS is the only source for Page 2.

**Audience:** Primary — William Penn Foundation (civic engagement, PA/Philadelphia focus). Secondary — election administrators, journalists, researchers. Framing: "participation pipeline", "eligible citizens" (not "CVAP"). Target hosting: Streamlit Community Cloud (zero cost, public GitHub repo).

## EAVS data reference

Full column definitions, value ranges, sentinel codes, and rate formulas are in [EAVS_DATA_REFERENCE.md](EAVS_DATA_REFERENCE.md). Critical facts that affect code:

- **Turnout numerator: use `F1a` directly.** It is total ballots cast and counted across all modes (Election Day in-person F1b, early in-person F1f, mail F1d+F1g, counted provisional F1e, UOCAVA F1c). Never construct it from components.
- **F1a definition changed at 2018–2020 boundary.** Pre-2020: "ballots cast". 2020+: "ballots cast AND counted". Do not compare across that boundary.
- **Registration denominator: `registered_eligible_voters` (A1a) vs `active_voters` (A1b).** EAC prefers A1b; current pipeline uses A1a. Six states (ID, MN, NH, ND, Guam, PR) do not distinguish active/inactive.
- **CVAP join requires explicit name bridge.** EAVS `state` = ALL CAPS; CVAP `geoname` = title case. Do NOT use `.str.title()` — produces "District Of Columbia". Use a dict.
- **Provisional rejection total: use `provisional_ballots_rejected_total` (E1d), not `provisional_ballots_rejected_total_2` (E3a).** E3a was renamed from E2a between 2020 and 2022; E1d is stable across all years.
- **Negative values after aggregation = sentinel artifact.** Always `pd.to_numeric(errors='coerce')` before `.sum()`. Null out any negative rates in output.
- **Rates >100% are real data** (stale voter rolls). Flag in UI; do not suppress.
- **Section C (mail) pre-2018 data is not comparable** to 2020/2022 — structural rename at 2018–2020 boundary. The timeseries handles 2020/2022 transparently.

## Confirmed data facts (as of 2026-06-07)

- **`data/cleaned/timeseries.parquet`** is the canonical source for Page 1. It covers 2004–2022, 57,668 rows, 480 columns. Columns `F1a` and `registered_eligible_voters` are confirmed present.
- **F1a = total ballots cast, all modes** — confirmed against EAVS survey docs (Section F, Q F1a). Includes: Election Day in-person (F1b), early in-person (F1f), mail (F1d + F1g), counted provisional (F1e), UOCAVA (F1c). Use F1a as turnout numerator, not a subset.
- **Verification:** `data/processed/state_rates.parquet` national 2022 F1a total = 112,053,409. EAC official report states ~112M. Difference ~0.05% — data is correct. TX 2022 turnout = 46.1% (not the ~2% that would result from mail+provisional only).
- **CVAP path confirmed:** `data/external/CVAP_2020-2024_ACS_csv_files/State.csv` (ACS 2018–2022 5-year estimates) exists and joins correctly on state name after title-casing.

## Current state of data/processed/ files (as of 2026-06-08)

| File | Date | Status |
|---|---|---|
| `state_rates.parquet` | Jun 3 | Has F1a, registration_rate, turnout_rate. Read by `build_dashboard.py`. |
| `eavs_dashboard_page1.html` | Jun 4 | Existing dashboard — built from state_rates.parquet. Has correct turnout. **Not** the "enhanced" version planned for session 2. |
| `eavs_state_f1a.csv` | Jun 6 | Richer aggregation with mail/provisional/rejection columns. **Not yet wired into build_dashboard.py.** |
| `eavs_dashboard_page2.html` | Jun 4 | Exists but provenance unclear — predates CPS clean data work. |

**Clarification on the session 2 handoff doc (2026-06-07):** The handoff claimed a "production Page 1 dashboard" was saved to `eavs_page1_dashboard.html`. That file does **not exist** — the session was interrupted before this was produced. The F1a fix and the correct `state_rates.parquet` were already in place before that session. What the session did produce is `eavs_state_f1a.csv` (Jun 6) with additional metric columns. The enhanced dashboard (with rejection rates, purge rates, richer tooltips, etc.) was **not built**.

## Open issues (as of 2026-06-07)

### Data quality issues — investigate before production use

1. **Negative rejection rates** — States including WI, CT, AR, OR, SC, MO show negative `rejected_registrations` after timeseries aggregation. Likely caused by corrections/amendments in later survey years summing to a net negative. Investigate at jurisdiction level before displaying `reg_rejection_rate`.

2. **Maine provisional rejection rate** — Shows −2186.8 in 2020 and 62.3 in 2022. Suppress or null out `prov_rejection_rate` for ME until resolved.

3. **South Dakota provisional** — Shows −16.6 in 2022. Same sentinel/aggregation artifact. Suppress.

4. **Kentucky registration rejection rate** — ~24% is due to duplicate counting in how KY reports, not true rejections. Add a note/footnote rather than suppressing.

5. **CVAP vintage** — `State.csv` uses ACS 2018–2022 5-year estimates for both election years. Ideally use 2016–2020 for the 2020 election and 2018–2022 for 2022.

6. **Denominator choice** — `eavs/aggregate.py` uses `registered_eligible_voters` (maps to `A1a` = total registered). EAC prefers `A1b` (active voters only). Unresolved; document the choice when publishing.

### `eavs/aggregate.py` — reconciliation needed

- Module currently saves to `state_rates.parquet`; the produced data file is `eavs_state_f1a.csv`. Reconcile output path before wiring into `run_pipeline.py`.

## Immediate next tasks (as of 2026-06-08)

1. **Wire `eavs_state_f1a.csv` into `build_dashboard.py`** — update INPUT_PATH to read the CSV (or convert to parquet), add the additional metric columns, and regenerate `eavs_dashboard_page1.html`.
2. Fix negative rejection rates — investigate timeseries aggregation at jurisdiction level for affected states before exposing rejection rate metrics on the dashboard.
3. Null out anomalous provisional rejection rates (ME, SD) before displaying.
4. Commit updated `eavs_dashboard_page1.html` and the new `build_dashboard.py` to repo.
5. **Download CPS Table 4b** for Page 2 source data:
   - 2022: `p20-586` table at census.gov/data/tables/time-series/demo/voting-and-registration/
   - 2020: `p20-585` table at same URL
   - Target: "Table 4b — Reported Voting and Registration by Sex, Race and Hispanic Origin, for States"
5. **Add 2024 data** — `data/raw/2024/1.0/2024_EAVS_for_Public_Release_V1_xlsx.xlsx` exists. Needs cleaning and integration into `clean_timeseries.py` before 2024 can appear on dashboards.
