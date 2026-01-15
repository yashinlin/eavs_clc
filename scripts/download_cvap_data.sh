#!/bin/bash
# Download Census CVAP 2018-2022 County data and Section 203 data

set -e  # Exit on error

echo "=== Downloading CVAP 2018-2022 County Data ==="
cd data/demographics

# Download the ZIP file containing county-level CVAP data
curl -L -o County_CVAP_2018-2022.zip   "https://www2.census.gov/programs-surveys/decennial/rdo/datasets/2022/2018-2022-cvap/County.zip"

# Extract the ZIP file
unzip -o County_CVAP_2018-2022.zip

# The ZIP should contain a CSV file named County_CVAP_2018-2022.csv
echo "CVAP file extracted"

echo ""
echo "=== Downloading Section 203 Data ==="
# Download Section 203 determinations (clean CSV from Census)
curl -L -o section_203_2021_raw.csv   "https://www2.census.gov/programs-surveys/decennial/rdo/datasets/2021/2021_Section203-Determinations/Sec203_PUF_2021_12_01.csv"

echo ""
echo "=== Files downloaded successfully ==="
ls -lh *.csv *.zip
echo ""
echo "Now run: python -m eavs.add_demographics"
