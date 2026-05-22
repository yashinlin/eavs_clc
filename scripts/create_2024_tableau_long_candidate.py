from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

input_path = ROOT / "data/cleaned/2024_dashboard_candidate.csv"
output_xlsx = ROOT / "data/cleaned/2024_tableau_long_candidate.xlsx"
output_counts_csv = ROOT / "data/cleaned/2024_tableau_long_counts_candidate.csv"
output_rates_csv = ROOT / "data/cleaned/2024_tableau_long_rates_candidate.csv"

ID_COLS = ["fips_code", "jurisdiction_name", "state", "state_abbr"]

df = pd.read_csv(input_path)

rename_ids = {
    "fips_code": "FIPSCode",
    "jurisdiction_name": "Jurisdiction_Name",
    "state": "State_Full",
    "state_abbr": "State_Abbr",
}

df = df.rename(columns=rename_ids)
df["Year"] = 2024

ID_OUT = ["FIPSCode", "Jurisdiction_Name", "State_Full", "State_Abbr", "Year"]

# Sheet1-style count data: Metric / Count / Value
COUNT_MAPPINGS = [
    # Applicants / registration-source counts
    ("Applicants", "Mail", "total_forms_mail_fax_email"),
    ("Applicants", "In Person", "total_forms_in_person"),
    ("Applicants", "Online", "total_forms_online"),
    ("Applicants", "DMV", "total_forms_dmv"),
    ("Applicants", "NVRA", "total_forms_mandatory_nvra"),
    ("Applicants", "Disabilities", "total_forms_disability_agency"),
    ("Applicants", "Armed Forces", "total_forms_armed_forces"),
    ("Applicants", "Non-NVRA", "total_forms_discretionary_nvra"),
    ("Applicants", "Registered Drives", "total_forms_advocacy_groups"),

    # Purged / removals counts
    ("Purged", "Felony", "voters_removed_felony"),
    ("Purged", "No Response", "voters_removed_nonresponse"),
    ("Purged", "Total", "voters_removed_total"),
]

count_frames = []

for metric, count_label, col in COUNT_MAPPINGS:
    if col not in df.columns:
        print(f"WARNING: missing count column: {col}")
        continue

    temp = df[ID_OUT + [col]].copy()
    temp["Metric"] = metric
    temp["Count"] = count_label
    temp["Value"] = pd.to_numeric(temp[col], errors="coerce")
    temp = temp.drop(columns=[col])
    count_frames.append(temp)

counts_long = pd.concat(count_frames, ignore_index=True)

# Sheet2-style rate inputs: Metric / Denominator / Numerator
# These mirror the earlier Tableau sample structure.
RATE_MAPPINGS = [
    # Applicants: rejected registration forms / total registration forms
    ("Applicants", "total_registrations_received", "rejected_registrations"),

    # Purged: total removals / approximate registered + removed population
    # This follows the earlier CLC denominator logic: A12a / (A1a + A12a)
    ("Purged", "registered_eligible_voters", "voters_removed_total"),
]

rate_frames = []

for metric, denominator_col, numerator_col in RATE_MAPPINGS:
    missing = [c for c in [denominator_col, numerator_col] if c not in df.columns]
    if missing:
        print(f"WARNING: missing rate columns for {metric}: {missing}")
        continue

    temp = df[ID_OUT + [denominator_col, numerator_col]].copy()
    temp["Metric"] = metric

    if metric == "Purged":
        temp["Denominator"] = (
            pd.to_numeric(temp[denominator_col], errors="coerce")
            + pd.to_numeric(temp[numerator_col], errors="coerce")
        )
    else:
        temp["Denominator"] = pd.to_numeric(temp[denominator_col], errors="coerce")

    temp["Numerator"] = pd.to_numeric(temp[numerator_col], errors="coerce")

    temp = temp.drop(columns=[denominator_col, numerator_col])
    rate_frames.append(temp)

rates_long = pd.concat(rate_frames, ignore_index=True)

# Match Tableau sample naming closely
counts_long = counts_long[
    ["FIPSCode", "Jurisdiction_Name", "State_Full", "State_Abbr", "Year", "Metric", "Count", "Value"]
]

rates_long = rates_long[
    ["FIPSCode", "Jurisdiction_Name", "State_Full", "State_Abbr", "Year", "Metric", "Denominator", "Numerator"]
]

counts_long.to_csv(output_counts_csv, index=False)
rates_long.to_csv(output_rates_csv, index=False)

with pd.ExcelWriter(output_xlsx, engine="openpyxl") as writer:
    counts_long.to_excel(writer, sheet_name="Sheet1", index=False)
    rates_long.to_excel(writer, sheet_name="Sheet2", index=False)

print(f"Saved: {output_xlsx}")
print(f"Saved: {output_counts_csv}")
print(f"Saved: {output_rates_csv}")
print(f"Counts long shape: {counts_long.shape}")
print(f"Rates long shape: {rates_long.shape}")
print(counts_long.head())
print(rates_long.head())