"""The MCP tool handlers, called the way the agent calls them."""

import asyncio
import json
import subprocess
import sys

from handover import data, tools


def call(t, args):
    return asyncio.run(t.handler(args))


def test_kpi_tool_returns_json():
    out = call(tools.calculate_shift_kpis, {"line": "L2", "shift_date": "2026-11-20", "shift": "night"})
    assert "is_error" not in out
    assert json.loads(out["content"][0]["text"])["oee_pct"] == 56.7


def test_tool_error_is_reported_not_raised():
    out = call(tools.calculate_shift_kpis, {"line": "L7", "shift_date": "2026-11-20", "shift": "night"})
    assert out["is_error"] is True and "Unknown line" in out["content"][0]["text"]


def test_server_builds_with_all_tools():
    server = tools.build_server()
    assert server["name"] == "plant" and len(tools.ALL_TOOLS) == 12


def test_draft_then_human_approval(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "DRAFTS", tmp_path)
    out = call(tools.draft_work_order, {
        "line": "L2", "machine": "CNC-21", "failure_mode": "HDF", "priority": "high",
        "title": "Replace spindle cooling fan filter", "justification": "4 HDF stops, 130 min",
        "sop_reference": "SOP-HDF-01 §4.1"})
    assert "PENDING_HUMAN_APPROVAL" in out["content"][0]["text"]
    draft = next(tmp_path.glob("DRAFT-*.json"))
    assert json.loads(draft.read_text())["status"] == "PENDING_HUMAN_APPROVAL"

    bad = call(tools.draft_work_order, {"line": "L1", "machine": "CNC-21", "failure_mode": "HDF",
                                        "priority": "low", "title": "x", "justification": "x"})
    assert bad["is_error"] is True


def test_approval_script_lists_pending():
    r = subprocess.run([sys.executable, "scripts/approve_work_order.py"], cwd=data.ROOT,
                       capture_output=True, text=True)
    assert r.returncode == 0
