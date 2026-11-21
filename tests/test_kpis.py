"""KPI checks against hand calculations (the 'Excel check')."""

import pytest

from handover import data, kpis, plant


def test_textbook_oee_example():
    # Classic worked example: 480 min shift, 60 min planned breaks, 47 min downtime,
    # ideal cycle 1.0 s, 19,271 parts, 423 rejects.
    ppt, run = 420, 373
    a = kpis.availability(run, ppt)
    p = kpis.performance(1.0, 19271, run)
    q = kpis.quality(19271 - 423, 19271)
    assert a == pytest.approx(0.8881, abs=1e-4)
    assert p == pytest.approx(0.8611, abs=1e-4)
    assert q == pytest.approx(0.9781, abs=1e-4)
    assert kpis.oee(a, p, q) == pytest.approx(0.7479, abs=1e-4)


def test_line2_last_night_by_hand():
    """Line 2, night of 2026-11-20, calculated by hand from the production log row.

    planned production = 480 - 30 break = 450 min
    run time           = 450 - 65 unplanned - 20 changeover = 365 min
    availability       = 365 / 450              = 81.1 %
    performance        = 60 s x 277 / (365 x 60 s) = 75.9 %
    quality            = 255 / 277              = 92.1 %
    OEE                = 0.8111 x 0.7589 x 0.9206 = 56.7 %
    """
    k = plant.shift_kpis("L2", "2026-11-20", "night")
    i = k["inputs"]
    assert (i["planned_production_min"], i["run_time_min"], i["total_count"], i["good_count"]) == (450, 365, 277, 255)
    assert k["availability_pct"] == 81.1
    assert k["performance_pct"] == 75.9
    assert k["quality_pct"] == 92.1
    assert k["oee_pct"] == 56.7
    assert k["gap_to_target_pp"] == -18.3
    # 65 min unplanned x 4500 EUR/h (assumed) = 4875 EUR
    assert k["unplanned_downtime_cost_eur_assumed"] == 4875
    # The visible stop is not the biggest loss: slow running after the restart is.
    assert k["loss_minutes"] == {"availability_loss_min": 85, "performance_loss_min": 88.0, "quality_loss_min": 22.0}
    assert k["biggest_loss"] == "performance"


def test_losses_add_up_to_oee_gap():
    """Planned time minus the three losses = minutes of good parts at ideal speed (= OEE x planned time)."""
    for r in data.production_log().itertuples():
        k = plant.shift_kpis(r.line, r.shift_date, r.shift)
        good_min = r.planned_production_min - sum(k["loss_minutes"].values())
        oee_exact = kpis.oee(kpis.availability(r.run_time_min, r.planned_production_min),
                             kpis.performance(r.ideal_cycle_time_s, r.total_count, r.run_time_min),
                             kpis.quality(r.good_count, r.total_count))
        assert good_min == pytest.approx(oee_exact * r.planned_production_min, abs=0.2)


def test_mtbf_mttr_line2_week():
    m = plant.mtbf_mttr("L2")
    assert m["failures"] == 6                       # E04 E10 E16 E18 E21 E22
    assert m["total_repair_min"] == 128             # 18+22+26+14+30+18
    assert m["mttr_min"] == 21.3                    # 128 / 6
    assert m["mtbf_min"] == round(m["run_time_min"] / 6, 1)


def test_maintenance_mix():
    mix = plant.maintenance_mix()
    assert (mix["planned_work_orders"], mix["all_work_orders"]) == (6, 16)
    assert mix["planned_share_pct"] == 37.5
    assert mix["assessment"] == "reactive (firefighting)"
    assert [w["wo_id"] for w in mix["overdue_preventive"]] == ["WO-1013"]


def test_failure_mode_ranking():
    ev = plant.downtime_events()
    assert list(ev["unplanned_by_failure_mode"])[0] == "HDF"
    assert ev["unplanned_by_failure_mode"]["HDF"] == {"stops": 4, "minutes": 130}
    assert list(ev["unplanned_minutes_by_machine"])[0] == "CNC-21"


def test_zero_denominators_return_none():
    assert kpis.availability(0, 0) is None
    assert kpis.mtbf(100, 0) is None
    assert kpis.mttr([]) is None
    assert kpis.oee(None, 0.9, 0.9) is None


def test_bad_inputs_raise():
    with pytest.raises(ValueError):
        plant.shift_kpis("L9", "2026-11-20", "night")
    with pytest.raises(ValueError):
        plant.shift_kpis("L2", "2026-11-20", "midnight")
