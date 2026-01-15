cat > eavs/add_demographics_lowmem.py << EOF
"""Ultra low-memory version of demographics enrichment.

Use this if the standard version runs out of memory (Exit code 9).

Usage:
    python scripts/add_demographics_lowmem.py
"""

import pandas as pd
from pathlib import Path
from loguru import logger
import sys
import gc

PROJ_ROOT = Path(__file__).resolve().parent.parent


def load_cvap_minimal(cvap_path: Path) -> pd.DataFrame:
    """Load only essential CVAP data in the most memory-efficient way."""
    
    logger.info("Loading CVAP data in ultra low-memory mode...")
    logger.info("This will take longer but uses ~50% less RAM")
    
    # Read only what we need, row by row
    chunks = []
    chunk_size = 10000  # Process 10k rows at a time
    
    cols_to_read = ["GEOID", "LNTITLE", "CVAP_EST", "CVAP_WHT", "CVAP_BLK", "CVAP_HSP", "CVAP_ASN", "CVAP_AIA"]
    
    chunk_count = 0
    for chunk in pd.read_csv(
        cvap_path,
        skiprows=5,
        usecols=cols_to_read,
        dtype=str,  # Read everything as string first
        chunksize=chunk_size,
        low_memory=True
    ):
        chunk_count += 1
        
        # Filter to Total rows only
        chunk = chunk[chunk["LNTITLE"] == "Total"].copy()
        
        if len(chunk) > 0:
            # Extract FIPS
            chunk["fips_code"] = chunk["GEOID"].str.replace("0500000US", "", regex=False)
            
            # Convert numeric columns
            for col in ["CVAP_EST", "CVAP_WHT", "CVAP_BLK", "CVAP_HSP", "CVAP_ASN", "CVAP_AIA"]:
                chunk[col] = pd.to_numeric(chunk[col], errors="coerce").fillna(0)
            
            # Calculate percentages immediately
            total = chunk["CVAP_EST"].replace(0, 1)
            result = pd.DataFrame({
                "fips_code": chunk["fips_code"],
                "cvap_total": chunk["CVAP_EST"].astype("int32"),
                "cvap_white_pct": (chunk["CVAP_WHT"] / total * 100).round(1).astype("float32"),
                "cvap_black_pct": (chunk["CVAP_BLK"] / total * 100).round(1).astype("float32"),
                "cvap_hisp_pct": (chunk["CVAP_HSP"] / total * 100).round(1).astype("float32"),
                "cvap_asian_pct": (chunk["CVAP_ASN"] / total * 100).round(1).astype("float32"),
                "cvap_aian_pct": (chunk["CVAP_AIA"] / total * 100).round(1).astype("float32"),
            })
            
            chunks.append(result)
            
        # Clear memory after each chunk
        del chunk
        gc.collect()
        
        if chunk_count % 5 == 0:
            logger.info(f"Processed {chunk_count * chunk_size:,} rows...")
    
    # Combine all chunks
    logger.info("Combining CVAP chunks...")
    cvap = pd.concat(chunks, ignore_index=True)
    del chunks
    gc.collect()
    
    logger.info(f"Loaded {len(cvap):,} counties")
    return cvap


