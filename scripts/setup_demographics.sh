#!/bin/bash
# Setup script for EAVS demographic data
# Downloads Census CVAP and Section 203 data files
# Run this once before using add_demographics.py

set -e  # Exit on any error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJ_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
DEMO_DIR="$PROJ_ROOT/data/demographics"

echo "========================================="
echo "EAVS Demographics Data Setup"
echo "========================================="
echo ""
echo "This script will download:"
echo "  1. Census CVAP 2018-2022 (ALL geographies, ~53 MB)"
echo "  2. Section 203 Language Minority Coverage (2021)"
echo ""

# Create demographics directory if it doesn't exist
mkdir -p "$DEMO_DIR"
cd "$DEMO_DIR"

# Function to check if a file exists and has reasonable size
check_file() {
    local file=$1
    local min_size=$2
    if [ -f "$file" ]; then
        local size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
        if [ "$size" -gt "$min_size" ]; then
            echo "✓ $file already exists and looks valid (${size} bytes)"
            return 0
        else
            echo "⚠ $file exists but seems corrupted (only ${size} bytes). Re-downloading..."
            rm -f "$file"
        fi
    fi
    return 1
}

# Download CVAP data
echo "========================================="
echo "1. Census CVAP 2018-2022 Data"
echo "========================================="

if ! check_file "County_CVAP_2018-2022.csv" 1000000; then
    echo "Downloading CVAP 2018-2022 ZIP file (all geographies, ~53 MB)..."
    
    if curl -L -o CVAP_2018-2022_ACS_csv_files.zip \
        "https://www2.census.gov/programs-surveys/decennial/rdo/datasets/2022/2022-cvap/CVAP_2018-2022_ACS_csv_files.zip"; then
        
        echo "Extracting CVAP data..."
        unzip -o CVAP_2018-2022_ACS_csv_files.zip

        # 🔑 THIS IS THE MISSING PIECE
        if [ -f "County.csv" ]; then
            echo "Renaming County.csv → County_CVAP_2018-2022.csv"
            mv County.csv County_CVAP_2018-2022.csv
        fi

        if [ -f "County_CVAP_2018-2022.csv" ]; then
            size=$(stat -f%z "County_CVAP_2018-2022.csv" 2>/dev/null || stat -c%s "County_CVAP_2018-2022.csv" 2>/dev/null)
            echo "✓ County CVAP data ready (${size} bytes)"
        else
            echo "✗ ERROR: County CVAP file not found after extraction."
            ls -lh *.csv
            exit 1
        fi
    else
        echo "✗ ERROR: Failed to download CVAP data"
        exit 1
    fi
fi

echo ""

# Download Section 203 data
echo "========================================="
echo "2. Section 203 Language Minority Coverage"
echo "========================================="

ZIP_NAME="Sec203_PUF_2021_12_01.zip"

if [ ! -f "$ZIP_NAME" ]; then
    echo "Downloading Section 203 ZIP file..."
    curl -L -o "$ZIP_NAME" \
        "https://www2.census.gov/programs-surveys/decennial/rdo/datasets/2021/2021_Section203-Determinations/Sec203_PUF_2021_12_01.zip"
else
    echo "✓ Section 203 ZIP already exists"
fi

echo "Extracting Section 203 files..."
unzip -o "$ZIP_NAME"

echo ""
echo "Extracted Section 203 files:"
ls -lh *.csv || true

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Key files in data/demographics/:"
echo ""
ls -lh County_CVAP_2018-2022.csv section_203_2021_raw.csv 2>/dev/null || true
echo ""
echo "Note: The ZIP also extracted other geography files (State, Place, Tract, etc.)"
echo "      These are available if you need them later, but the County file is"
echo "      what add_demographics.py uses."
echo ""
echo "Next steps:"
echo "  1. Run: python -m eavs.add_demographics"
echo "     (or python scripts/add_demographics_lowmem.py if low on RAM)"
echo ""
echo "  2. This will enrich your EAVS data with:"
echo "     - CVAP racial/ethnic percentages by county"
echo "     - Section 203 language minority coverage flags"
echo ""
echo "For other volunteers: Just run 'bash scripts/setup_demographics.sh'"
echo ""