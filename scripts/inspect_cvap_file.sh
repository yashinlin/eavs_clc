"""Inspect the structure of the CVAP file to understand its format."""
import pandas as pd
from pathlib import Path

PROJ_ROOT = Path(__file__).resolve().parent.parent
cvap_path = PROJ_ROOT / "data" / "demographics" / "cvap_county_2018_2022.csv"

print(f"Inspecting: {cvap_path}")
print(f"File size: {cvap_path.stat().st_size:,} bytes")
print()

# Try reading just the first 20 lines to see structure
print("=== First 20 lines of file ===")
with open(cvap_path, 'r') as f:
    for i, line in enumerate(f):
        if i < 20:
            print(f"Line {i}: {line.rstrip()[:150]}")  # First 150 chars
        else:
            break

print("\n=== Trying to read with pandas (no skiprows) ===")
try:
    df = pd.read_csv(cvap_path, nrows=5)
    print(f"Columns: {df.columns.tolist()}")
    print(df.head())
except Exception as e:
    print(f"Error: {e}")

print("\n=== Trying to read with skiprows=5 ===")
try:
    df = pd.read_csv(cvap_path, skiprows=5, nrows=10)
    print(f"Columns: {df.columns.tolist()}")
    print(df.head())
except Exception as e:
    print(f"Error: {e}")
