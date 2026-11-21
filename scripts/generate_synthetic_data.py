"""Generate the synthetic plant data for the Shift Handover Agent.

Everything this script writes is SYNTHETIC: a fictional plant with 3 lines,
7 days, 3 shifts a day. The downtime events, work orders and shift notes are
hand-written below so they tell a consistent story. Only the speed and quality
noise is random (fixed seed, so the output is always the same).

Run:  python scripts/generate_synthetic_data.py
"""

from __future__ import annotations

import csv
import json
import math
import random
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "synthetic"
CONFIG = json.loads((ROOT / "config" / "plant_assumptions.json").read_text())

START = date(2026, 11, 14)
DAYS = 7
SHIFTS = ["early", "late", "night"]
LINES = list(CONFIG["lines"])

# ---------------------------------------------------------------------------
# Downtime events (hand-written). Story: CNC-21 on Line 2 overheats more and
# more often (HDF). The preventive work order to replace its cooling fan filter
# is overdue. Tool wear (TWF) on CNC-22 adds to the losses.
# (event_id, line, machine, shift_date, shift, start "YYYY-MM-DD HH:MM",
#  minutes, category, failure_mode, work_order_id, description)
# ---------------------------------------------------------------------------
EVENTS = [
    ("E01", "L1", "CNC-11", "2026-11-14", "early", "2026-11-14 08:10", 20, "changeover", "", "", "Changeover product M to L"),
    ("E02", "L2", "CNC-21", "2026-11-14", "late", "2026-11-14 15:30", 15, "changeover", "", "", "Changeover product L to M"),
    ("E03", "L3", "CNC-31", "2026-11-14", "night", "2026-11-15 01:20", 20, "changeover", "", "", "Changeover product M to H"),
    ("E04", "L2", "CNC-21", "2026-11-15", "late", "2026-11-15 17:05", 25, "unplanned_failure", "HDF", "WO-1001", "Spindle over-temperature alarm, machine stopped"),
    ("E05", "L1", "CNC-12", "2026-11-15", "night", "2026-11-15 23:40", 15, "changeover", "", "", "Changeover product L to M"),
    ("E06", "L1", "CNC-11", "2026-11-16", "early", "2026-11-16 06:00", 60, "planned_maintenance", "", "WO-1002", "Planned spindle lubrication and inspection"),
    ("E07", "L1", "CNC-12", "2026-11-16", "early", "2026-11-16 10:45", 35, "unplanned_failure", "OSF", "WO-1003", "Overload alarm on heavy cut, worn tool"),
    ("E08", "L3", "CNC-31", "2026-11-16", "late", "2026-11-16 18:00", 20, "changeover", "", "", "Changeover product H to L"),
    ("E09", "L3", "CNC-31", "2026-11-17", "early", "2026-11-17 09:15", 15, "unplanned_failure", "RNF", "WO-1004", "Controller froze, no clear cause, reboot"),
    ("E10", "L2", "CNC-21", "2026-11-17", "night", "2026-11-18 02:30", 30, "unplanned_failure", "HDF", "WO-1005", "Spindle over-temperature alarm, machine stopped"),
    ("E11", "L2", "CNC-22", "2026-11-17", "night", "2026-11-18 04:10", 15, "changeover", "", "", "Changeover product M to L"),
    ("E12", "L3", "CNC-31", "2026-11-18", "early", "2026-11-18 06:00", 45, "planned_maintenance", "", "WO-1006", "Planned way-cover and coolant system service"),
    ("E13", "L1", "CNC-11", "2026-11-18", "late", "2026-11-18 16:20", 50, "unplanned_failure", "PWF", "WO-1007", "Spindle drive power fault, drive reset and cable check"),
    ("E14", "L2", "CNC-22", "2026-11-18", "early", "2026-11-18 11:00", 20, "changeover", "", "", "Changeover product L to M"),
    ("E15", "L1", "CNC-12", "2026-11-19", "early", "2026-11-19 07:30", 15, "changeover", "", "", "Changeover product M to L"),
    ("E16", "L2", "CNC-21", "2026-11-19", "late", "2026-11-19 19:40", 35, "unplanned_failure", "HDF", "WO-1008", "Spindle over-temperature alarm, machine stopped"),
    ("E17", "L3", "CNC-31", "2026-11-19", "night", "2026-11-20 03:05", 20, "unplanned_failure", "TWF", "WO-1009", "End mill worn out, tool change"),
    ("E18", "L2", "CNC-22", "2026-11-20", "early", "2026-11-20 12:10", 20, "unplanned_failure", "TWF", "WO-1010", "Drill chipped, tool change"),
    ("E19", "L1", "CNC-11", "2026-11-20", "late", "2026-11-20 14:30", 20, "changeover", "", "", "Changeover product L to M"),
    ("E20", "L2", "CNC-22", "2026-11-20", "night", "2026-11-20 22:15", 20, "changeover", "", "", "Changeover product M to H"),
    ("E21", "L2", "CNC-21", "2026-11-20", "night", "2026-11-21 01:50", 40, "unplanned_failure", "HDF", "WO-1011", "Spindle over-temperature alarm, machine stopped"),
    ("E22", "L2", "CNC-22", "2026-11-20", "night", "2026-11-21 04:20", 25, "unplanned_failure", "TWF", "WO-1012", "End mill broke at end of tool life"),
    ("E23", "L3", "CNC-31", "2026-11-20", "night", "2026-11-20 23:30", 15, "changeover", "", "", "Changeover product L to M"),
]

