"""
Add CVAP racial demographics + Section 203 flag to cleaned EAVS data.

Setup required (one-time):
    bash scripts/setup_demographics.sh

Usage:
    python -m eavs.add_demographics
"""

import pandas as pd
from pathlib import Path
from loguru import logger
import sys

PROJ_ROOT = Path(__file__).resolve().parent.parent


def add_demographics(df: pd.DataFrame, year: int = 2024) -> pd.DataFrame:
    demo_dir = PROJ_ROOT / "data" / "demographics"

    # =========================================================
    # 1. LOAD + PROCESS CVAP (county-level)
    # =========================================================
    cvap_path = demo_dir / "County_CVAP_2018-2022.csv"

    if not cvap_path.exists():
        raise FileNotFoundError(
            f"Missing {cvap_path}. Run: bash scripts/setup_demographics.sh"
        )

    logger.info("Loading CVAP county data...")

    cvap = pd.read_csv(
        cvap_path,
        encoding="latin1",
        low_memory=False,
    )
    cvap.columns = cvap.columns.str.lower()

    # Map Census race labels → internal names
    RACE_MAP = {
        "Total": "total",
        "White Alone": "white",
        "Black or African American Alone": "black",
        "Asian Alone": "asian",
        "American Indian or Alaska Native Alone": "aian",
        "Hispanic or Latino": "hispanic",
    }

    cvap["lntitle"] = cvap["lntitle"].str.strip()

    cvap = cvap[cvap["lntitle"].isin(RACE_MAP)].copy()

    cvap["county_fips"] = (
        cvap["geoid"]
        .str.replace("0500000US", "", regex=False)
        .str.zfill(5)
    )

    cvap_wide = (
        cvap.assign(race=cvap["lntitle"].map(RACE_MAP))
        .pivot_table(
            index="county_fips",
            columns="race",
            values="cvap_est",
            aggfunc="first",
        )
        .reset_index()
    )

    total = cvap_wide["total"].replace(0, pd.NA)

    for race in ["white", "black", "asian", "aian", "hispanic"]:
        cvap_wide[f"cvap_{race}_pct"] = (
            cvap_wide[race] / total * 100
        ).round(1)

    cvap_final = cvap_wide[
        [
            "county_fips",
            "total",
            "cvap_white_pct",
            "cvap_black_pct",
            "cvap_asian_pct",
            "cvap_aian_pct",
            "cvap_hispanic_pct",
        ]
    ].rename(columns={"total": "cvap_total"})

    logger.info(f"Processed CVAP for {len(cvap_final):,} counties")

    # =========================================================
    # 2. LOAD SECTION 203 (optional)
    # =========================================================
    s203_path = demo_dir / "section_203_2021_raw.csv"
    cvap_final["section_203_covered"] = 0

    if s203_path.exists():
        logger.info("Loading Section 203 data...")

        s203 = None
        read_attempts = [
            dict(dtype=str, sep=",", engine="c"),                 # normal CSV
            dict(dtype=str, sep=",", engine="python"),            # python engine is more forgiving
            dict(dtype=str, sep=None, engine="python"),           # auto-detect delimiter
            dict(dtype=str, sep=",", engine="python", on_bad_lines="skip"),  # skip bad rows
        ]

        last_err = None
        for kwargs in read_attempts:
            try:
                s203 = pd.read_csv(s203_path, **kwargs)
                break
            except Exception as e:
                last_err = e

        if s203 is None:
            logger.warning(
                f"Could not parse Section 203 file; continuing without it. Error: {last_err}"
            )
        else:
            # Normalize column names
            s203.columns = [c.strip() for c in s203.columns]

            if {"State_Code", "County_Code"}.issubset(s203.columns):
                s203["county_fips"] = (
                    s203["State_Code"].astype(str).str.zfill(2)
                    + s203["County_Code"].astype(str).str.zfill(3)
                )
                covered = set(s203["county_fips"].dropna().astype(str))
                cvap_final["section_203_covered"] = (
                    cvap_final["county_fips"].isin(covered).astype("int8")
                )
                logger.info(f"Section 203: matched {len(covered):,} covered counties")
            else:
                # Fallback: look for a FIPS-like column
                fips_col = None
                for col in s203.columns:
                    cl = col.lower()
                    if "fips" in cl or "geoid" in cl:
                        fips_col = col
                        break

                if fips_col:
                    s203["county_fips"] = s203[fips_col].astype(str).str.zfill(5).str[:5]
                    covered = set(s203["county_fips"].dropna().astype(str))
                    cvap_final["section_203_covered"] = (
                        cvap_final["county_fips"].isin(covered).astype("int8")
                    )
                    logger.info(f"Section 203: matched {len(covered):,} covered counties")
                else:
                    logger.warning(
                        "Section 203 parsed, but no State_Code/County_Code or FIPS/GEOID column found. "
                        "Continuing without coverage flags."
                    )


    # =========================================================
    # 3. MERGE WITH EAVS
    # =========================================================
    logger.info("Merging demographics into EAVS data...")

    # EAVS may have 10-digit FIPS → truncate to county
    df["county_fips"] = df["fips_code"].astype(str).str[:5]

    df_enriched = df.merge(
        cvap_final,
        on="county_fips",
        how="left",
    )

    pct_cols = [c for c in df_enriched.columns if c.endswith("_pct")]
    df_enriched[pct_cols] = df_enriched[pct_cols].fillna(0)

    df_enriched["cvap_total"] = (
        df_enriched["cvap_total"].fillna(0).astype("int32")
    )
    df_enriched["section_203_covered"] = (
        df_enriched["section_203_covered"].fillna(0).astype("int8")
    )

    matched = df_enriched["cvap_total"].gt(0).sum()
    logger.info(
        f"Matched CVAP data for {matched:,}/{len(df_enriched):,} jurisdictions"
    )

    return df_enriched


# =============================================================
# CLI ENTRY POINT
# =============================================================
if __name__ == "__main__":
    input_path = PROJ_ROOT / "data" / "cleaned" / "2024_cleaned.parquet"
    output_path = PROJ_ROOT / "data" / "cleaned" / "2024_cleaned_with_demographics.parquet"

    if not input_path.exists():
        logger.error(f"Missing input file: {input_path}")
        sys.exit(1)

    logger.info("Loading cleaned EAVS data...")
    df = pd.read_parquet(input_path)

    enriched = add_demographics(df, year=2024)

    logger.info(f"Saving enriched data → {output_path}")
    enriched.to_parquet(output_path, index=False)

    logger.success("✓ Demographics enrichment complete")
