from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1] # dynamically finds main project folder

input_path = ROOT / "data/cleaned/2024_cleaned_candidate.csv"
output_dir = ROOT / "data/cleaned"
output_csv = output_dir / "2024_dashboard_candidate.csv"
output_parquet = output_dir / "2024_dashboard_candidate.parquet"

ID_COLS = ["fips_code", "jurisdiction_name", "state", "state_abbr"]

DASHBOARD_COLS = [
    "registered_eligible_voters",
    "active_voters",
    "inactive_voters",
    "total_registrations_received",
    "new_valid_registrations",
    "pre_registrations",
    "duplicate_registrations",
    "registration_updates",
    "rejected_registrations",

    "total_forms_mail_fax_email",
    "new_registrations_mail_fax_email",
    "duplicate_registrations_mail_fax_email",
    "rejected_registrations_mail_fax_email",

    "total_forms_in_person",
    "new_registrations_in_person",
    "duplicate_registrations_in_person",
    "rejected_registrations_in_person",

    "total_forms_online",
    "new_registrations_online",
    "duplicate_registrations_online",
    "rejected_registrations_online",

    "total_forms_dmv",
    "new_registrations_dmv",
    "duplicate_registrations_dmv",
    "rejected_registrations_dmv",

    "total_forms_mandatory_nvra",
    "new_registrations_mandatory_nvra",
    "duplicate_registrations_mandatory_nvra",
    "rejected_registrations_mandatory_nvra",

    "total_forms_disability_agency",
    "new_registrations_disability_agency",
    "duplicate_registrations_disability_agency",
    "rejected_registrations_disability_agency",

    "total_forms_armed_forces",
    "new_registrations_armed_forces",
    "duplicate_registrations_armed_forces",
    "rejected_registrations_armed_forces",

    "total_forms_discretionary_nvra",
    "new_registrations_discretionary_nvra",
    "duplicate_registrations_discretionary_nvra",
    "rejected_registrations_discretionary_nvra",

    "total_forms_advocacy_groups",
    "new_registrations_advocacy_groups",
    "duplicate_registrations_advocacy_groups",
    "rejected_registrations_advocacy_groups",

    "confirmation_notices_sent_total",
    "confirmation_notices_undeliverable",
    "confirmation_notices_status_unknown",

    "voters_removed_total",
    "voters_removed_felony",
    "voters_removed_nonresponse",

    "mail_transmitted_total",
    "mail_returned_by_voters",
    "mail_ballots_counted",
    "mail_ballots_rejected_total",
    "mail_ballots_rejected_late",
    "mail_ballots_rejected_missing_voter_signature",
    "mail_ballots_rejected_missing_witness_signature",
    "mail_ballots_rejected_non_matching_voter_signature",
    "mail_ballots_rejected_unofficial_envelope",
    "mail_ballots_rejected_ballot_missing_from_envelope",
    "mail_ballots_rejected_multiple_ballots_one_envelope",
    "mail_ballots_rejected_envelope_not_sealed",
    "mail_ballots_rejected_no_resident_address",
    "mail_ballots_rejected_voter_deceased",
    "mail_ballots_rejected_voter_already_voted",
    "mail_ballots_rejected_missing_documentation",
    "mail_ballots_rejected_no_ballot_application",
    "mail_ballots_rejected_other_1",
    "mail_ballots_rejected_other_2",
    "mail_ballots_rejected_other_3",

    "provisional_ballots_cast_total",
    "provisional_ballots_fully_counted",
    "provisional_ballots_partially_counted",
    "provisional_ballots_rejected_total",
    "provisional_ballots_rejected_not_registered",
    "provisional_ballots_rejected_wrong_jurisdiction",
    "provisional_ballots_rejected_wrong_precinct",
    "provisional_ballots_rejected_no_id",
    "provisional_ballots_rejected_incomplete",
    "provisional_ballots_rejected_ballot_missing",
    "provisional_ballots_rejected_no_signature",
    "provisional_ballots_rejected_non_matching_signature",
    "provisional_ballots_rejected_already_voted",
]

SENTINELS = {
    "-99": pd.NA,
    "-88": pd.NA,
    "-77": pd.NA,
    "-66": pd.NA,
    -99: pd.NA,
    -88: pd.NA,
    -77: pd.NA,
    -66: pd.NA,
}

df = pd.read_csv(input_path, dtype=str)

requested = ID_COLS + DASHBOARD_COLS
existing = [c for c in requested if c in df.columns]
missing = [c for c in requested if c not in df.columns]

out = df[existing].replace(SENTINELS)

for col in out.columns:
    if col not in ID_COLS:
        out[col] = pd.to_numeric(out[col], errors="coerce")

output_dir.mkdir(parents=True, exist_ok=True)
out.to_csv(output_csv, index=False)
out.to_parquet(output_parquet, index=False)

print(f"Saved: {output_csv}")
print(f"Saved: {output_parquet}")
print(f"Rows, columns: {out.shape}")
print(f"Missing requested columns: {len(missing)}")
for col in missing:
    print(f"- {col}")