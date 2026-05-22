from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

input_path = ROOT / "data/cleaned/2024_dashboard_candidate.csv"
output_path = ROOT / "data/cleaned/2024_state_rejection_rates_candidate.csv"

df = pd.read_csv(input_path)

id_cols = ["state", "state_abbr"]

count_cols = [
    "mail_returned_by_voters",
    "mail_ballots_rejected_total",
    "provisional_ballots_cast_total",
    "provisional_ballots_rejected_total",
]

for col in count_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

state = (
    df.groupby(id_cols, dropna=False)[count_cols]
    .sum(min_count=1)
    .reset_index()
)

state["mail_rejection_numerator"] = state["mail_ballots_rejected_total"]
state["mail_rejection_denominator"] = state["mail_returned_by_voters"]

state["provisional_rejection_numerator"] = state["provisional_ballots_rejected_total"]
state["provisional_rejection_denominator"] = state["provisional_ballots_cast_total"]

state["mail_ballot_rejection_rate"] = (
    state["mail_rejection_numerator"] / state["mail_rejection_denominator"]
)

state["provisional_ballot_rejection_rate"] = (
    state["provisional_rejection_numerator"]
    / state["provisional_rejection_denominator"]
)

output_cols = [
    "state",
    "state_abbr",
    "mail_rejection_numerator",
    "mail_rejection_denominator",
    "mail_ballot_rejection_rate",
    "provisional_rejection_numerator",
    "provisional_rejection_denominator",
    "provisional_ballot_rejection_rate",
]

out = state[output_cols].copy()

out.to_csv(output_path, index=False)

print(f"Saved: {output_path}")
pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

print(out.to_string(index=False))