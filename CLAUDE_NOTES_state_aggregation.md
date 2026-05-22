# CLAUDE notes — EAVS state-level aggregation (2024)

> **STATUS: OBSOLETE (as of 2026-05-22).** The 9-cell aggregation plan,
> derived-formula scaffolding, and "Exact next steps on resume" sections
> below are superseded by the architecture decision recorded in the
> "Current architecture" section immediately following this header. The
> historical content is preserved unedited for provenance — do not act on
> it.

## Current architecture (2026-05-22)

- **YAML scope**: mapping files in `eavs/assets/column_mappings/` hold
  raw/harmonized variable mappings ONLY. No `derived_columns:` blocks. No
  rate/ratio/indicator formulas.
- **Indicator layer**: Tableau owns derived/dashboard calculations
  downstream. Do not duplicate that logic in YAML or in the cleaning
  pipeline.
- **Notebook role**: `notebooks/1.4 variable lookup.ipynb` (and siblings)
  are for validation / QA / exploration. They are NOT production
  transformation logic.
- **Active 2024 mapping**: `2024_3_corrected_expanded_no_derived.yaml`
  (149 columns, no derived formulas). Other 2024 YAMLs
  (`2024_1_original.yaml`, `2024_2_clc_subset.yaml`) are retained for
  provenance only — do not use them as the active mapping.
- **Pipeline files** (`eavs/clean.py`, `run_pipeline.py`) still reference
  the deleted `2024.yaml`. Pipeline repointing is deferred. Do NOT modify
  pipeline files. Cleaned-dataset generation for the candidate YAML must
  happen outside the existing pipeline via a one-off script or notebook
  cell — the goal is to test the candidate YAML without changing
  canonical pipeline behavior.
- **Immediate goal**: generate and validate a cleaned 2024-only candidate
  dataset against `2024_3_corrected_expanded_no_derived.yaml`. Compare
  aggregated totals against EAC publications. Avoid full timeseries
  integration for now.

Everything below this section is historical record from sessions on
2026-05-20 / 2026-05-21 and predates this architecture call.

---

## [HISTORICAL — superseded 2026-05-22] Original working notes

Working notes. Author: working sessions 2026-05-20, 2026-05-21.

## EAVS FIPSCode structure

- Raw `FIPSCode` is a **10-digit composite administrative identifier**, not a
  Census GEOID. Sources: 2024 EAVS Data Template User Guide; EAVS Time Series
  User Guide v1.1 (cited in `notebooks/1.2.EDA FIPS check.ipynb`).
- Layout: chars 1–2 state FIPS, chars 3–5 county FIPS, chars 6–10 sub-county
  component (MCD / town / place / consolidated city, EAC-assigned).
- Leading zeros stripped by Excel — load with `dtype=str` + `zfill(10)`.
- Most states report at county level (sub-county component zero-padded).
  New England + MI + MN + WI report at sub-county. WI has the largest 2024
  row count (1,851).

## Risks of the 5-digit truncation in `clean.py`

`eavs/clean.py:129` does `df["fips_code"] = df["fips_code"].astype(str).str.zfill(5).str[:5]`.
Destructive for downstream analysis (sub-county identity lost, cross-state
collisions, not actually a Census GEOID). Pipeline fix deferred — notebook-first
work is on raw 10-digit FIPSCode. See `notebooks/1.2.EDA FIPS check.ipynb`
for sub-county geography linkage WIP.

## Notebook-first decision

Pipeline files (`eavs/clean.py`, `eavs/clean_timeseries.py`,
`eavs/assets/column_mappings/2024.yaml`) are **not** being edited. State-level
aggregation work lives in `notebooks/1.4 variable lookup.ipynb`, reading raw
2024 xlsx directly and using a separate corrected YAML.

## Counts-first-rates-after rule

For every rate-shaped indicator: sum the raw counts to the state level with
`groupby('State_Abbr').sum(min_count=1)`, then compute the ratio on the
aggregated frame. `min_count=1` keeps all-NaN groups as NaN. Never average
per-jurisdiction rates. This is mathematically equivalent to evaluating the
ratio expression on already-summed columns via `state_counts.eval(expr)`
because numerator/denominator are linear in counts.

---

## Session 2026-05-20 / 2026-05-21 — decisions made

1. **Target notebook**: `notebooks/1.4 variable lookup.ipynb` (not 1.3).
2. **Indicator source of truth**: inline Python dicts (`COUNT_VARS_RAW`,
   `RATE_FORMULAS_RAW`) in the notebook. The YAML's `derived_columns:` is
   informational only and is used for column mapping only.
