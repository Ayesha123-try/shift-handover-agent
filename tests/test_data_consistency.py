"""The synthetic data must agree with itself, like a real MES and CMMS should."""

from handover import data


def test_production_log_time_model():
    log = data.production_log()
    assert (log.planned_production_min == log.shift_length_min - log.planned_stop_min).all()
    assert (log.run_time_min == log.planned_production_min - log.unplanned_downtime_min - log.changeover_min).all()
    assert (log.good_count + log.scrap_count + log.rework_count == log.total_count).all()
    # performance must stay at or below 100 %
    assert (log.ideal_cycle_time_s * log.total_count <= log.run_time_min * 60).all()


def test_downtime_matches_events():
    log = data.production_log().set_index(["line", "shift_date", "shift"])
    ev = data.downtime_events()
    for cat, col in [("unplanned_failure", "unplanned_downtime_min"), ("changeover", "changeover_min")]:
        sums = ev[ev.category == cat].groupby(["line", "shift_date", "shift"]).duration_min.sum()
        for key, minutes in sums.items():
            assert log.loc[key, col] == minutes, key


def test_every_failure_has_a_work_order_with_repair_shorter_than_stop():
    ev = data.downtime_events()
    wo = data.work_orders().set_index("wo_id")
    for e in ev[ev.category == "unplanned_failure"].itertuples():
        w = wo.loc[e.work_order_id]
        assert w.type == "corrective" and w.failure_mode == e.failure_mode
        assert 0 < w.repair_min <= e.duration_min
