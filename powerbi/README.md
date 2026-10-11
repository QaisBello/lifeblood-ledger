# Lifeblood Ledger: Power BI

Three One Health Lifesavers blood drives in Lagos as a Power BI report: who donated, why donors were turned away, and the gap between promising to return and coming back.

This folder is a Power BI project (`Lifeblood_Ledger.pbip`): a TMDL semantic model and a PBIR report. It is generated from one Python spec, checked against Microsoft's JSON schemas, and its numbers are recomputed independently in pandas.

## Open it

1. Open **`Lifeblood_Ledger.pbip`** in Power BI Desktop. In versions before mid-2025, first turn on the preview features for Power BI Project (.pbip), the TMDL model format and the PBIR report format.
2. Click **Refresh**. The model reads this repo's cleaned CSVs from GitHub through the **BaseUrl** parameter. If asked, choose **Anonymous** access for `raw.githubusercontent.com`.
3. Check the visuals against [`docs/expected_values.md`](docs/expected_values.md).

## Pages

- **Overview:** drive, gender, campus and history slicers; check-ins, units, donation rate, first-timers and actual return; the return journey as a funnel; the dynamic headline.
- **Screening:** deferral reasons; deferral rate by gender and age; women vs men; blood groups; check-ins by hour on drive day.
- **Return and voice:** each drive's promised and actual return; donation history; sentiment and donors' own words.

## Model

- **Tables:** Responses, Drives, Donors, Journey.
- **Relationships:** Responses[drive_id] to Drives[drive_id]; Responses[donor_id] to Donors[donor_id]; Journey[response_id] to Responses[response_id] (both directions).
- **19 DAX measures** in display folders: Drive (Check-ins, Units Collected, Donation Rate, First-timer Share, Unique Donors); Screening (Deferrals, Deferral Rate, Unknown Blood Group %, Low PCV/Hb Share of Deferrals, Female Deferral Rate, Male Deferral Rate); Return (Measurable Check-ins, Promised Return %, Actual Return %, Return Gap, Reminder Opt-in %, Journey Headline, Journey Check-ins); Voice (Comments). The full DAX is in [`docs/measures.md`](docs/measures.md).

## From build guide to project

This folder used to hold a manual build guide (`BUILD-GUIDE.md`), the measures (`measures.dax`) and a theme. `Lifeblood_Ledger.pbip` now opens ready-made with the same measures, with boolean filters written `==` (in DAX, `BLANK() = FALSE()` is true). The web dashboard's Sankey needs a custom visual, so the journey here is Power BI's native funnel over a journey table built in Power Query. `tools/expected.py` checks the README's headline figures: all agree.

## Rebuild and check

```bash
pip install jsonschema referencing pandas numpy
python tools/spec.py        # the spec: writes the .pbip and its folders
python tools/validate.py    # Microsoft schemas, field and DAX references, name clashes
python tools/expected.py    # what the report should show, checked against the project's own results
```

`tools/pbikit.py` is a small shared library for writing Power BI projects as code. It is used across the portfolio and encodes lessons from real Power BI Desktop runs: names are case-insensitive; a format string must not start with a quote; empty CSV cells must become null before a type change; in DAX, `BLANK() = FALSE()` is true.