# (wo_id, line, machine, type, failure_mode, opened, closed, repair_min, status,
#  due_date, linked_event, description)
WORK_ORDERS = [
    ("WO-1001", "L2", "CNC-21", "corrective", "HDF", "2026-11-15 17:06", "2026-11-15 17:30", 18, "closed", "", "E04", "Over-temp alarm. Let spindle cool, cleaned fan grille, restarted. Filter looks dusty."),
    ("WO-1002", "L1", "CNC-11", "preventive", "", "2026-11-10 09:00", "2026-11-16 07:00", 55, "closed", "2026-11-16", "E06", "Quarterly spindle lubrication and inspection."),
    ("WO-1003", "L1", "CNC-12", "corrective", "OSF", "2026-11-16 10:46", "2026-11-16 11:20", 28, "closed", "", "E07", "Overload on heavy cut. Tool was past wear limit. Changed tool, reduced depth of cut."),
    ("WO-1004", "L3", "CNC-31", "corrective", "RNF", "2026-11-17 09:16", "2026-11-17 09:30", 10, "closed", "", "E09", "Controller froze. Rebooted. No fault found in logs."),
    ("WO-1005", "L2", "CNC-21", "corrective", "HDF", "2026-11-18 02:31", "2026-11-18 03:00", 22, "closed", "", "E10", "Over-temp again. Cooled, cleaned grille. Recommend filter replacement (see WO-1013)."),
    ("WO-1006", "L3", "CNC-31", "preventive", "", "2026-11-11 09:00", "2026-11-18 06:45", 42, "closed", "2026-11-18", "E12", "Way-cover and coolant system service."),
    ("WO-1007", "L1", "CNC-11", "corrective", "PWF", "2026-11-18 16:21", "2026-11-18 17:10", 41, "closed", "", "E13", "Drive power fault. Reset drive, found loose motor cable connector, tightened."),
    ("WO-1008", "L2", "CNC-21", "corrective", "HDF", "2026-11-19 19:41", "2026-11-19 20:15", 26, "closed", "", "E16", "Over-temp third time this week. Spindle at 1290 rpm on product H. Filter clogged. Spare filter not in stock."),
    ("WO-1009", "L3", "CNC-31", "corrective", "TWF", "2026-11-20 03:06", "2026-11-20 03:25", 15, "closed", "", "E17", "End mill worn. Tool changed."),
    ("WO-1010", "L2", "CNC-22", "corrective", "TWF", "2026-11-20 12:11", "2026-11-20 12:30", 14, "closed", "", "E18", "Chipped drill. Tool changed. Tool life counter was not reset at last change."),
    ("WO-1011", "L2", "CNC-21", "corrective", "HDF", "2026-11-21 01:51", "2026-11-21 02:30", 30, "closed", "", "E21", "Over-temp, longest stop yet. Temporary fix: cleaned filter with compressed air. Needs new filter."),
    ("WO-1012", "L2", "CNC-22", "corrective", "TWF", "2026-11-21 04:21", "2026-11-21 04:45", 18, "closed", "", "E22", "End mill broke at end of life. 18 parts with burrs scrapped. Tool life counter again not reset."),
    ("WO-1013", "L2", "CNC-21", "preventive", "", "2026-11-05 08:00", "", 0, "open", "2026-11-12", "", "Replace spindle cooling fan filter. OVERDUE: waiting for spare part."),
    ("WO-1014", "L1", "CNC-12", "preventive", "", "2026-11-13 08:00", "2026-11-15 10:20", 20, "closed", "2026-11-15", "", "Way lubrication check (done during break)."),
    ("WO-1015", "L3", "CNC-31", "preventive", "", "2026-11-14 08:00", "2026-11-17 13:40", 15, "closed", "2026-11-17", "", "Coolant concentration check (done during break)."),
    ("WO-1016", "L2", "CNC-22", "preventive", "", "2026-11-15 08:00", "2026-11-18 13:35", 25, "closed", "2026-11-18", "", "Tool magazine inspection (done during break)."),
]

