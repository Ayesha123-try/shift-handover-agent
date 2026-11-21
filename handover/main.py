"""Command line entry point.

Examples:
    python -m handover.main                                  # latest shift, Line 2
    python -m handover.main --line L1 --date 2026-11-18 --shift late
    python -m handover.main --task "Prepare the handover for Line 2, night shift"
    python -m handover.main --ask "What was the OEE of Line 2 last night?"
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeSDKError,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

from . import agents, data, plant


def _label(tool: ToolUseBlock) -> str:
    name = tool.name.replace("mcp__plant__", "plant.")
    if tool.name == "Agent":
        return f"-> subagent {tool.input.get('subagent_type', '?')}: {tool.input.get('description', '')}"
    if tool.name == "Write":
        return f"   write {tool.input.get('file_path')}"
    detail = {k: v for k, v in tool.input.items() if k in ("line", "shift_date", "shift", "mode", "path",
                                                              "file_path", "pattern", "machine")}
    return f"   {name} {detail if detail else ''}"


async def run(prompt: str, mode: str = "handover", output_format: dict | None = None,
              verbose: bool = True) -> ResultMessage | None:
    options = agents.build_options(mode, output_format)
    result: ResultMessage | None = None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage) and verbose:
            who = "  [sub]" if message.parent_tool_use_id else ""
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    print(f"{who}{_label(block)}", flush=True)
                elif isinstance(block, TextBlock) and not message.parent_tool_use_id and block.text.strip():
                    print(f"\n{block.text.strip()}\n", flush=True)
        elif isinstance(message, ResultMessage):
            result = message
    return result


def handover_prompt(line: str, shift_date: str, shift: str) -> str:
    base = f"{shift_date}_{line}_{shift}"
    return (f"Prepare the shift handover for Line {line[-1]} ({line}), {shift} shift of {shift_date}.\n"
            f"Write the plant manager report to reports/{base}_plant_manager.md\n"
            f"and the operator report to reports/{base}_operators.md.")


def main(argv: list[str] | None = None) -> int:
    latest = plant.available_shifts()["latest_shift"]
    ap = argparse.ArgumentParser(description="Shift Handover Agent (Claude Agent SDK)")
    ap.add_argument("--line", default="L2")
    ap.add_argument("--date", default=latest["shift_date"], help="Shift date YYYY-MM-DD")
    ap.add_argument("--shift", default=latest["shift"], choices=["early", "late", "night"])
    ap.add_argument("--task", help="Free-text task instead of --line/--date/--shift")
    ap.add_argument("--ask", help="Ask one question (no reports are written)")
    args = ap.parse_args(argv)

    if args.ask:
        prompt, mode = args.ask, "qa"
    else:
        prompt = args.task or handover_prompt(args.line.upper(), args.date, args.shift)
        if args.task:
            prompt += ("\nName the reports reports/<date>_<line>_<shift>_plant_manager.md and "
                       "reports/<date>_<line>_<shift>_operators.md.")
        mode = "handover"
    data.REPORTS.mkdir(exist_ok=True)

    print(f"Model: {agents.MODEL} | budget cap: ${agents.MAX_BUDGET_USD:.2f} | audit log: logs/audit.jsonl\n")
    try:
        result = asyncio.run(run(prompt, mode))
    except ClaudeSDKError as e:
        print(f"Agent run failed: {e}", file=sys.stderr)
        if "authenticate" in str(e).lower():
            print("Set ANTHROPIC_API_KEY in this terminal, e.g.  $env:ANTHROPIC_API_KEY = \"sk-ant-...\"",
                  file=sys.stderr)
        return 1
    if result is None:
        print("No result returned.", file=sys.stderr)
        return 1
    print("-" * 70)
    if result.result:
        print(result.result)
    cost = f"${result.total_cost_usd:.3f}" if result.total_cost_usd is not None else "n/a"
    print(f"\nturns: {result.num_turns} | cost: {cost} | {result.duration_ms / 1000:.0f}s | status: {result.subtype}")
    return 1 if result.is_error else 0


if __name__ == "__main__":
    sys.exit(main())
