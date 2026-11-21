"""The eval's expected answers must match the data. If you regenerate the data, this tells you to update them."""

import json
from pathlib import Path

from evals.run_evals import grade
from handover import plant

Q = {q["id"]: q for q in json.loads((Path(__file__).parents[1] / "evals" / "questions.json").read_text())}
LAST_NIGHT = ("L2", "2026-11-20", "night")


def test_expected_numbers_match_tools():
    k = plant.shift_kpis(*LAST_NIGHT)
    assert Q["Q01"]["expected"] == k["oee_pct"]
    assert Q["Q08"]["expected"] == k["scrap_rate_pct"]
    m = plant.mtbf_mttr("L2")
    assert Q["Q03"]["expected"] == m["mttr_min"]
    assert Q["Q04"]["expected"] == m["mtbf_hours"]
    assert Q["Q05"]["expected"] == plant.maintenance_mix()["planned_share_pct"]


def test_expected_text_matches_tools():
    ev = plant.downtime_events()
    assert list(ev["unplanned_by_failure_mode"])[0] in Q["Q02"]["any_of"]
    assert list(ev["unplanned_minutes_by_machine"])[0] in Q["Q06"]["any_of"]
    assert plant.shift_kpis(*LAST_NIGHT)["biggest_loss"] in Q["Q07"]["any_of"]
    assert plant.maintenance_mix()["overdue_preventive"][0]["wo_id"] in Q["Q09"]["all_of"]


def test_grader():
    assert grade(Q["Q01"], "OEE was 56.7 %", None)
    assert grade(Q["Q01"], "x", 56.9)
    assert not grade(Q["Q01"], "x", 62.7)
    assert grade(Q["Q10"], "Run at 85 % feed override [SOP-HDF-01 §3.5]", None)
    assert not grade(Q["Q10"], "Run at 85 % feed override", None)