# (note_id, line, shift_date, shift, author_role, text)
SHIFT_NOTES = [
    ("N01", "L1", "2026-11-14", "early", "operator", "Changeover M to L took 20 min, fixture alignment was slow. Otherwise smooth."),
    ("N02", "L2", "2026-11-14", "late", "operator", "Quick changeover to M, 15 min. CNC-21 fan sounds louder than usual."),
    ("N03", "L3", "2026-11-14", "night", "operator", "Changeover to product H, 20 min. No issues."),
    ("N04", "L2", "2026-11-15", "late", "operator", "Line 2 stopped 25 min, CNC-21 spindle over-temp alarm. Let it cool, maintenance cleaned the fan grille, restarted. Running product H at low rpm."),
    ("N05", "L1", "2026-11-15", "night", "operator", "Changeover L to M on CNC-12, 15 min. All fine."),
    ("N06", "L1", "2026-11-16", "early", "shift lead", "Planned lube and inspection on CNC-11 first hour, as scheduled. CNC-12 overload alarm at 10:45 on a heavy cut, tool was past its wear limit. 35 min stop, 9 parts scrapped."),
    ("N07", "L3", "2026-11-16", "late", "operator", "Changeover H to L, 20 min."),
    ("N08", "L3", "2026-11-17", "early", "operator", "CNC-31 controller froze at 09:15. Reboot fixed it, 15 min lost. Maintenance found nothing in the logs."),
    ("N09", "L2", "2026-11-17", "night", "operator", "CNC-21 over-temp again at 02:30, 30 min stop. Shop is cold tonight but the spindle still got hot. Product H, about 1300 rpm."),
    ("N10", "L2", "2026-11-17", "night", "maintenance tech", "CNC-21 fan filter is clogged. Cleaned the grille as a quick fix. The filter replacement work order WO-1013 is still open, no spare filter in stock."),
    ("N11", "L3", "2026-11-18", "early", "shift lead", "Planned coolant and way-cover service on CNC-31, 45 min, done on time."),
    ("N12", "L2", "2026-11-18", "early", "operator", "Changeover L to M on CNC-22, 20 min. 6 extra parts scrapped on first-off check after changeover."),
    ("N13", "L1", "2026-11-18", "late", "operator", "CNC-11 spindle drive power fault at 16:20. Line down 50 min. Maintenance found a loose motor cable connector."),
    ("N14", "L1", "2026-11-19", "early", "operator", "Changeover to L, 15 min. Good shift."),
    ("N15", "L2", "2026-11-19", "late", "operator", "Third CNC-21 over-temp this week, 35 min stop. Ran slower after restart to keep temperature down."),
    ("N16", "L2", "2026-11-19", "late", "shift lead", "Escalated CNC-21 overheating to maintenance planner. Spare filter ordered, delivery unknown."),
    ("N17", "L3", "2026-11-19", "night", "operator", "End mill on CNC-31 worn out at 03:05, 20 min for tool change."),
    ("N18", "L2", "2026-11-20", "early", "operator", "CNC-22 drill chipped at 12:10, 20 min stop. Tool life counter had not been reset at the last tool change."),
    ("N19", "L1", "2026-11-20", "late", "operator", "Changeover L to M, 20 min."),
    ("N20", "L2", "2026-11-20", "night", "operator", "Changeover to product H on CNC-22 at start of shift, 20 min."),
    ("N21", "L2", "2026-11-20", "night", "operator", "Line 2 stopped 40 min at 01:50, CNC-21 spindle overheating again. Cooled and restarted. Ran at 85% feed override for about an hour after restart."),
    ("N22", "L2", "2026-11-20", "night", "maintenance tech", "Cleaned CNC-21 filter with compressed air. Temporary only. Spindle temp will climb again within 1-2 shifts on product H. New filter needed (WO-1013)."),
    ("N23", "L2", "2026-11-20", "night", "operator", "CNC-22 end mill broke at 04:20, 25 min stop. 18 parts with burrs scrapped. Tool life counter not reset again."),
    ("N24", "L3", "2026-11-20", "night", "operator", "Changeover L to M at 23:30, 15 min. Quiet night otherwise."),
    ("N25", "L1", "2026-11-20", "night", "operator", "No stops. CNC-11 running well since the cable fix."),
    ("N26", "L3", "2026-11-20", "late", "operator", "No stops. Coolant level topped up."),
]

