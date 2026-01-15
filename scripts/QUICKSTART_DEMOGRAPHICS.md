# Demographics Quick Start Guide

**For EAVS Data Prep Volunteers**

## TL;DR - First Time Setup

```bash
# 1. Download Census data (one-time, ~5 minutes)
bash scripts/setup_demographics.sh

# 2. Add demographics to EAVS data
python -m eavs.add_demographics

# 3. Verify it worked
python scripts/verify_demographics.py
```

That's it! Your enriched data is now at:
`data/cleaned/2024_cleaned_with_demographics.parquet`

---

## What Just Happened?

You added these columns to every county/jurisdiction:
- `cvap_total` - Total voting-age citizens
- `cvap_white_pct`, `cvap_black_pct`, `cvap_hisp_pct`, `cvap_asian_pct`, `cvap_aian_pct`
- `section_203_covered` - Language assistance requirement (1=yes, 0=no)

---

## Troubleshooting

### "CVAP file not found"
→ Run: `bash scripts/setup_demographics.sh`

### "Failed to download"
→ Check internet connection and try again  
→ Or manually download from links in `README_DEMOGRAPHICS.md`

### "Only XX% matched"
→ This is normal! CVAP is county-level, but EAVS includes cities/towns

### Need help?
→ Run: `python scripts/verify_demographics.py` to diagnose issues  
→ Check `README_DEMOGRAPHICS.md` for detailed docs  
→ Ask in #eavs-data-prep Slack channel

---

## Using the Demographic Data

```python
import pandas as pd

df = pd.read_parquet("data/cleaned/2024_cleaned_with_demographics.parquet")

# Example: High rejection rates in majority-minority counties
analysis = df[
    (df["rejection_rate"] > 5.0) & 
    (df["cvap_white_pct"] < 50)
]

# Example: Compare by Section 203 coverage
df.groupby("section_203_covered")["rejection_rate"].mean()
```

---

## Files You Now Have

```
scripts/
├── setup_demographics.sh           ← Run this first
└── verify_demographics.py          ← Check if it worked

eavs/
└── add_demographics.py             ← Main enrichment code

data/demographics/
├── County_CVAP_2018-2022.csv       ← Census CVAP (~18 MB)
└── section_203_2021_raw.csv        ← Section 203 coverage

data/cleaned/
├── 2024_cleaned.parquet            ← Original
└── 2024_cleaned_with_demographics.parquet  ← NEW! Use this one
```

---

## Questions?

- **What is CVAP?** Citizen Voting Age Population from Census Bureau
- **Why county-level?** That's the finest granularity Census provides for CVAP
- **What if my jurisdiction isn't matched?** Expected for sub-county jurisdictions (cities, towns)
- **Can I re-run if EAVS data updates?** Yes! Just run `python -m eavs.add_demographics` again

For detailed documentation: `README_DEMOGRAPHICS.md`