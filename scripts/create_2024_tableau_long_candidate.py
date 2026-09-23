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

# Spec sums the three "other" mail-rejection reasons (C9r+C9s+C9t) into one
df["mail_ballots_rejected_other"] = df[
    ["mail_ballots_rejected_other_1", "mail_ballots_rejected_other_2", "mail_ballots_rejected_other_3"]
].apply(pd.to_numeric, errors="coerce").sum(axis=1, min_count=1)

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

    # Ballots / rejections
    ("Provisional Rejected", "Total", "provisional_ballots_rejected_total"),
    ("Provisional Rejected", "Not Registered", "provisional_ballots_rejected_not_registered"),
    ("Provisional Rejected", "Wrong Jurisdiction", "provisional_ballots_rejected_wrong_jurisdiction"),
    ("Provisional Rejected", "Wrong Precinct", "provisional_ballots_rejected_wrong_precinct"),
    ("Provisional Rejected", "Insuffic ID", "provisional_ballots_rejected_no_id"),
    ("Provisional Rejected", "Incomplete Ballot/Env", "provisional_ballots_rejected_incomplete"),
    ("Provisional Rejected", "Ballot Missing", "provisional_ballots_rejected_ballot_missing"),
    ("Provisional Rejected", "No Signature", "provisional_ballots_rejected_no_signature"),
    ("Provisional Rejected", "No Match Signature", "provisional_ballots_rejected_non_matching_signature"),
    ("Provisional Rejected", "Already Voted", "provisional_ballots_rejected_already_voted"),

    # Registration rejections BY SOURCE (EAVS has no rejection *reasons* for registrations)
    ("Registrations Rejected", "Total", "rejected_registrations"),
    ("Registrations Rejected", "Mail", "rejected_registrations_mail_fax_email"),
    ("Registrations Rejected", "In Person", "rejected_registrations_in_person"),
    ("Registrations Rejected", "Online", "rejected_registrations_online"),
    ("Registrations Rejected", "DMV", "rejected_registrations_dmv"),
    ("Registrations Rejected", "NVRA", "rejected_registrations_mandatory_nvra"),
    ("Registrations Rejected", "Disabilities", "rejected_registrations_disability_agency"),
    ("Registrations Rejected", "Armed Forces", "rejected_registrations_armed_forces"),
    ("Registrations Rejected", "Non-NVRA", "rejected_registrations_discretionary_nvra"),
    ("Registrations Rejected", "Registered Drives", "rejected_registrations_advocacy_groups"),

    # Mail ballot rejections by reason (C9a-C9t)
    ("Mail Rejected", "Total", "mail_ballots_rejected_total"),
    ("Mail Rejected", "Late / Missed Deadline", "mail_ballots_rejected_late"),
    ("Mail Rejected", "No Voter Signature", "mail_ballots_rejected_missing_voter_signature"),
    ("Mail Rejected", "No Witness Signature", "mail_ballots_rejected_missing_witness_signature"),
    ("Mail Rejected", "Non-Matching Signature", "mail_ballots_rejected_non_matching_voter_signature"),
    ("Mail Rejected", "Unofficial Envelope", "mail_ballots_rejected_unofficial_envelope"),
    ("Mail Rejected", "Ballot Missing from Envelope", "mail_ballots_rejected_ballot_missing_from_envelope"),
    ("Mail Rejected", "Multiple Ballots in Envelope", "mail_ballots_rejected_multiple_ballots_one_envelope"),
    ("Mail Rejected", "Envelope Not Sealed", "mail_ballots_rejected_envelope_not_sealed"),
    ("Mail Rejected", "No Address on Envelope", "mail_ballots_rejected_no_resident_address"),
    ("Mail Rejected", "Voter Deceased", "mail_ballots_rejected_voter_deceased"),
    ("Mail Rejected", "Already Voted", "mail_ballots_rejected_voter_already_voted"),
    ("Mail Rejected", "Missing Documentation", "mail_ballots_rejected_missing_documentation"),
    ("Mail Rejected", "No Ballot Application", "mail_ballots_rejected_no_ballot_application"),
    ("Mail Rejected", "Other", "mail_ballots_rejected_other"),

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
    # Purged, EAC dashboard formula: A12a / A1a (removed / registered)
    ("Purged (EAC)", "registered_eligible_voters", "voters_removed_total"),
    # Provisional: E1d / E1a (CLC spec; matches EAC dashboard)
    ("Provisional Rejected", "provisional_ballots_cast_total", "provisional_ballots_rejected_total"),
    # Mail: C9a / C1b (rejected / returned by voters -- matches EAC Appendix D)
    ("Mail Rejected", "mail_returned_by_voters", "mail_ballots_rejected_total"),

]

# Fail loudly: one typo'd column must stop the script, not silently drop a reason
needed = [col for _, _, col in COUNT_MAPPINGS] + \
         [c for _, d, n in RATE_MAPPINGS for c in (d, n)]
missing = sorted(set(needed) - set(df.columns))
if missing:
    raise KeyError(f"Columns missing from {input_path.name}: {missing}")


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