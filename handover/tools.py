"""Custom tools, served to the agent as an in-process MCP server named "plant".

The agent sees each tool as mcp__plant__<name>. All tools are read-only except
draft_work_order, which can only create a DRAFT in drafts/work_orders/. It can
never approve or submit one; a human does that with scripts/approve_work_order.py.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from claude_agent_sdk import ToolAnnotations, create_sdk_mcp_server, tool

from . import data, plant

SERVER_NAME = "plant"

READ_ONLY = ToolAnnotations(readOnlyHint=True)


def _schema(props: dict[str, dict], required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": props, "required": required or [],
            "additionalProperties": False}


LINE = {"type": "string", "description": "Line id: L1, L2 or L3 (or 'all' where allowed)."}
DATE = {"type": "string", "description": "ISO date YYYY-MM-DD. A night shift belongs to the date it starts on."}
SHIFT = {"type": "string", "enum": ["early", "late", "night"]}


def _wrap(fn: Callable[..., dict[str, Any]]) -> Callable[[dict], Awaitable[dict]]:
    """Turn a plant.* function into a tool handler that returns JSON text, or an error."""
    async def handler(args: dict) -> dict:
        try:
            result = fn(**args)
        except (ValueError, KeyError) as e:
            return {"content": [{"type": "text", "text": f"Error: {e}"}], "is_error": True}
        return {"content": [{"type": "text", "text": json.dumps(result, default=str, indent=1)}]}
    return handler


list_available_shifts = tool(
    "list_available_shifts",
    "List lines and the date range of available shifts, including the latest finished shift. "
    "Call this first to resolve words like 'last night' or 'this week'.",
    _schema({}), annotations=READ_ONLY,
)(_wrap(plant.available_shifts))

calculate_shift_kpis = tool(
    "calculate_shift_kpis",
    "Calculate OEE, availability, performance, quality, scrap rate, first pass yield, the three OEE "
    "losses in minutes, the biggest loss, and the assumed downtime cost for ONE line and ONE shift.",
    _schema({"line": LINE, "shift_date": DATE, "shift": SHIFT}, ["line", "shift_date", "shift"]),
    annotations=READ_ONLY,
)(_wrap(plant.shift_kpis))

get_kpi_trend = tool(
    "get_kpi_trend",
    "OEE and its factors for every shift of one line in a date window (oldest first), plus the "
    "window OEE computed from summed minutes. Use it to see if a line is getting worse.",
    _schema({"line": LINE, "start_date": DATE, "end_date": DATE}, ["line"]), annotations=READ_ONLY,
)(_wrap(plant.kpi_trend))

calculate_mtbf_mttr = tool(
    "calculate_mtbf_mttr",
    "MTBF (run time / failures) and MTTR (repair minutes from work orders / repairs) for a line or "
    "'all' over a date window. Omit dates for the whole data set.",
    _schema({"line": LINE, "start_date": DATE, "end_date": DATE}), annotations=READ_ONLY,
)(_wrap(plant.mtbf_mttr))

get_maintenance_mix = tool(
    "get_maintenance_mix",
    "Planned (preventive) vs unplanned (corrective) work orders, the planned share, and overdue "
    "preventive work orders, for a line or 'all'.",
    _schema({"line": LINE, "start_date": DATE, "end_date": DATE}), annotations=READ_ONLY,
)(_wrap(plant.maintenance_mix))

get_downtime_events = tool(
    "get_downtime_events",
    "Downtime events (unplanned failures, changeovers, planned maintenance) with failure mode and "
    "linked work order, plus minutes by category, by failure mode and by machine.",
    _schema({"line": LINE, "start_date": DATE, "end_date": DATE, "shift": SHIFT}), annotations=READ_ONLY,
)(_wrap(plant.downtime_events))

get_work_orders = tool(
    "get_work_orders",
    "Maintenance work orders, filtered by line, machine (e.g. CNC-21) and status (open/closed).",
    _schema({"line": LINE, "machine": {"type": "string"},
             "status": {"type": "string", "enum": ["open", "closed"]}}), annotations=READ_ONLY,
)(_wrap(plant.work_orders_list))

get_shift_notes = tool(
    "get_shift_notes",
    "Free-text shift notes written by operators, shift leads and maintenance technicians.",
    _schema({"line": LINE, "start_date": DATE, "end_date": DATE, "shift": SHIFT}), annotations=READ_ONLY,
)(_wrap(plant.notes))

get_failure_rate_by_type = tool(
    "get_failure_rate_by_type",
    "Failure rate per failure type (TWF, HDF, PWF, OSF, RNF) from the AI4I 2020 machine data.",
    _schema({}), annotations=READ_ONLY,
)(_wrap(plant.failure_rate_by_type))

get_failure_mode_profile = tool(
    "get_failure_mode_profile",
    "For one AI4I failure mode: the rule that triggers it, and average sensor values (temperature "
    "gap, rpm, torque, power, tool wear) when it failed vs when nothing failed. Use it to explain "
    "the physics of a failure and what operators should watch.",
    _schema({"mode": {"type": "string", "enum": list(plant.FAILURE_MODES)}}, ["mode"]), annotations=READ_ONLY,
)(_wrap(plant.failure_mode_profile))

get_rul_predictions = tool(
    "get_rul_predictions",
    "Predicted remaining useful life (hours) per machine, lowest first. Model estimate.",
    _schema({"line": LINE}), annotations=READ_ONLY,
)(_wrap(plant.rul))


@tool(
    "draft_work_order",
    "Create a DRAFT maintenance work order for a human to review. It is NOT submitted. "
    "A person must approve it with scripts/approve_work_order.py.",
    _schema({
        "line": LINE,
        "machine": {"type": "string", "description": "e.g. CNC-21"},
        "failure_mode": {"type": "string", "enum": list(plant.FAILURE_MODES) + ["NONE"]},
        "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
        "title": {"type": "string"},
        "justification": {"type": "string", "description": "Evidence: KPIs, events, notes, work order ids."},
        "sop_reference": {"type": "string", "description": "e.g. SOP-HDF-01 section 4.1"},
    }, ["line", "machine", "failure_mode", "priority", "title", "justification"]),
)
async def draft_work_order(args: dict) -> dict:
    line, machine = args["line"].upper(), args["machine"].upper()
    if line not in data.config()["lines"] or machine not in data.config()["lines"][line]["machines"]:
        return {"content": [{"type": "text", "text": f"Error: {machine} is not a machine on {line}."}],
                "is_error": True}
    data.DRAFTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = re.sub(r"[^a-z0-9]+", "-", args["title"].lower()).strip("-")[:40]
    path = data.DRAFTS / f"DRAFT-{stamp}-{machine}-{slug}.json"
    record = {
        "status": "PENDING_HUMAN_APPROVAL",
        "created_at_utc": stamp,
        "created_by": "shift-handover-agent",
        **{k: args.get(k) for k in ("line", "machine", "failure_mode", "priority", "title",
                                     "justification", "sop_reference")},
        "line": line, "machine": machine,
    }
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    shown = path.relative_to(data.ROOT) if path.is_relative_to(data.ROOT) else path
    return {"content": [{"type": "text", "text":
            f"Draft saved to {shown.as_posix()}. Status: PENDING_HUMAN_APPROVAL. "
            "It has not been submitted. Tell the user a person must approve it."}]}


ALL_TOOLS = [
    list_available_shifts, calculate_shift_kpis, get_kpi_trend, calculate_mtbf_mttr, get_maintenance_mix,
    get_downtime_events, get_work_orders, get_shift_notes, get_failure_rate_by_type,
    get_failure_mode_profile, get_rul_predictions, draft_work_order,
]


def mcp_name(t) -> str:
    return f"mcp__{SERVER_NAME}__{t.name}"


def build_server():
    return create_sdk_mcp_server(name=SERVER_NAME, version="1.0.0", tools=ALL_TOOLS)
