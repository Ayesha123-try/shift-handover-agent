"""The safety layer: reads only from data folders, writes only reports."""

import asyncio

import pytest

from handover import data, guardrails
from handover.guardrails import check_tool_call

ROOT = data.ROOT


@pytest.mark.parametrize("tool,inp", [
    ("Read", {"file_path": "data/sops/SOP-HDF-01_spindle_overheating.md"}),
    ("Read", {"file_path": str(ROOT / "config" / "plant_assumptions.json")}),
    ("Grep", {"pattern": "overheat", "path": "data/sops"}),
    ("Glob", {"pattern": "*.md", "path": "data/sops"}),
    ("Read", {"file_path": ".claude/skills/kpi-glossary/SKILL.md"}),
    ("Write", {"file_path": "reports/2026-11-20_L2_night_operators.md", "content": "x"}),
    ("mcp__plant__calculate_shift_kpis", {"line": "L2"}),
    ("mcp__plant__draft_work_order", {}),
    ("Agent", {"subagent_type": "kpi-analyst"}),
])
def test_allowed(tool, inp):
    assert check_tool_call(tool, inp) is None


@pytest.mark.parametrize("tool,inp", [
    ("Bash", {"command": "ls"}),
    ("Edit", {"file_path": "reports/a.md"}),
    ("WebFetch", {"url": "https://example.com"}),
    ("Write", {"file_path": "data/synthetic/production_log.csv", "content": "x"}),
    ("Write", {"file_path": "handover/tools.py", "content": "x"}),
    ("Write", {"file_path": "drafts/work_orders/approved/x.md", "content": "x"}),
    ("Write", {"file_path": "reports/../handover/evil.md", "content": "x"}),
    ("Write", {"file_path": "reports/script.py", "content": "x"}),
    ("Read", {"file_path": ".env"}),
    ("Read", {"file_path": "C:/Windows/win.ini"}),
    ("Read", {"file_path": "handover/agents.py"}),
    ("Grep", {"pattern": "API_KEY"}),                   # no path = whole project: blocked
    ("Glob", {"pattern": "C:/Users/**/*.txt", "path": "data"}),
    ("mcp__other__anything", {}),
])
def test_blocked(tool, inp):
    assert check_tool_call(tool, inp) is not None


def test_hook_denies_and_logs(tmp_path, monkeypatch):
    monkeypatch.setattr(guardrails, "AUDIT_LOG", tmp_path / "audit.jsonl")
    out = asyncio.run(guardrails.guard_and_log_pre(
        {"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}, "session_id": "s1",
         "hook_event_name": "PreToolUse"}, "tu1", None))
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    ok = asyncio.run(guardrails.guard_and_log_pre(
        {"tool_name": "mcp__plant__get_shift_notes", "tool_input": {}, "session_id": "s1",
         "agent_type": "root-cause-analyst", "hook_event_name": "PreToolUse"}, "tu2", None))
    assert ok == {}
    lines = (tmp_path / "audit.jsonl").read_text().splitlines()
    assert len(lines) == 2 and '"deny"' in lines[0] and '"root-cause-analyst"' in lines[1]