3. **YAML to use**: `eavs/assets/column_mappings/2024_corrected.yaml`
   (untracked file added this session). Existing pipeline still points at
   `2024.yaml` — untouched.
4. **Aggregation key**: `State_Abbr` (raw name, preserved).
5. **Non-state jurisdictions** (`AS`, `GU`, `MP`, `PR`, `VI`, `DC`): kept
   in the groupby.
6. **Identifier preservation**: `FIPSCode`, `State_Abbr`, `Jurisdiction_Name`
   preserved as raw column names. `State_Full` renamed to `state` via the
   YAML map.
7. **Sentinel policy**: empty placeholder (user to fill later).
8. **Divide-by-zero**: coerce `inf` / `-inf` to `NaN` after rate
   computation.
9. **Duplicate rate-rows in user's table** (`A12e/(A1a+A12a)` and
   `A12e/A12a` each appeared twice) deduped.
10. **`C9r`, `C9s`, `C9t` added to `COUNT_VARS_RAW`** so the derived count
    `C9r+C9s+C9t` and its two ratios can compute. Not in the user's
    original variable rows.
11. **Additive expressions** (`+`-only, no `/`) handled uniformly with
    ratios via `state_counts.eval(translated_expression)`.

## Corrected YAML strategy

- File: `eavs/assets/column_mappings/2024_corrected.yaml`. Untracked.
- Contains `columns:` (88 entries, including new A8b/c/f-j, A10*, A12*,
  A4j/A5j/A6j absent from the original `2024.yaml`) and `derived_columns:`
  (69 entries with `name`, `formula`, `raw_formula`, `description`).
- Internal consistency verified: every `formula:` (clean-name) matches its
  `raw_formula:` (raw EAVS code) under the `columns:` mapping.
- The inline `RATE_FORMULAS_RAW` (67 unique entries after dedup) is a
  strict subset of the YAML's `derived_columns.raw_formula` set. The YAML
  has 2 extra entries that the user did not exclude — they got merged in
  when the user supplied the comprehensive variable+formula table.
- Decision pending later: whether to promote `2024_corrected.yaml` to
  replace `2024.yaml` in the pipeline. Not in scope for this session.

## Current repo status (end of 2026-05-21 session)

Branch: `fix/tuan-review` (up to date with origin).

Modified (uncommitted, pre-existing changes from prior sessions, **not**
touched this session):

- `README.md`
- `eavs/clean.py`
- `eavs/clean_timeseries.py`
- `pyproject.toml`
- `run_pipeline.py`
- `uv.lock`

Untracked (new this session and prior):

- `.github/`
- `CLAUDE_NOTES_state_aggregation.md` (this file)
- `eavs/assets/column_mappings/2024_corrected.yaml`

**`notebooks/1.4 variable lookup.ipynb`**: currently has 3 prototype cells
(YAML load using the old `2024.yaml`; sample SELECTED_RAW_CODES → COUNT_VARS
demo; empty cell). The full 9-cell aggregation workflow was **not** applied
— the user paused notebook edits before they took effect. Notebook is
in its pre-session state.

No edits to pipeline files. No output files written.

## Planned 9-cell layout for the notebook (to apply on resume)

Apply by replacing the 3 existing cells (ids `51da8ec6`, `03e35cac`,
`90d3d120`) and inserting 6 new cells after `90d3d120` in reverse
declaration order.

