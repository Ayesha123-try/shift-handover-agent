"""Plant analytics: combines the data with the KPI formulas.

Every function returns a plain dict that can be sent to the agent as JSON.
The MCP tools, the tests and the evals all call these functions.
"""

from __future__ import annotations

import functools
import json
from typing import Any

from . import data, kpis


def _plain(fn):
    """Return plain Python types (no numpy) so results are JSON-safe and easy to compare in tests."""
    def default(o):
        return o.item() if hasattr(o, "item") else str(o)

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return json.loads(json.dumps(fn(*args, **kwargs), default=default))
    return wrapper


def _pct(x: float | None) -> float | None:
    return None if x is None else round(x * 100, 1)


def _check_shift(shift: str) -> str:
    shift = shift.lower()
    if shift not in data.SHIFT_ORDER:
        raise ValueError(f"Unknown shift '{shift}'. Use one of: early, late, night.")
    return shift


def _check_line(line: str) -> str:
    line = line.upper()
    if line not in data.config()["lines"]:
        raise ValueError(f"Unknown line '{line}'. Lines: {', '.join(data.config()['lines'])}.")
    return line


# --------------------------------------------------------------------------- shifts

@_plain
def available_shifts() -> dict[str, Any]:
    log = data.production_log()
    keys = log[["shift_date", "shift"]].drop_duplicates()
    keys = keys.assign(_o=keys["shift"].map(data.SHIFT_ORDER)).sort_values(["shift_date", "_o"])
    latest = keys.iloc[-1]
    return {
        "lines": list(data.config()["lines"]),
        "first_shift_date": keys["shift_date"].min(),
        "last_shift_date": keys["shift_date"].max(),
        "latest_shift": {"shift_date": latest["shift_date"], "shift": latest["shift"]},
        "shift_times": data.config()["shifts"],
        "note": "A night shift belongs to the date it starts on (night of 2026-11-20 = 22:00 on 11-20 to 06:00 on 11-21).",
    }


@_plain
def shift_kpis(line: str, shift_date: str, shift: str) -> dict[str, Any]:
    """All OEE-related KPIs for one line and one shift."""
    line, shift = _check_line(line), _check_shift(shift)
    log = data.production_log()
    row = log[(log["line"] == line) & (log["shift_date"] == shift_date) & (log["shift"] == shift)]
    if row.empty:
        raise ValueError(f"No production data for {line} {shift_date} {shift}.")
    r = row.iloc[0]
    cfg = data.config()

    a = kpis.availability(r.run_time_min, r.planned_production_min)
    p = kpis.performance(r.ideal_cycle_time_s, r.total_count, r.run_time_min)
    q = kpis.quality(r.good_count, r.total_count)
    o = kpis.oee(a, p, q)
    losses = kpis.oee_loss_minutes(r.planned_production_min, r.run_time_min, r.ideal_cycle_time_s,
                                   r.total_count, r.good_count)
    biggest = max(losses, key=losses.get)
    value_per_h = cfg["lines"][line]["production_value_eur_per_hour"]

    return {
        "line": line, "shift_date": shift_date, "shift": shift,
        "inputs": {
            "shift_length_min": int(r.shift_length_min),
            "planned_stop_min": int(r.planned_stop_min),
            "planned_production_min": int(r.planned_production_min),
            "unplanned_downtime_min": int(r.unplanned_downtime_min),
            "changeover_min": int(r.changeover_min),
            "run_time_min": int(r.run_time_min),
            "ideal_cycle_time_s": int(r.ideal_cycle_time_s),
            "total_count": int(r.total_count),
            "good_count": int(r.good_count),
            "scrap_count": int(r.scrap_count),
            "rework_count": int(r.rework_count),
        },
        "availability_pct": _pct(a),
        "performance_pct": _pct(p),
        "quality_pct": _pct(q),
        "oee_pct": _pct(o),
        "oee_target_pct": _pct(cfg["oee_target"]),
        "gap_to_target_pp": None if o is None else round((o - cfg["oee_target"]) * 100, 1),
        "scrap_rate_pct": _pct(kpis.scrap_rate(r.scrap_count, r.total_count)),
        "first_pass_yield_pct": _pct(kpis.first_pass_yield(r.good_count, r.total_count)),
        "loss_minutes": {k: round(v, 1) for k, v in losses.items()},
        "biggest_loss": biggest.replace("_loss_min", ""),
        "unplanned_downtime_cost_eur_assumed": round(kpis.downtime_cost_eur(r.unplanned_downtime_min, value_per_h)),
        "all_downtime_cost_eur_assumed": round(
            kpis.downtime_cost_eur(r.unplanned_downtime_min + r.changeover_min, value_per_h)),
        "production_value_eur_per_hour_assumed": value_per_h,
        "warnings": ["Performance above 100 %: check ideal cycle time."] if p and p > 1 else [],
    }


