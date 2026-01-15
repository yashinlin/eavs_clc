#!/usr/bin/env python3
"""Verify that demographics data is properly set up and accessible."""

import sys
from pathlib import Path
import pandas as pd

PROJ_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = PROJ_ROOT / "data" / "demographics"

def check_file(path: Path, min_size: int, description: str) -> bool:
    """Check if a file exists and meets minimum size requirements."""
    print(f"\nChecking: {description}")
    print(f"  Path: {path}")
    
    if not path.exists():
        print(f"  ✗ MISSING - File not found")
        return False
    
    size = path.stat().st_size
    if size < min_size:
        print(f"  ✗ CORRUPTED - File too small ({size:,} bytes, expected >{min_size:,})")
        return False
    
    print(f"  ✓ OK - {size:,} bytes")
    return True


def verify_cvap_structure(path: Path) -> bool:
    """Verify CVAP CSV has expected structure."""
    print("\nVerifying CVAP file structure...")
    
    try:
        # Read first few rows after header
        df = pd.read_csv(path, skiprows=5, nrows=5)
        
        required_cols = ["GEOID", "LNTITLE", "CVAP_EST", "CVAP_WHT", "CVAP_BLK", "CVAP_HSP"]
        missing = [col for col in required_cols if col not in df.columns]
        
        if missing:
            print(f"  ✗ INVALID - Missing columns: {missing}")
            print(f"  Found columns: {df.columns.tolist()}")
            return False
        
        print(f"  ✓ Valid structure - {len(df.columns)} columns found")
        print(f"  Sample FIPS codes: {df['GEOID'].head(3).tolist()}")
        return True
        
    except Exception as e:
        print(f"  ✗ ERROR reading file: {e}")
        return False


def verify_section203_structure(path: Path) -> bool:
    """Verify Section 203 CSV has expected structure."""
    print("\nVerifying Section 203 file structure...")
    
    try:
        df = pd.read_csv(path, nrows=5)
        
        # Check for FIPS-related columns
        fips_cols = [col for col in df.columns if any(
            term in col.lower() for term in ["fips", "state", "county", "geoid"]
        )]
        
        if not fips_cols:
            print(f"  ⚠ WARNING - No obvious FIPS columns found")
            print(f"  Columns: {df.columns.tolist()}")
            print(f"  (May still work if add_demographics.py can parse it)")
            return True  # Non-critical warning
        
        print(f"  ✓ Valid structure - FIPS columns: {fips_cols}")
        return True
        
    except Exception as e:
        print(f"  ✗ ERROR reading file: {e}")
        return False


def main():
    print("=" * 60)
    print("EAVS Demographics Setup Verification")
    print("=" * 60)
    
    all_ok = True
    
    # Check CVAP file
    cvap_path = DEMO_DIR / "County_CVAP_2018-2022.csv"
    cvap_ok = check_file(cvap_path, 1_000_000, "Census CVAP 2018-2022 County Data")
    if cvap_ok:
        cvap_ok = verify_cvap_structure(cvap_path)
    all_ok = all_ok and cvap_ok
    
    # Check Section 203 file
    s203_path = DEMO_DIR / "section_203_2021_raw.csv"
    s203_ok = check_file(s203_path, 10_000, "Section 203 Coverage Data")
    if s203_ok:
        s203_ok = verify_section203_structure(s203_path)
    
    # Section 203 is optional, so don't fail overall check
    if not s203_ok:
        print("\n  ⚠ Note: Section 203 data is optional. Demographics will work without it.")
    
    # Check if enriched data already exists
    enriched_path = PROJ_ROOT / "data" / "cleaned" / "2024_cleaned_with_demographics.parquet"
    print(f"\nChecking: Enriched EAVS data (optional)")
    print(f"  Path: {enriched_path}")
    if enriched_path.exists():
        size = enriched_path.stat().st_size
        print(f"  ✓ Already exists - {size:,} bytes")
        print(f"  (To regenerate, run: python -m eavs.add_demographics)")
    else:
        print(f"  ○ Not yet created - run: python -m eavs.add_demographics")
    
    # Final summary
    print("\n" + "=" * 60)
    if all_ok:
        print("✓ SETUP COMPLETE - Ready to run add_demographics")
        print("\nNext step:")
        print("  python -m eavs.add_demographics")
        return 0
    else:
        print("✗ SETUP INCOMPLETE - Please run setup script")
        print("\nNext step:")
        print("  bash scripts/setup_demographics.sh")
        return 1


if __name__ == "__main__":
    sys.exit(main())