def main():
    from eavs.config import PROJ_ROOT
    
    logger.info("=" * 60)
    logger.info("Ultra Low-Memory Demographics Enrichment")
    logger.info("=" * 60)
    
    demo_dir = PROJ_ROOT / "data" / "demographics"
    
    # Check for required files
    cvap_path = demo_dir / "County_CVAP_2018-2022.csv"
    if not cvap_path.exists():
        logger.error(f"CVAP file not found: {cvap_path}")
        logger.error("Run: bash scripts/setup_demographics.sh")
        return 1
    
    # Load EAVS data
    input_path = PROJ_ROOT / "data" / "cleaned" / "2024_cleaned.parquet"
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        logger.error("Run data cleaning pipeline first: python -m eavs.clean")
        return 1
    
    logger.info(f"Loading EAVS data from {input_path}...")
    df = pd.read_parquet(input_path)
    df["fips_code"] = df["fips_code"].astype(str)
    logger.info(f"Loaded {len(df):,} rows")
    
    # Load CVAP in minimal mode
    try:
        cvap = load_cvap_minimal(cvap_path)
    except Exception as e:
        logger.exception(f"Failed to load CVAP: {e}")
        return 1
    
    # Load Section 203 (small file, no special handling needed)
    s203_path = demo_dir / "section_203_2021_raw.csv"
    if s203_path.exists():
        logger.info("Loading Section 203 data...")
        try:
            s203 = pd.read_csv(s203_path, dtype=str)
            
            # Identify FIPS column
            if "State_Code" in s203.columns and "County_Code" in s203.columns:
                s203["fips_code"] = s203["State_Code"].str.zfill(2) + s203["County_Code"].str.zfill(3)
            else:
                for col in s203.columns:
                    if "fips" in col.lower() or "geoid" in col.lower():
                        s203["fips_code"] = s203[col].astype(str).str.zfill(5)
                        break
            
            if "fips_code" in s203.columns:
                covered_fips = set(s203["fips_code"].unique())
                cvap["section_203_covered"] = cvap["fips_code"].isin(covered_fips).astype("int8")
                logger.info(f"Found {len(covered_fips):,} Section 203 covered jurisdictions")
            else:
                cvap["section_203_covered"] = 0
                
            del s203
            gc.collect()
        except Exception as e:
            logger.warning(f"Could not load Section 203: {e}")
            cvap["section_203_covered"] = 0
    else:
        logger.info("Section 203 file not found (optional) - continuing without it")
        cvap["section_203_covered"] = 0
    
    # Merge
    logger.info("Merging demographics with EAVS data...")
    df_enriched = df.merge(cvap, on="fips_code", how="left")
    
    del df, cvap
    gc.collect()
    
    # Fill missing values
    pct_cols = [c for c in df_enriched.columns if "_pct" in c]
    df_enriched[pct_cols] = df_enriched[pct_cols].fillna(0)
    df_enriched["cvap_total"] = df_enriched["cvap_total"].fillna(0).astype("int32")
    df_enriched["section_203_covered"] = df_enriched["section_203_covered"].fillna(0).astype("int8")
    
    matched = df_enriched["cvap_total"].gt(0).sum()
    match_pct = (matched / len(df_enriched) * 100) if len(df_enriched) > 0 else 0
    logger.info(f"Matched demographics for {matched:,}/{len(df_enriched):,} jurisdictions ({match_pct:.1f}%)")
    
    # Save
    output_path = PROJ_ROOT / "data" / "cleaned" / "2024_cleaned_with_demographics.parquet"
    logger.info(f"Saving to {output_path}...")
    df_enriched.to_parquet(output_path, index=False)
    logger.success(f"✓ Saved: {output_path}")
    
    # Summary
    print("\n" + "=" * 60)
    print("COVERAGE SUMMARY")
    print("=" * 60)
    print(f"Total jurisdictions:    {len(df_enriched):>8,}")
    print(f"With CVAP data:         {matched:>8,}")
    print(f"Section 203 covered:    {df_enriched['section_203_covered'].sum():>8,}")
    
    # Only calculate averages where data exists
    has_cvap = df_enriched['cvap_total'] > 0
    if has_cvap.sum() > 0:
        print(f"Avg % White:            {df_enriched[has_cvap]['cvap_white_pct'].mean():>8.1f}%")
        print(f"Avg % Black:            {df_enriched[has_cvap]['cvap_black_pct'].mean():>8.1f}%")
        print(f"Avg % Hispanic:         {df_enriched[has_cvap]['cvap_hisp_pct'].mean():>8.1f}%")
    print("=" * 60)
    
    logger.success("Demographics enrichment complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())EOF