@_plain
def kpi_trend(line: str, start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
    """OEE per shift for one line, oldest first, plus the window average."""
    line = _check_line(line)
    log = data.in_window(data.for_line(data.production_log(), line), start_date, end_date)
    log = log.assign(_o=log["shift"].map(data.SHIFT_ORDER)).sort_values(["shift_date", "_o"])
    rows = [
        {k: shift_kpis(line, r.shift_date, r.shift)[k]
         for k in ("shift_date", "shift", "oee_pct", "availability_pct", "performance_pct", "quality_pct")}
        | {"unplanned_downtime_min": int(r.unplanned_downtime_min)}
        for r in log.itertuples()
    ]
    window = _window_oee(log)
    return {"line": line, "shifts": rows, "window_oee_pct": window,
            "oee_target_pct": _pct(data.config()["oee_target"])}


def _window_oee(log) -> float | None:
    """OEE over many shifts: computed from summed minutes and counts, not by averaging percentages."""
    if log.empty:
        return None
    ppt = log.planned_production_min.sum()
    run = log.run_time_min.sum()
    ideal_run_min = (log.ideal_cycle_time_s * log.total_count).sum() / 60
    good_ideal_min = (log.ideal_cycle_time_s * log.good_count).sum() / 60
    a = run / ppt
    p = ideal_run_min / run
    q = good_ideal_min / ideal_run_min
    return _pct(a * p * q)


# --------------------------------------------------------------------------- maintenance

@_plain
def mtbf_mttr(line: str = "all", start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
    log = data.in_window(data.for_line(data.production_log(), line), start_date, end_date)
    ev = data.in_window(data.for_line(data.downtime_events(), line), start_date, end_date)
    failures = ev[ev["category"] == "unplanned_failure"]
    wo = data.work_orders()
    repairs = wo[wo["wo_id"].isin(failures["work_order_id"])]["repair_min"].tolist()
    run = float(log["run_time_min"].sum())
    m_bf = kpis.mtbf(run, len(failures))
    m_ttr = kpis.mttr(repairs)
    return {
        "line": line.upper(), "start_date": start_date or log["shift_date"].min(),
        "end_date": end_date or log["shift_date"].max(),
        "run_time_min": int(run),
        "failures": int(len(failures)),
        "mtbf_min": None if m_bf is None else round(m_bf, 1),
        "mtbf_hours": None if m_bf is None else round(m_bf / 60, 1),
        "repairs_counted": len(repairs),
        "total_repair_min": int(sum(repairs)),
        "mttr_min": None if m_ttr is None else round(m_ttr, 1),
        "unplanned_downtime_min": int(failures["duration_min"].sum()),
        "note": "MTTR uses repair time from work orders. Stop time is longer because it includes waiting.",
    }


@_plain
def maintenance_mix(line: str = "all", start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
    """Planned (preventive) vs unplanned (corrective) work orders active in the window."""
    wo = data.for_line(data.work_orders(), line)
    opened = wo["opened_at"].str[:10]
    closed = wo["closed_at"].str[:10]
    if end_date:
        wo = wo[opened <= end_date]
        closed = closed[wo.index]
    if start_date:
        wo = wo[(closed >= start_date) | (wo["status"] == "open")]
    planned = int((wo["type"] == "preventive").sum())
    total = int(len(wo))
    share = kpis.planned_maintenance_share(planned, total)
    threshold = data.config()["planned_maintenance_good_threshold"]
    overdue = wo[(wo["status"] == "open") & (wo["due_date"] != "") &
                 (wo["due_date"] < (end_date or available_shifts()["last_shift_date"]))]
    return {
        "line": line.upper(), "planned_work_orders": planned,
        "unplanned_work_orders": int((wo["type"] == "corrective").sum()),
        "all_work_orders": total,
        "planned_share_pct": _pct(share),
        "healthy_threshold_pct": _pct(threshold),
        "assessment": None if share is None else ("ahead of problems" if share >= threshold else "reactive (firefighting)"),
        "overdue_preventive": overdue[["wo_id", "line", "machine", "due_date", "description"]].to_dict("records"),
    }


@_plain
def downtime_events(line: str = "all", start_date: str | None = None, end_date: str | None = None,
                    shift: str | None = None) -> dict[str, Any]:
    ev = data.in_window(data.for_line(data.downtime_events(), line), start_date, end_date)
    if shift:
        ev = ev[ev["shift"] == _check_shift(shift)]
    by_mode = (ev[ev["category"] == "unplanned_failure"].groupby("failure_mode")["duration_min"]
               .agg(["count", "sum"]).sort_values("sum", ascending=False))
    by_cat = ev.groupby("category")["duration_min"].sum()
    by_machine = (ev[ev["category"] == "unplanned_failure"].groupby("machine")["duration_min"].sum()
                  .sort_values(ascending=False))
    return {
        "events": ev.to_dict("records"),
        "minutes_by_category": {k: int(v) for k, v in by_cat.items()},
        "unplanned_by_failure_mode": {m: {"stops": int(r["count"]), "minutes": int(r["sum"])}
                                      for m, r in by_mode.iterrows()},
        "unplanned_minutes_by_machine": {k: int(v) for k, v in by_machine.items()},
    }


@_plain
def work_orders_list(line: str = "all", machine: str | None = None, status: str | None = None) -> dict[str, Any]:
    wo = data.for_line(data.work_orders(), line)
    if machine:
        wo = wo[wo["machine"] == machine.upper()]
    if status:
        wo = wo[wo["status"] == status.lower()]
    return {"work_orders": wo.to_dict("records")}


@_plain
def notes(line: str = "all", start_date: str | None = None, end_date: str | None = None,
          shift: str | None = None) -> dict[str, Any]:
    n = data.in_window(data.for_line(data.shift_notes(), line), start_date, end_date)
    if shift:
        n = n[n["shift"] == _check_shift(shift)]
    return {"notes": n.to_dict("records"), "source": "synthetic shift notes (data/synthetic/shift_notes.csv)"}


@_plain
def rul(line: str = "all") -> dict[str, Any]:
    r = data.for_line(data.rul_predictions(), line).sort_values("predicted_rul_hours")
    return {"predictions": r.to_dict("records"),
            "note": "Model estimate. Placeholder in the shape of the NASA C-MAPSS turbofan RUL output, mapped to plant assets as an analogy."}


# --------------------------------------------------------------------------- AI4I failure modes

FAILURE_MODES = {
    "TWF": "Tool wear failure: tool wear reaches 200-240 min.",
    "HDF": "Heat dissipation failure: air-process temperature gap < 8.6 K and speed < 1380 rpm.",
    "PWF": "Power failure: power (torque x angular speed) < 3500 W or > 9000 W.",
    "OSF": "Overstrain failure: tool wear x torque > 11000 (L), 12000 (M), 13000 (H) min*Nm.",
    "RNF": "Random failure: 0.1 % chance, no clear cause.",
}


@_plain
def failure_rate_by_type() -> dict[str, Any]:
    df, source = data.ai4i()
    n = len(df)
    rates = {m: {"failures": int(df[m].sum()), "rate_pct": round(df[m].sum() / n * 100, 2)} for m in FAILURE_MODES}
    return {"records": n, "source": source,
            "any_failure": {"failures": int(df["Machine failure"].sum()),
                            "rate_pct": round(df["Machine failure"].sum() / n * 100, 2)},
            "by_type": dict(sorted(rates.items(), key=lambda kv: -kv[1]["failures"]))}


@_plain
def failure_mode_profile(mode: str) -> dict[str, Any]:
    """Average sensor values when this failure happened vs when no failure happened."""
    mode = mode.upper()
    if mode not in FAILURE_MODES:
        raise ValueError(f"Unknown failure mode '{mode}'. Use one of {list(FAILURE_MODES)}.")
    df, source = data.ai4i()
    df = df.assign(**{"Temp gap [K]": df["Process temperature [K]"] - df["Air temperature [K]"],
                      "Power [W]": df["Torque [Nm]"] * df["Rotational speed [rpm]"] * 2 * 3.14159 / 60})
    cols = ["Temp gap [K]", "Rotational speed [rpm]", "Torque [Nm]", "Power [W]", "Tool wear [min]"]
    failed = df[df[mode] == 1][cols].mean().round(1).to_dict()
    normal = df[df["Machine failure"] == 0][cols].mean().round(1).to_dict()
    return {"mode": mode, "rule": FAILURE_MODES[mode], "source": source,
            "failures": int(df[mode].sum()),
            "mean_when_failed": failed, "mean_when_no_failure": normal}
