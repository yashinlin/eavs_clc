from pathlib import Path
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
yaml_path = ROOT / "eavs/assets/column_mappings/2024_3_corrected_expanded_no_derived.yaml"
raw_dir = ROOT / "data/raw/2024"

excel_files = list(raw_dir.rglob("*.xls*"))
assert len(excel_files) == 1, excel_files

with open(yaml_path, "r") as f:
    config = yaml.safe_load(f)

columns = config["columns"]
mapping = {c["raw_name"]: c["name"] for c in columns if "raw_name" in c and "name" in c}

df = pd.read_excel(excel_files[0], engine="openpyxl", dtype=str)

keep = [c for c in mapping if c in df.columns]
out = df[keep].rename(columns={c: mapping[c] for c in keep})

out_dir = ROOT / "data/cleaned"
out_dir.mkdir(parents=True, exist_ok=True)

out.to_parquet(out_dir / "2024_cleaned_candidate.parquet", index=False)
out.to_csv(out_dir / "2024_cleaned_candidate.csv", index=False)

print(out.shape)
print(out.columns.tolist()[:20])