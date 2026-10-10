# Data dictionary

## fact_responses.csv (one row per check-in)
| Column | Type | Description |
|---|---|---|
| response_id | text | `R-0001`… in submission order |
| donor_id | text | `D-0001`… anonymous person ID, stable across drives |
| drive_id | text | `VAL25`, `WBDD25`, `VAL26` |
| drive_name, drive_date | text, date | Drive label and date |
| submitted_at | datetime | Form submission time, rounded to the minute |
| submit_hour | int | Hour of submission (proxy for clinic flow) |
| age | int | Age in years; blank if implausible |
| age_band | text | Under 18, 18-19, 20-21, 22-24, 25+, Unknown |
| underage | bool | Age < 18 |
| gender | text | Female, Male, Not captured |
| occupation | text | Student, Non-student |
| institution_group | text | LASUCOM, LASU (Main), Other University, Workplace / Other, Unknown |
| blood_group | text | O+, O-, A+, A-, B+, B-, AB+, AB-, Unknown |
| abo, rh | text | Blood group split into ABO type and Rh factor |
| genotype | text | AA, AS, AC, Unknown; "Not asked" outside WBDD '25 |
| prior_donations | int | Donations before this drive (5-10 → 6, >10 → 11) |
| prior_bucket | text | First-timer, 1 prior, 2 prior, 3-4 prior, 5+ prior |
| first_time | bool | prior_donations = 0 |
| is_returning_to_ohls | bool | Person attended an earlier OHLS drive in this dataset |
| has_later_drive | bool | A later drive exists, so return can be measured |
| came_back_later | bool | Person appears at a later drive |
| donated | bool | Answer to "Were you able to donate?" |
| deferral_reason | text | Donated, Low PCV / Haemoglobin, Low body weight, Underage, Menstruation, Fasting, Medication, Not specified |
| deferral_reason_text | text | Original free-text answer |
| will_return | bool | Said they would donate at the next drive |
| wants_reminder | bool | Opted in to a reminder |
| experience_text | text | "How was the experience?" (Val's Day '26 only) |
| experience_sentiment | text | Positive, Neutral, Mixed / Negative, Did not donate, Not asked |

## dim_drive.csv
drive_id, drive_name, drive_date, drive_seq (1-3), campaign (Valentine / World Blood Donor Day)

## dim_donor.csv
donor_id, drives_attended, first_drive, last_drive, times_donated_with_ohls

## data_quality_log.csv
drive, issue, rows_affected, action. One row per cleaning rule applied.
