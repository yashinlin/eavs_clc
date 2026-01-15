from pathlib import Path
from typing import Dict, Any, List

import pandas as pd
import pandera as pa
import yaml
from loguru import logger as log

from eavs.clean_timeseries import clean_timeseries

# -----------------
# 0. Configuration
# -----------------
# PROJ_ROOT = directory above 'eavs' (ie. /home/user/eavs_clc)
PROJ_ROOT = Path(__file__).resolve().parent.parent

CONFIG_PATH = PROJ_ROOT / 'eavs' / 'assets' / 'column_mappings'

def load_config(year: int) -> List[Dict[str, Any]]:
    """
    Dynamically load the year-specific config file (e.g., 2022.yaml).
    Handles top-level nesting (e.g., under a 'columns' key) to ensure 
    a clean list of mappings is returned.
    """
    config_file = CONFIG_PATH / f'{year}.yaml'
    if not config_file.exists():
        log.warning(f"Config file not found for year {year}: {config_file}. Cleaning will proceed without specific variable handling.")
        return [] 
    
    try:
        with open(config_file, 'r') as f:
            data = yaml.safe_load(f) 
            
            # If the loaded data is a dictionary (ie has key:value pairs), extract the list from the 'columns' key.
            if isinstance(data, dict) and 'columns' in data:
                log.debug("Extracted column list from 'columns' key.")
                return data['columns']
                
            # If it's already a list (flat structure), return it directly.
            if isinstance(data, list):
                log.debug("Loaded config as flat list.")
                return data
                
            # Fallback for unexpected structure
            log.warning(f"Config for year {year} is in an unexpected format (neither dictionary nor list). Returning empty list.")
            return []
            
    except Exception as e:
        log.error(f"Error loading config file {config_file}: {e}")
        return []

# -----------------
# 1. Schema Definition
# -----------------

class CleanedEAVSSchema(pa.DataFrameModel):
    """
    Validate core identifier fields in cleaned EAVS datasets via minimal Pandera schema.

    This schema enforces basic structural integrity by checking that
    all cleaned EAVS outputs contain valid FIPS codes and year values.
    It is intentionally permissive about all other columns so that
    different years and products (e.g., timeseries vs per-year files)
    can include different sets of variables without failing validation.

    Notes:
    - Only `fips_code` and `year` are validated.
    - Additional columns are allowed and ignored by this schema.
    - Type coercion is enabled to normalize input data before validation.
    """

    # FIPS codes must be 5-digit strings
    fips_code: Series[String] = pa.Field(str_matches=r'^\d{5}$')
    
    # Year of the EAVS data (e.g., 2022)
    year: Series[int] = pa.Field(ge=2000, le=2030)
    
    class Config:
        strict = False # allows dataframe to have extra columns beyond the above two
        coerce = True
        
schema = CleanedEAVSSchema

# -----------------
# 2. Datatype conversion configuration
# -----------------

