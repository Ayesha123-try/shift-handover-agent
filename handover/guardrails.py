"""Safety layer: an audit trail of every tool call, and a hook that blocks
anything outside the allowed folders.

Rules
-----
- Read / Glob / Grep: only inside data/, config/, reports/ and .claude/skills/.
- Write: only Markdown files inside reports/.
- Plant tools (mcp__plant__*): allowed. They are read-only, except
  draft_work_order, which can only create a draft for a human to approve.
- Everything else (Bash, Edit, web access, ...): denied.

The hooks run for the main agent and for every subagent. In the audit log a
subagent's calls carry its agent_type, so you can see who did what.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from claude_agent_sdk import HookContext, HookMatcher

from . import data

READ_ROOTS = [data.DATA, data.ROOT / "config", data.REPORTS, data.ROOT / ".claude" / "skills"]
WRITE_ROOTS = [data.REPORTS]
READ_TOOLS = {"Read", "Glob", "Grep"}
ALWAYS_OK = {"Agent", "Skill"}
PLANT_PREFIX = "mcp__plant__"

AUDIT_LOG = data.LOGS / "audit.jsonl"


# --------------------------------------------------------------------------- path checks

def _resolve(raw: str) -> Path:
    """Resolve a tool path against the project root. Handles /c/Users/... style paths too."""
    m = re.match(r"^/([a-zA-Z])/(.*)$", raw)
    if m:
        raw = f"{m.group(1)}:/{m.group(2)}"
    p = Path(raw)
    if not p.is_absolute():
        p = data.ROOT / p
    return p.resolve()


def _inside(path: Path, roots: list[Path]) -> bool:
    return any(path == r.resolve() or path.is_relative_to(r.resolve()) for r in roots)


def check_tool_call(tool_name: str, tool_input: dict[str, Any]) -> str | None:
    """Return None if the call is allowed, or the reason it is blocked."""
    if tool_name in ALWAYS_OK or tool_name.startswith(PLANT_PREFIX):
        return None

    if tool_name in READ_TOOLS:
        raw = tool_input.get("file_path") or tool_input.get("path")
        if not raw:
            return (f"{tool_name} needs an explicit path inside data/, config/, reports/ or .claude/skills/ "
                    "(for SOPs use path='data/sops').")
        if tool_name == "Glob" and Path(tool_input.get("pattern", "")).is_absolute():
            raw = tool_input["pattern"]
        if not _inside(_resolve(raw), READ_ROOTS):
            return f"Reading '{raw}' is outside the allowed folders (data/, config/, reports/, .claude/skills/)."
        return None

    if tool_name == "Write":
        raw = tool_input.get("file_path", "")
        path = _resolve(raw)
        if not _inside(path, WRITE_ROOTS):
            return f"Writing '{raw}' is blocked. The agent may only write reports inside reports/."
        if path.suffix.lower() != ".md":
            return "Only Markdown (.md) reports may be written."
        return None

    return f"Tool '{tool_name}' is not allowed for this agent (read-only plant analyst)."


# --------------------------------------------------------------------------- audit log

def _audit(record: dict[str, Any]) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {"ts_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), **record}
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


def _short(value: Any, limit: int = 400) -> Any:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text if len(text) <= limit else text[:limit] + f"... [{len(text) - limit} more chars]"


def _who(input_data: dict) -> str:
    return input_data.get("agent_type") or "main"


async def guard_and_log_pre(input_data: dict, tool_use_id: str | None, context: HookContext) -> dict:
    """PreToolUse: block disallowed calls, and log every attempt with the decision."""
    tool_name, tool_input = input_data["tool_name"], input_data.get("tool_input", {})
    reason = check_tool_call(tool_name, tool_input)
    _audit({"event": "PreToolUse", "session_id": input_data.get("session_id"), "agent": _who(input_data),
            "tool": tool_name, "tool_use_id": tool_use_id, "input": _short(tool_input),
            "decision": "deny" if reason else "allow", "reason": reason})
    if reason:
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                       "permissionDecisionReason": reason}}
    return {}


async def log_post(input_data: dict, tool_use_id: str | None, context: HookContext) -> dict:
    """PostToolUse / PostToolUseFailure: log the outcome of each call."""
    _audit({"event": input_data["hook_event_name"], "session_id": input_data.get("session_id"),
            "agent": _who(input_data), "tool": input_data.get("tool_name"), "tool_use_id": tool_use_id,
            "duration_ms": input_data.get("duration_ms"),
            "output": _short(input_data.get("tool_response", input_data.get("error")), 300)})
    return {}


async def log_subagent(input_data: dict, tool_use_id: str | None, context: HookContext) -> dict:
    _audit({"event": input_data["hook_event_name"], "session_id": input_data.get("session_id"),
            "agent": input_data.get("agent_type"), "agent_id": input_data.get("agent_id")})
    return {}


def hooks() -> dict:
    return {
        "PreToolUse": [HookMatcher(matcher=None, hooks=[guard_and_log_pre])],
        "PostToolUse": [HookMatcher(matcher=None, hooks=[log_post])],
        "PostToolUseFailure": [HookMatcher(matcher=None, hooks=[log_post])],
        "SubagentStart": [HookMatcher(matcher=None, hooks=[log_subagent])],
        "SubagentStop": [HookMatcher(matcher=None, hooks=[log_subagent])],
    }
