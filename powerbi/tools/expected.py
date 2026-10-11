"""What the Power BI report should show, recomputed in pandas and checked against the README's headline figures.
Run from powerbi/:  python tools/expected.py   (writes docs/expected_values.md; exit code 1 on any disagreement)"""
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN = os.path.join(os.path.dirname(ROOT), "data", "cleaned")
f = pd.read_csv(os.path.join(CLEAN, "fact_responses.csv"))
problems = []


def check(label, got, want):
    if got != want:
        problems.append(f"{label}: {got} vs README {want}")


meas = f[f.has_later_drive]
pr, ar = (meas.will_return.mean(), meas.came_back_later.mean())
defer = f[~f.donated]
fem = f[f.gender == "Female"]
male = f[f.gender == "Male"]
check("Check-ins", len(f), 273)
check("Units", int(f.donated.sum()), 192)
check("Donation rate", round(100 * f.donated.mean()), 70)
check("Low PCV/Hb share of deferrals", round(100 * (defer.deferral_reason == "Low PCV / Haemoglobin").mean()), 58)
check("Female deferral", round(100 * (~fem.donated).mean()), 49)
check("Male deferral", round(100 * (~male.donated).mean()), 6)
check("Came back", (int(meas.came_back_later.sum()), len(meas)), (13, 195))
check("Promised", round(100 * pr), 92)
check("Unknown blood group", round(100 * (f.blood_group == "Unknown").mean()), 32)
lines = ["# Expected values", "", "From `tools/expected.py`, checked against the README's headline figures: "
         f"**{'all agree' if not problems else 'DISAGREEMENTS: ' + '; '.join(problems)}**.", "",
         "## Overview (no slicer)", "", "| Card | Expected |", "|---|---:|",
         f"| Check-ins | {len(f)} |", f"| Units collected | {int(f.donated.sum())} |", f"| Donation rate | {f.donated.mean():.0%} |",
         f"| First-timers | {f.first_time.mean():.0%} |", f"| Came back to a later drive | {ar:.0%} |",
         f"| The return gap | {pr:.0%} promised to come back. {ar:.0%} did. |", f"| Asked for a reminder | {f.wants_reminder.mean():.0%} |",
         f"| Didn't know their blood group | {(f.blood_group == 'Unknown').mean():.0%} |", f"| Promise minus reality | {100 * (pr - ar):.0f} points |",
         "", f"Funnel: {len(meas)} checked in (2025 drives) → {int(meas.will_return.sum())} promised → {int(meas.came_back_later.sum())} came back.",
         "", "## Screening", "", "| Card | Expected |", "|---|---:|",
         f"| Women deferred | {(~fem.donated).mean():.0%} |", f"| Men deferred | {(~male.donated).mean():.0%} |",
         f"| Deferrals from low PCV / Hb | {(defer.deferral_reason == 'Low PCV / Haemoglobin').mean():.0%} |", f"| Deferral rate | {(~f.donated).mean():.0%} |"]
os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
open(os.path.join(ROOT, "docs", "expected_values.md"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
sys.exit(1 if problems else 0)