# Extra scrap tied to events in the notes: (line, shift_date, shift) -> parts
EXTRA_SCRAP = {
    ("L1", "2026-11-16", "early"): 9,
    ("L2", "2026-11-18", "early"): 6,
    ("L2", "2026-11-20", "night"): 18,
}
# Lower speed after restarts, as told in the notes
SPEED_OVERRIDE = {
    ("L2", "2026-11-19", "late"): 0.79,
    ("L2", "2026-11-20", "night"): 0.76,
}

# Remaining useful life: placeholder in the shape of the turbofan model output.
RUL = [
    ("CNC-11", "L1", 1850, 0.80),
    ("CNC-12", "L1", 1420, 0.75),
    ("CNC-21", "L2", 140, 0.70),
    ("CNC-22", "L2", 960, 0.72),
    ("CNC-31", "L3", 2300, 0.82),
]


def _write_csv(path: Path, header: list[str], rows: list[tuple | list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def build_production_log(rng: random.Random) -> list[list]:
    rows = []
    for d in range(DAYS):
        day = (START + timedelta(days=d)).isoformat()
        for shift in SHIFTS:
            for line in LINES:
                key = (line, day, shift)
                ev = [e for e in EVENTS if (e[1], e[3], e[4]) == key]
                planned_maint = sum(e[6] for e in ev if e[7] == "planned_maintenance")
                unplanned = sum(e[6] for e in ev if e[7] == "unplanned_failure")
                changeover = sum(e[6] for e in ev if e[7] == "changeover")
                planned_stop = CONFIG["planned_break_min"] + planned_maint
                ppt = CONFIG["shift_length_min"] - planned_stop
                run = ppt - unplanned - changeover
                ict = CONFIG["lines"][line]["ideal_cycle_time_s"]
                speed = SPEED_OVERRIDE.get(key, round(rng.uniform(0.80, 0.90), 3))
                total = math.floor(run * 60 / ict * speed)
                scrap = round(total * rng.uniform(0.008, 0.018)) + EXTRA_SCRAP.get(key, 0)
                rework = round(total * rng.uniform(0.003, 0.009))
                good = total - scrap - rework
                rows.append([day, shift, line, CONFIG["shift_length_min"], planned_stop, ppt,
                             unplanned, changeover, run, ict, total, good, scrap, rework])
    return rows


def build_ai4i_sample(rng: random.Random, n: int = 3000) -> list[list]:
    """Synthetic stand-in in the AI4I 2020 schema, using the dataset's documented failure rules."""
    rows = []
    air = 300.0
    for i in range(1, n + 1):
        ptype = rng.choices(["L", "M", "H"], weights=[50, 30, 20])[0]
        air = min(304.5, max(295.3, air + rng.gauss(0, 0.15)))
        proc = air + 10 + rng.gauss(0, 1.0)
        # In AI4I, speed and torque move against each other (power stays near
        # ~6 kW), so draw power and speed, then derive torque.
        rpm = max(1168, rng.gauss(1540, 180))
        power_w = rng.gauss(6300, 1100)
        torque = max(3.8, power_w * 60 / (2 * math.pi * rpm))
        power_w = torque * rpm * 2 * math.pi / 60
        wear = rng.randint(0, 250)
        osf_limit = {"L": 11000, "M": 12000, "H": 13000}[ptype]
        twf = int(200 <= wear <= 240 and rng.random() < 0.06)
        hdf = int((proc - air) < 8.6 and rpm < 1380)
        pwf = int(power_w < 3500 or power_w > 9000)
        osf = int(wear * torque > osf_limit)
        rnf = int(rng.random() < 0.001)
        failure = int(any([twf, hdf, pwf, osf, rnf]))
        rows.append([i, f"{ptype}{10000 + i}", ptype, round(air, 1), round(proc, 1), round(rpm),
                     round(torque, 1), wear, failure, twf, hdf, pwf, osf, rnf])
    return rows


def main() -> None:
    rng = random.Random(42)
    _write_csv(OUT / "production_log.csv",
               ["shift_date", "shift", "line", "shift_length_min", "planned_stop_min",
                "planned_production_min", "unplanned_downtime_min", "changeover_min",
                "run_time_min", "ideal_cycle_time_s", "total_count", "good_count",
                "scrap_count", "rework_count"],
               build_production_log(rng))
    _write_csv(OUT / "downtime_events.csv",
               ["event_id", "line", "machine", "shift_date", "shift", "start", "duration_min",
                "category", "failure_mode", "work_order_id", "description"], EVENTS)
    _write_csv(OUT / "work_orders.csv",
               ["wo_id", "line", "machine", "type", "failure_mode", "opened_at", "closed_at",
                "repair_min", "status", "due_date", "linked_event_id", "description"], WORK_ORDERS)
    _write_csv(OUT / "shift_notes.csv",
               ["note_id", "line", "shift_date", "shift", "author_role", "text"], SHIFT_NOTES)
    _write_csv(OUT / "rul_predictions.csv",
               ["machine", "line", "predicted_rul_hours", "model_confidence", "as_of", "source"],
               [(m, l, r, c, "2026-11-21", "placeholder in C-MAPSS model output shape") for m, l, r, c in RUL])
    _write_csv(OUT / "ai4i_sample.csv",
               ["UDI", "Product ID", "Type", "Air temperature [K]", "Process temperature [K]",
                "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]", "Machine failure",
                "TWF", "HDF", "PWF", "OSF", "RNF"], build_ai4i_sample(rng))
    print(f"Wrote synthetic data to {OUT}")


if __name__ == "__main__":
    main()