def apply_yaml_dtypes(df: pd.DataFrame, configs: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Convert dataframe columns to pandas dtypes based on YAML configs.
    Assumes columns have already been renamed to their `name` values.
    """
    for c in configs:
        name = c.get("name")
        dtype = str(c.get("dtype", "")).lower()

        if not name or name not in df.columns:
            continue

        try:
            if dtype.startswith("int"):
                df[name] = pd.to_numeric(df[name], errors="coerce").astype(pd.Int64Dtype())
            elif dtype.startswith("float"):
                df[name] = pd.to_numeric(df[name], errors="coerce").astype(pd.Float64Dtype())
            elif dtype.startswith("string"):
                # pandas nullable string dtype
                df[name] = df[name].astype("string")
            else:
                # Unknown dtype — leave as-is but log once in a while
                log.debug(f"Skipping dtype coercion for column '{name}' with dtype='{dtype}'")
        except Exception as e:
            log.warning(f"Failed to coerce '{name}' to '{dtype}': {e}")

    return df

# -----------------
# 3. Cleaning Functions
# -----------------

def clean_data(year: int, config: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Loads raw EAVS data for a given year, applies renaming and type conversion 
    based on the loaded configuration, and ensures robust column selection.
    
    NOTE: This function relies on raw data being found in:
    <PROJ_ROOT>/data/raw/<year>/<filename>.xlsx
    """
    raw_data_dir = PROJ_ROOT / 'data' / 'raw' / str(year)
    excel_files = list(raw_data_dir.rglob('*.xls*')) 
    
    if not excel_files:
        log.warning(f"Raw EAVS file not found for year {year} within {raw_data_dir}")
        return pd.DataFrame()
        
    data_path = excel_files[0]
    log.info(f"Cleaning data for {year} using file: {data_path.name}")

    # Robustly create mapping, skipping malformed config entries 
    valid_configs = [
        c for c in config 
        if isinstance(c, dict) and 'raw_name' in c and 'name' in c
    ]
    if len(valid_configs) != len(config):
        log.warning(f"Skipped {len(config) - len(valid_configs)} malformed entries in the {year} column mapping file.")

    mapping = {col['raw_name']: col['name'] for col in valid_configs}
    dtypes = {col['raw_name']: str for col in valid_configs} 

    # EXTRACT: Load raw data
    try:
        df = pd.read_excel(data_path, sheet_name=0, engine='openpyxl', dtype=dtypes)
    except Exception as e:
        log.error(f"Error loading {data_path}: {e}")
        return pd.DataFrame()

    # Standardize FIPS column name
    fips_col = next((col for col in df.columns if 'FIPS' in str(col).upper()), None)
    if fips_col:
        df = df.rename(columns={fips_col: 'fips_code'})
    else:
        log.error(f"FIPS code column not found in {year} data.")
        return pd.DataFrame() 

    # Add year column
    df["year"] = year

    # --- TRANSFORM: Normalize & interpret FIPSCode variants ---

    # Preserve raw for traceability
    df["fips_code_raw"] = df["fips_code"].astype(str).str.strip()

    # Digit-only identifier (keeps UOCAVA 23, tract GEOIDs, etc.)
    digits = df["fips_code_raw"].str.replace(r"\D", "", regex=True)
    df["geoid"] = digits

    # County-only 5-digit code for validation + county joins
    df["fips_code"] = pd.NA

    # UOCAVA marker (keep separate; do NOT force into county fips)
    df["is_uocava"] = digits.eq("23")

    # Standard county FIPS already 5 digits
    county5_mask = digits.str.len().eq(5) & ~df["is_uocava"]
    df.loc[county5_mask, "fips_code"] = digits[county5_mask]

    # CA 2024 formatting issue (len 9 like 600100000): derive county FIPS = first 4 digits, zfill to 5
    len9_mask = digits.str.len().eq(9)
    df.loc[len9_mask, "fips_code"] = digits[len9_mask].str[:4].str.zfill(5)

    # Logging summary (helpful for PR reviewers)
    len_counts = digits.str.len().value_counts(dropna=False).to_dict()
    log.info(f"{year} FIPSCode digit-length distribution: {len_counts}")
    log.info(
        f"{year} derived county fips_code counts: "
        f"county5={county5_mask.sum()}, len9_fixed={len9_mask.sum()}, "
        f"uocava={df['is_uocava'].sum()}, county_missing={df['fips_code'].isna().sum()}"
    )

    # Apply YAML renaming & Robust Filtering
    mapping_keys = mapping.keys()
    existing_keys = [k for k in mapping_keys if k in df.columns]
    
    cols_to_select = existing_keys + ['fips_code', 'year', 'geoid', 'is_uocava']
    
    df = df.filter(items=cols_to_select, axis=1)

    renaming_map = {k: mapping[k] for k in existing_keys}
    df = df.rename(columns=renaming_map)
    df = apply_yaml_dtypes(df, valid_configs)
    return df

def combine_data(cleaned_dfs: List[pd.DataFrame]) -> pd.DataFrame:
    """Combines cleaned dataframes from multiple years."""
    log.info(f"Combining {len(cleaned_dfs)} years of cleaned data.")
    combined_df = pd.concat(cleaned_dfs, ignore_index=True)
    return combined_df

# -----------------
# 4. New Saving Function 
# -----------------
def save_dataframes(df: pd.DataFrame, filename: str, output_dir: Path):
    """Save a DataFrame to Parquet, XLSX, and CSV formats."""
    log.info(f"Saving {filename} data to multiple formats in {output_dir.name}/")
    
    # Ensure output directory exists (redundant with main, but safer here)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Always save Parquet — fastest, smallest, best for analysis
    parquet_path = output_dir / f"{filename}.parquet"
    df.to_parquet(parquet_path, index=False)
    log.success(f"Parquet saved: {parquet_path.name}")

    # Only save CSV for the combined dataset (as requested)
    if save_csv:
        csv_path = output_dir / f"{filename}.csv"
        df.to_csv(csv_path, index=False)
        log.success(f"CSV saved (combined only): {csv_path.name}")


# -----------------
# 5. Main Execution 
# -----------------

def main():    
    """
    Run the EAVS cleaning pipeline for selected years and the historical timeseries dataset, 
    producing per-year, combined, and timeseries outputs."""

    years = [2020, 2022, 2024] 
    
    log.info(f"Starting per-year cleaning for years: {years}")
    
    # Define output directory and ensure it exists
    output_dir = PROJ_ROOT / 'data' / 'cleaned'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    cleaned_dataframes = []
    for year in years:
        year_config = load_config(year) 
        
        if not year_config: # if year_config is missing or empty
            log.warning(f"Skipping cleaning for year {year} due to missing or empty config.")
            continue

        df = clean_data(year, year_config)
        if not df.empty:
            cleaned_dataframes.append(df)
            save_dataframes(df, f'{year}_cleaned', output_dir)
            
    # Run timeseries cleaning via its own module (saves its own parquet)
    try:
        ts_df = clean_timeseries()
        if ts_df is not None and not ts_df.empty:
            log.info(f"Timeseries file processed in separate module: {len(ts_df)} rows")
        else:
            log.info("Timeseries was processed but returned empty or not processed.")
    except Exception as e:
        # Protect the pipeline from timeseries failures
        log.error(f"Error when running timeseries module: {e}")

    if not cleaned_dataframes:
        log.error("No valid dataframes were cleaned. Exiting.")
        return

    combined_df = combine_data(cleaned_dataframes)
    cleaned_df = combined_df.copy()

    # Save combined dataset with all geographies (county + UOCAVA + sub-county GEOIDs)
    save_dataframes(combined_df, "eavs_combined_cleaned_all_geo", output_dir)

    # Combined output is county-level only; non-county geographies (UOCAVA, sub-county GEOIDs)
    # are preserved upstream but excluded from this validated artifact.
    cleaned_df = cleaned_df.dropna(subset=["fips_code"])

    # VALIDATE: Ensure fips_code is string before schema validation
    cleaned_df['fips_code'] = cleaned_df['fips_code'].astype(str)
    log.info(f"Starting per-year cleaning for years: {years}")
    
    try:
        log.info(f"Validating combined data with {len(cleaned_df)} rows...")
        schema.validate(cleaned_df)
        log.success("Data validation successful!")
        
        # LOAD: Save combined file in all formats
        save_dataframes(cleaned_df, 'eavs_combined_cleaned', output_dir)

    except pa.errors.SchemaError as e:
        log.error(f"Data validation failed: {e}")
        return
        
    log.info("Finished EAVS Cleaning Pipeline.")

if __name__ == '__main__':
    main()