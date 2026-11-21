"""Pure KPI formulas. No data access here, so each one can be checked by hand.

Definitions match .claude/skills/kpi-glossary/SKILL.md.
"""

from __future__ import annotations


def _ratio(numerator: float, denominator: float) -> float | None:
    """Return numerator / denominator, or None when the denominator is 0."""
    return None if denominator == 0 else numerator / denominator


def availability(run_time_min: float, planned_production_min: float) -> float | None:
    """Run time ÷ planned production time."""
    return _ratio(run_time_min, planned_production_min)


def performance(ideal_cycle_time_s: float, total_count: int, run_time_min: float) -> float | None:
    """(Ideal cycle time × total count) ÷ run time, both in seconds."""
    return _ratio(ideal_cycle_time_s * total_count, run_time_min * 60)


def quality(good_count: int, total_count: int) -> float | None:
    """Good count ÷ total count (good = good on the first pass)."""
    return _ratio(good_count, total_count)


def oee(avail: float | None, perf: float | None, qual: float | None) -> float | None:
    """Availability × performance × quality."""
    if None in (avail, perf, qual):
        return None
    return avail * perf * qual


def oee_loss_minutes(
    planned_production_min: float,
    run_time_min: float,
    ideal_cycle_time_s: float,
    total_count: int,
    good_count: int,
) -> dict[str, float]:
    """Split the gap between planned time and good output into the three OEE losses (minutes)."""
    ideal_min_per_part = ideal_cycle_time_s / 60
    return {
        "availability_loss_min": planned_production_min - run_time_min,
        "performance_loss_min": run_time_min - ideal_min_per_part * total_count,
        "quality_loss_min": ideal_min_per_part * (total_count - good_count),
    }


def scrap_rate(scrap_count: int, total_count: int) -> float | None:
    return _ratio(scrap_count, total_count)


def first_pass_yield(good_first_time: int, total_count: int) -> float | None:
    return _ratio(good_first_time, total_count)


def mtbf(run_time_min: float, failures: int) -> float | None:
    """Mean time between failures, in minutes. None when there were no failures."""
    return _ratio(run_time_min, failures)


def mttr(repair_minutes: list[float]) -> float | None:
    """Mean time to repair, in minutes."""
    return _ratio(sum(repair_minutes), len(repair_minutes))


def planned_maintenance_share(planned_work_orders: int, all_work_orders: int) -> float | None:
    return _ratio(planned_work_orders, all_work_orders)


def downtime_cost_eur(downtime_min: float, production_value_eur_per_hour: float) -> float:
    """Downtime hours × production value per hour (an ASSUMED value)."""
    return downtime_min / 60 * production_value_eur_per_hour
