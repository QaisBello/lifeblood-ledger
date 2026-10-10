"""
Build dashboard/index.html from the cleaned data and src/dashboard_template.html.

Run: python src/build_dashboard.py
"""
import json, os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = os.path.join(ROOT, "data", "cleaned")
f = pd.read_csv(os.path.join(C, "fact_responses.csv"))
drive_idx = {"VAL25": 0, "WBDD25": 1, "VAL26": 2}
donor_idx = {k: i for i, k in enumerate(f.donor_id.unique())}
nz = lambda v, cast=lambda x: x: None if pd.isna(v) else cast(v)

rows = [[drive_idx[r.drive_id], donor_idx[r.donor_id], int(r.submit_hour), nz(r.age, int), r.age_band, r.gender,
         r.institution_group, r.blood_group, r.prior_bucket, int(r.first_time), int(r.donated), r.deferral_reason,
         int(r.will_return), int(r.wants_reminder), nz(r.experience_text), r.experience_sentiment, r.genotype]
        for r in f.itertuples()]
log = pd.read_csv(os.path.join(C, "data_quality_log.csv")).to_dict("records")

tpl = open(os.path.join(ROOT, "src", "dashboard_template.html"), encoding="utf-8").read()
html = tpl.replace("__DATA__", json.dumps({"rows": rows, "log": log}, ensure_ascii=False))
page = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<style>body{margin:0}</style></head><body>' + html + '</body></html>')
os.makedirs(os.path.join(ROOT, "dashboard"), exist_ok=True)
open(os.path.join(ROOT, "dashboard", "index.html"), "w", encoding="utf-8").write(page)
print(f"Built dashboard/index.html with {len(rows)} rows")