| # | Cell | Content (summary) |
|---|------|-------------------|
| 0 | Replace `51da8ec6` | Imports (`pathlib`, `re`, `numpy`, `pandas`, `yaml`); raw 2024 load with `dtype=str` on identifier cols; `FIPSCode.str.zfill(10)`. |
| 1 | Replace `03e35cac` | YAML load from `2024_corrected.yaml`; build `variable_lookup` DataFrame with `original_name`, `clean_name`, `description`, `dtype`; build `RAW_TO_CLEAN` dict. |
| 2 | Replace `90d3d120` | Apply YAML renames excluding the 3 preserved-raw identifiers; print summary of renames/unmapped/preserved. |
| 3 | Insert | `COUNT_VARS_RAW` literal (84 codes = 81 user-listed + C9r/C9s/C9t); assert each in `RAW_TO_CLEAN`; build `COUNT_VARS` (clean names); assert each in `df.columns`. |
| 4 | Insert | `RATE_FORMULAS_RAW` literal (67 unique entries); tokenize via `\b[A-Z]\d+[a-z]?\b`; assert tokens ⊆ `COUNT_VARS_RAW`; translate to `RATE_FORMULAS` (clean-name expressions). |
| 5 | Insert | Sentinel policy placeholder: `SENTINEL_VALUES = []`, `SENTINEL_COLUMNS = None`, `COERCE_TO_NUMERIC = True`, `GROUPBY_MIN_COUNT_1 = True`. |
| 6 | Insert | Aggregation: apply sentinel policy (no-op when empty); `pd.to_numeric(errors='coerce').astype('float64')` on `COUNT_VARS`; `groupby('State_Abbr')[COUNT_VARS].sum(min_count=1)`; for each rate, `state_counts[name] = state_counts.eval(expr)`; coerce `[inf, -inf]` → `NaN` on rate columns. |
| 7 | Insert | Validation placeholder: `EXPECTED_STATE_TOTALS = {}`, tolerance knobs, `STRICT_VALIDATION = False`; comparison code runs only if dict is non-empty. |
| 8 | Insert | Display: `state_counts.shape`, `state_counts.head(10)`, side table `jurisdiction_diag` (one row per `State_Abbr` with `row_count`, `example_fips`, `example_jurisdiction`). |

Exact code for each cell was drafted in-session and is reproducible from
this spec; no other state needed.

## Unresolved questions (still open)

1. **Sentinel policy values** — what raw-2024 sentinels (numeric like
   `-99`/`-88`, strings like `"Does not apply"` / `"Valid skip"`) should be
   replaced with NaN, and on which columns. Currently empty placeholder.
2. **Validation ground truth** — does EAC publish a machine-readable
   state-totals appendix for 2024, or must cross-checks be done against the
   PDF tables manually? `EXPECTED_STATE_TOTALS` is empty.
3. **Output target** — display-only for now; no decision yet on whether to
   write `state_counts` to `data/processed/<...>.parquet|csv` and what
   filename convention to use.
4. **Sub-county geography linkage** — not in scope here; tracked in
   `notebooks/1.2.EDA FIPS check.ipynb`. State-level aggregation does not
   require it, but any sub-state analysis will.
5. **Whether to promote `2024_corrected.yaml`** to replace `2024.yaml` in
   the pipeline — deferred.
6. **Inactive vs. active voters across years** — `A1c` (inactive) is
   `float64` in the YAML; comparing totals across 2020/2022/2024 may need
   care about whether totals include inactive in each year's questionnaire
   wording. Out of scope here.

## Exact next steps on resume

1. Re-read `notebooks/1.4 variable lookup.ipynb` to confirm the 3 prototype
   cells (ids `51da8ec6`, `03e35cac`, `90d3d120`) are still present.
2. Apply the 9-cell layout from the table above (3 replaces, then 6 inserts
   anchored to `90d3d120` in reverse declaration order: Display →
   Validation → Aggregation → Sentinel → RATE_FORMULAS → COUNT_VARS).
3. Execute the notebook top-to-bottom and verify:
   - `raw_df.shape` matches expected 2024 row count
   - `variable_lookup` has 88 rows
   - `COUNT_VARS_RAW` resolves cleanly (84 codes, 0 missing)
   - `RATE_FORMULAS_RAW` resolves cleanly (67 entries, 0 missing tokens)
   - `state_counts.shape` is `(57, 84 + 67)` — 50 states + DC + 5
     territories + 1 federal, by 84 counts + 67 rate columns. Note: the
     exact row count depends on whether all `State_Abbr` values are
     present in the raw frame; cross-check before assuming 57.
4. Spot-check 2–3 high-population states (CA, TX, NY) against an EAC
   published state-totals source.
5. Decide on output write target.
6. Do not edit pipeline files. Do not write output files yet.

## Recommended resume prompt

> Resume from `CLAUDE_NOTES_state_aggregation.md`. The plan is to apply the
> 9-cell layout to `notebooks/1.4 variable lookup.ipynb` per the table in
> the "Planned 9-cell layout" section. Start by re-reading the notebook to
> confirm the 3 prototype cells (`51da8ec6`, `03e35cac`, `90d3d120`) are
> still present, then execute the edits: 3 replaces, then 6 inserts
> anchored to `90d3d120` in reverse declaration order. Do not edit pipeline
> files (`eavs/clean.py`, `eavs/clean_timeseries.py`, the original
> `2024.yaml`), do not write output files, do not run terminal diagnostics
> against the raw data. After the cells are in, run the notebook
> end-to-end and report the four verification checks listed in the "Exact
> next steps on resume" section.
