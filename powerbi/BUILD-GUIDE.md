# Lifeblood Ledger · Power BI build guide

Data: `../data/cleaned/fact_responses.csv`, `dim_drive.csv`, `dim_donor.csv`. Theme: `lifeblood-theme.json`. Measures: `measures.dax`.

## 1. Load and model (10 min)
1. Get data > Text/CSV > load the three CSVs from `data/cleaned`.
2. Power Query: set `submitted_at` to Date/Time, `drive_date` to Date, `age` to Whole Number, all `True/False` columns to True/False. Close & Apply.
3. Model view relationships (single direction, many-to-one):
   - `fact_responses[drive_id]` -> `dim_drive[drive_id]`
   - `fact_responses[donor_id]` -> `dim_donor[donor_id]`
4. Sort columns: `dim_drive[drive_name]` by `drive_seq`; `age_band` and `prior_bucket` by a small sort column (or use the order in step 6 visuals).
5. View > Themes > Browse for themes > `lifeblood-theme.json`.
6. Create a `_Measures` table and paste in each measure from `measures.dax`.

## 2. Page 1 · Overview (16:9)
| Zone | Visual | Fields |
|---|---|---|
| Top strip | 4 slicers (tile style): Drive, Gender, Campus, History | `dim_drive[drive_name]`, `gender`, `institution_group`, `prior_bucket` |
| KPI row | 5 Card (new) visuals | Check-ins, Units Collected, Donation Rate, First-timer Share, Actual Return % (reference label: Promised Return %) |
| Hero | Sankey (AppSource: "Sankey Chart" by Microsoft) | Source/Destination built from an unpivoted journey table (see section 4) |
| Right of hero | Card | Journey Headline |

## 3. Page 2 · Screening
- Bar chart: `deferral_reason` (filter out "Donated") x Deferrals, sorted descending. Data colours: fx > Field value > Deferral Bar Colour.
- Bar chart: `gender` x Deferral Rate; second bar chart `age_band` x Deferral Rate. Add a constant line at 0.4.
- Card pair: Female Deferral Rate vs Male Deferral Rate.
- Column chart "vials": `blood_group` x Check-ins, legend `donated`. Set column width to narrow and round corners to 10.
- Line chart: `submit_hour` (11–16) x Check-ins, legend `drive_name` (the drive-day pulse).

## 4. Journey table for the Sankey (Power Query)
Reference `fact_responses`, add three custom columns, then unpivot into Source/Destination pairs:
```
Stage1 = if [donated] then "Donated" else if [deferral_reason] = "Low PCV / Haemoglobin" then "Low PCV / Hb" else if [deferral_reason] = "Low body weight" then "Low weight" else "Other deferral"
Stage2 = if [will_return] then "Will return" else "Won't return"
Stage3 = if not [has_later_drive] then "Too recent to tell" else if [came_back_later] then "Came back" else "Not back yet"
```
Create three queries (Checked in -> Stage1, Stage1 -> Stage2, Stage2 -> Stage3), each with columns Source, Destination, response_id; Append them into `journey_links`. Relate `journey_links[response_id]` -> `fact_responses[response_id]` (bi-directional) so slicers filter the Sankey. Weight = count of response_id.

## 5. Page 3 · Retention & voice
- Matrix: rows `dim_drive[drive_name]`, values Measurable Check-ins, Actual Return %.
- Table: `experience_text`, `experience_sentiment` filtered to Val's Day 2026.
- 100% stacked bar: `experience_sentiment` x Check-ins.

## 6. Interactions and finish
- Format > Edit interactions: let the deferral-reason bar and blood-group columns cross-filter everything.
- Add a "Reset filters" bookmark button.
- Add a text box on each page with the source note: self-reported form data, n = 273 after de-duplication.
