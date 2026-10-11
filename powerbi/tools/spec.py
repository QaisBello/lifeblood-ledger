"""Power BI version of the Lifeblood Ledger (One Health Lifesavers blood drives). Run from powerbi/:

    python tools/spec.py        # writes Lifeblood_Ledger.pbip and its folders
    python tools/validate.py    # schema and reference checks
    python tools/expected.py    # what the visuals should show, checked against the README's headline figures

This replaces the manual BUILD-GUIDE.md with a project that opens ready-made. The measures are those in measures.dax, with
boolean filters written with == (in DAX, BLANK() = FALSE() is true). The web dashboard's Sankey needs a custom visual, so
the donor journey here is Power BI's native funnel over a journey table built in Power Query.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pbikit import C, M, build, card, color, lit, slicer, text_box, visual  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "Lifeblood_Ledger"
RED, PLUM, GREY, INK = "#D0304A", "#6B5A60", "#B9AEB1", "#1E1416"

TABLES = {
    "Responses": dict(
        file="fact_responses.csv",
        description="One row per donor check-in (273) across three drives, anonymised. Self-reported form data.",
        columns=[("response_id", "string", {"isKey": True, "isHidden": True}), ("donor_id", "string", {"isHidden": True}),
                 ("drive_id", "string", {"isHidden": True}), ("drive_name", "string", {"isHidden": True}),
                 ("drive_date", "dateTime", {"isHidden": True}), ("submitted_at", "dateTime", {"isHidden": True}),
                 ("submit_hour", "int64", {}), ("age", "double", {"formatString": "0"}), ("age_band", "string", {"sortByColumn": "Age Order"}),
                 ("underage", "boolean", {}), ("gender", "string", {}), ("occupation", "string", {}), ("institution_group", "string", {}),
                 ("blood_group", "string", {}), ("abo", "string", {"isHidden": True}), ("rh", "string", {"isHidden": True}),
                 ("genotype", "string", {}), ("prior_donations", "int64", {"isHidden": True}),
                 ("prior_bucket", "string", {"sortByColumn": "History Order"}), ("first_time", "boolean", {}),
                 ("is_returning_to_ohls", "boolean", {}), ("has_later_drive", "boolean", {}), ("came_back_later", "boolean", {}),
                 ("donated", "boolean", {}), ("deferral_reason", "string", {}), ("deferral_reason_text", "string", {"isHidden": True}),
                 ("will_return", "boolean", {}), ("wants_reminder", "boolean", {}), ("experience_text", "string", {}),
                 ("experience_sentiment", "string", {})],
        added=[("Age Order", "int64", {"isHidden": True}), ("History Order", "int64", {"isHidden": True})],
        m_extra='''
            #"Age Order" = Table.AddColumn(#"Filtered Rows", "Age Order", each
                List.PositionOf({"Under 18", "18-19", "20-21", "22-24", "25+", "Unknown"}, [age_band]), Int64.Type),
            #"History Order" = Table.AddColumn(#"Age Order", "History Order", each
                List.PositionOf({"First-timer", "1 prior", "2 prior", "3-4 prior", "5+ prior"}, [prior_bucket]), Int64.Type)
        ''', m_last="History Order"),
    "Drives": dict(
        file="dim_drive.csv", description="The three drives: Valentine's Day 2025, World Blood Donor Day 2025, Valentine's Day 2026.",
        columns=[("drive_id", "string", {"isKey": True, "isHidden": True}), ("drive_name", "string", {"sortByColumn": "drive_seq"}),
                 ("drive_date", "dateTime", {"formatString": "dd mmm yyyy"}), ("drive_seq", "int64", {"isHidden": True}),
                 ("campaign", "string", {})]),
    "Donors": dict(
        file="dim_donor.csv", description="One row per anonymised donor (260), with the drives they attended.",
        columns=[("donor_id", "string", {"isKey": True, "isHidden": True}), ("drives_attended", "int64", {}),
                 ("first_drive", "string", {}), ("last_drive", "string", {}), ("times_donated_with_ohls", "int64", {})]),
    "Journey": dict(
        description="The return journey for check-ins at drives with a later drive (the 2025 drives): checked in, promised to come back, "
                    "came back. One row per check-in per stage reached; built in Power Query for the funnel.",
        m='''
let
    Source = Csv.Document(Web.Contents(BaseUrl, [RelativePath = "fact_responses.csv"]), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Base = Table.SelectRows(Table.SelectColumns(Promoted, {"response_id", "has_later_drive", "will_return", "came_back_later"}),
        each Text.Lower([has_later_drive]) = "true"),
    Stage1 = Table.AddColumn(Base, "Stage", each "1. Checked in (2025 drives)"),
    Stage2 = Table.AddColumn(Table.SelectRows(Base, each Text.Lower([will_return]) = "true"), "Stage", each "2. Promised to come back"),
    Stage3 = Table.AddColumn(Table.SelectRows(Base, each Text.Lower([came_back_later]) = "true"), "Stage", each "3. Came back"),
    Combined = Table.SelectColumns(Table.Combine({Stage1, Stage2, Stage3}), {"response_id", "Stage"}),
    Result = Table.TransformColumnTypes(Combined, {{"response_id", type text}, {"Stage", type text}})
in
    Result''',
        columns=[("response_id", "string", {"isHidden": True}), ("Stage", "string", {})]),
}

RELATIONSHIPS = [
    (("Responses", "drive_id"), ("Drives", "drive_id"), {}),
    (("Responses", "donor_id"), ("Donors", "donor_id"), {}),
    (("Journey", "response_id"), ("Responses", "response_id"), {"crossFilteringBehavior": "bothDirections"}),
]

R = "Responses"
MEASURES = [
    ("Check-ins", R, "Drive", "#,0", "COUNTROWS ( Responses )", "Donor check-ins (form responses after de-duplication)."),
    ("Units Collected", R, "Drive", "#,0", "CALCULATE ( [Check-ins], Responses[donated] == TRUE () )", "Units of whole blood collected."),
    ("Deferrals", R, "Screening", "#,0", "CALCULATE ( [Check-ins], Responses[donated] == FALSE () )",
     "Check-ins turned away at screening (blank for the Donated reason, so bar charts leave it out)."),
    ("Donation Rate", R, "Drive", "0%", "DIVIDE ( [Units Collected], [Check-ins] )", "Share of check-ins who donated."),
    ("Deferral Rate", R, "Screening", "0%", "DIVIDE ( [Deferrals], [Check-ins] )", "Share of check-ins deferred."),
    ("First-timer Share", R, "Drive", "0%", "DIVIDE ( CALCULATE ( [Check-ins], Responses[first_time] == TRUE () ), [Check-ins] )",
     "Share who had never donated before."),
    ("Unique Donors", R, "Drive", "#,0", "DISTINCTCOUNT ( Responses[donor_id] )", "Distinct donors."),
    ("Measurable Check-ins", R, "Return", "#,0", "CALCULATE ( [Check-ins], Responses[has_later_drive] == TRUE () )",
     "Check-ins at drives that have a later drive, so return can be measured."),
    ("Promised Return %", R, "Return", "0%", """DIVIDE (
    CALCULATE ( [Check-ins], Responses[has_later_drive] == TRUE (), Responses[will_return] == TRUE () ),
    [Measurable Check-ins]
)""", "Said they would come back."),
    ("Actual Return %", R, "Return", "0%", """DIVIDE (
    CALCULATE ( [Check-ins], Responses[has_later_drive] == TRUE (), Responses[came_back_later] == TRUE () ),
    [Measurable Check-ins]
)""", "Were seen at a later drive."),
    ("Return Gap", R, "Return", '0" points"', "( [Promised Return %] - [Actual Return %] ) * 100", "Promise minus reality, in percentage points."),
    ("Reminder Opt-in %", R, "Return", "0%", "DIVIDE ( CALCULATE ( [Check-ins], Responses[wants_reminder] == TRUE () ), [Check-ins] )",
     "Asked to be reminded about the next drive."),
    ("Unknown Blood Group %", R, "Screening", "0%", 'DIVIDE ( CALCULATE ( [Check-ins], Responses[blood_group] = "Unknown" ), [Check-ins] )',
     "Did not know their blood group."),
    ("Low PCV/Hb Share of Deferrals", R, "Screening", "0%",
     'DIVIDE ( CALCULATE ( [Check-ins], Responses[deferral_reason] = "Low PCV / Haemoglobin" ), [Deferrals] )',
     "Deferrals caused by low packed cell volume or haemoglobin."),
    ("Female Deferral Rate", R, "Screening", "0%",
     'CALCULATE ( [Deferral Rate], REMOVEFILTERS ( Responses[gender] ), Responses[gender] = "Female" )', "Ignores any gender slicer."),
    ("Male Deferral Rate", R, "Screening", "0%",
     'CALCULATE ( [Deferral Rate], REMOVEFILTERS ( Responses[gender] ), Responses[gender] = "Male" )', "Ignores any gender slicer."),
    ("Journey Headline", R, "Return", "General", """IF (
    ISBLANK ( [Measurable Check-ins] ),
    "Return can't be measured for the latest drive yet",
    FORMAT ( [Promised Return %], "0%" ) & " promised to come back. " & FORMAT ( [Actual Return %], "0%" ) & " did."
)""", "Dynamic headline for the journey."),
    ("Comments", R, "Voice", "#,0", "CALCULATE ( [Check-ins], NOT ISBLANK ( Responses[experience_text] ) )",
     "Check-ins that left a written comment (blank otherwise, so the quote table lists only comments)."),
    ("Journey Check-ins", "Journey", "Return", "#,0", "DISTINCTCOUNT ( Journey[response_id] )", "Check-ins reaching each journey stage."),
]

p1, p2, p3 = "overview", "screening", "return"
red_fill = {"dataPoint": [{"properties": {"fill": color(RED)}}], "labels": [{"properties": {"show": lit(True)}}]}
PAGES = [
    (p1, "Overview", [
        text_box(p1, "title", 24, 8, 560, 44, "Lifeblood Ledger · One Health Lifesavers, Lagos", 16),
        slicer(p1, "drive", 600, 4, 160, 60, C("Drives", "drive_name", "Drive"), None),
        slicer(p1, "gender", 772, 4, 160, 60, C(R, "gender", "Gender"), None),
        slicer(p1, "campus", 944, 4, 156, 60, C(R, "institution_group", "Campus"), None),
        slicer(p1, "history", 1112, 4, 144, 60, C(R, "prior_bucket", "History"), None),
        card(p1, "ci", 24, 76, 236, 96, M(R, "Check-ins", "Check-ins")),
        card(p1, "units", 272, 76, 236, 96, M(R, "Units Collected", "Units collected")),
        card(p1, "rate", 520, 76, 236, 96, M(R, "Donation Rate", "Donation rate")),
        card(p1, "first", 768, 76, 236, 96, M(R, "First-timer Share", "First-timers")),
        card(p1, "back", 1016, 76, 240, 96, M(R, "Actual Return %", "Came back to a later drive")),
        visual(p1, "journey", "funnel", 24, 184, 760, 524, {"Category": [C("Journey", "Stage")], "Y": [M("Journey", "Journey Check-ins", "Check-ins")]},
               "The return journey (2025 drives, which have a later drive to come back to)",
               objects={"dataPoint": [{"properties": {"fill": color(RED)}}]}, sort=(C("Journey", "Stage"), "Ascending"), z=10),
        card(p1, "headline", 800, 184, 456, 160, M(R, "Journey Headline", "The return gap"), size=16),
        card(p1, "remind", 800, 356, 456, 112, M(R, "Reminder Opt-in %", "Asked for a reminder")),
        card(p1, "unknown", 800, 480, 456, 112, M(R, "Unknown Blood Group %", "Didn't know their blood group")),
        card(p1, "gap", 800, 604, 456, 104, M(R, "Return Gap", "Promise minus reality")),
    ]),
    (p2, "Screening", [
        text_box(p2, "title", 24, 8, 1232, 44, "Why donors are turned away", 16),
        card(p2, "fem", 24, 60, 300, 96, M(R, "Female Deferral Rate", "Women deferred")),
        card(p2, "male", 336, 60, 300, 96, M(R, "Male Deferral Rate", "Men deferred")),
        card(p2, "pcv", 648, 60, 300, 96, M(R, "Low PCV/Hb Share of Deferrals", "Deferrals from low PCV / Hb")),
        card(p2, "def", 960, 60, 296, 96, M(R, "Deferral Rate", "Deferral rate")),
        visual(p2, "reasons", "clusteredBarChart", 24, 168, 500, 260, {"Category": [C(R, "deferral_reason", "Reason")], "Y": [M(R, "Deferrals")]},
               "Deferral reasons", objects=red_fill, sort=(M(R, "Deferrals"), "Descending"), z=10),
        visual(p2, "gender", "clusteredBarChart", 540, 168, 340, 260, {"Category": [C(R, "gender", "Gender")], "Y": [M(R, "Deferral Rate")]},
               "Deferral rate by gender", objects=red_fill, z=11),
        visual(p2, "age", "clusteredBarChart", 896, 168, 360, 260, {"Category": [C(R, "age_band", "Age")], "Y": [M(R, "Deferral Rate")]},
               "Deferral rate by age", objects={**red_fill, "dataPoint": [{"properties": {"fill": color(PLUM)}}]},
               sort=(C(R, "age_band"), "Ascending"), z=12),
        visual(p2, "blood", "clusteredColumnChart", 24, 440, 600, 268, {"Category": [C(R, "blood_group", "Blood group")],
                                                                          "Y": [M(R, "Check-ins"), M(R, "Units Collected")]},
               "Blood groups: check-ins and units", objects={"dataPoint": [{"properties": {"fill": color(GREY)}, "selector": {"metadata": "Responses.Check-ins"}},
                                                                            {"properties": {"fill": color(RED)}, "selector": {"metadata": "Responses.Units Collected"}}]},
               sort=(M(R, "Check-ins"), "Descending"), z=13),
        visual(p2, "pulse", "lineChart", 640, 440, 616, 268, {"Category": [C(R, "submit_hour", "Hour")], "Y": [M(R, "Check-ins")],
                                                              "Series": [C("Drives", "drive_name", "Drive")]},
               "Drive-day pulse: check-ins by hour", sort=(C(R, "submit_hour"), "Ascending"), z=14),
    ]),
    (p3, "Return and voice", [
        text_box(p3, "title", 24, 8, 1232, 44, "Who came back, and how it felt (self-reported form data, n = 273)", 16),
        visual(p3, "drives", "tableEx", 24, 60, 600, 200,
               {"Values": [C("Drives", "drive_name", "Drive"), M(R, "Check-ins"), M(R, "Units Collected", "Units"), M(R, "Measurable Check-ins", "Measurable"),
                           M(R, "Promised Return %", "Promised"), M(R, "Actual Return %", "Came back")]},
               "By drive (the latest drive has no later drive yet, so return is blank)", sort=(C("Drives", "drive_name"), "Ascending"), z=10),
        visual(p3, "history", "clusteredBarChart", 640, 60, 616, 200, {"Category": [C(R, "prior_bucket", "Donation history")], "Y": [M(R, "Check-ins")]},
               "Donation history", objects={"dataPoint": [{"properties": {"fill": color(PLUM)}}], "labels": [{"properties": {"show": lit(True)}}]},
               sort=(C(R, "prior_bucket"), "Ascending"), z=11),
        visual(p3, "sent", "clusteredBarChart", 24, 272, 400, 436, {"Category": [C(R, "experience_sentiment", "Sentiment")], "Y": [M(R, "Check-ins")]},
               "How it felt (asked at Valentine's Day 2026)", objects={"dataPoint": [{"properties": {"fill": color(RED)}}], "labels": [{"properties": {"show": lit(True)}}]},
               sort=(M(R, "Check-ins"), "Descending"), z=12),
        visual(p3, "quotes", "tableEx", 440, 272, 816, 436,
               {"Values": [C(R, "experience_text", "In their words"), C(R, "experience_sentiment", "Sentiment"), M(R, "Comments", "n")]},
               "What donors said", z=13),
    ]),
]

SPEC = dict(name=NAME, root=ROOT, tables=TABLES, measures=MEASURES, relationships=RELATIONSHIPS, pages=PAGES,
            base_url="https://raw.githubusercontent.com/QaisBello/One-health-life-savers-blood-ledger/main/data/cleaned/",
            base_desc="Folder of cleaned, anonymised CSVs from this repo (data/cleaned). Point it at a local folder or another branch to test.")

if __name__ == "__main__":
    build(SPEC)
