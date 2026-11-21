"""The main "plant analyst" agent and its four specialist subagents."""

from __future__ import annotations

import os

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions

from . import data, guardrails, tools

MODEL = os.environ.get("HANDOVER_MODEL", "claude-opus-5-5")
MAX_BUDGET_USD = float(os.environ.get("HANDOVER_MAX_BUDGET_USD", "3.0"))

T = {t.name: tools.mcp_name(t) for t in tools.ALL_TOOLS}

COMMON_RULES = """
Ground rules (all agents):
- The data is a fictional demo plant: synthetic production log, notes, work orders and SOPs, plus AI4I-schema machine data. Never present it as a real company's data.
- Use only numbers that come from a tool result or a file you read. Never invent a number. If something is missing, say so.
- Label every cost figure "assumed".
- Use the definitions in the kpi-glossary skill.
"""

KPI_AGENT = AgentDefinition(
    description="Calculates production and maintenance KPIs (OEE and its factors, losses, MTBF, MTTR, "
                "maintenance mix, downtime cost, RUL) for a line and shift. Use for any number.",
    prompt=f"""You are the KPI analyst for a machining plant.
Given a line, a shift date and a shift:
1. Call calculate_shift_kpis for that shift.
2. Call get_kpi_trend for the line over the available week, to say whether this shift is better or worse than usual.
3. Call calculate_mtbf_mttr and get_maintenance_mix for the line over the week.
4. Call get_rul_predictions for the line.
Return a compact summary: OEE vs target (gap in pp), the three factors, the loss minutes and the biggest loss,
scrap rate, unplanned downtime and its assumed cost, MTBF/MTTR, planned maintenance share, overdue preventive
work orders, the lowest RUL, and how this shift compares with the week. Show the inputs behind OEE.
{COMMON_RULES}""",
    tools=[T["list_available_shifts"], T["calculate_shift_kpis"], T["get_kpi_trend"],
           T["calculate_mtbf_mttr"], T["get_maintenance_mix"], T["get_rul_predictions"]],
    skills=["kpi-glossary"],
    model="inherit",
)

ROOT_CAUSE_AGENT = AgentDefinition(
    description="Links KPI drops to downtime events, shift notes, work orders and AI4I failure modes to find "
                "the likely root cause. Use after the KPIs are known.",
    prompt=f"""You are a maintenance and reliability engineer.
Given a line, shift, and the KPI summary:
1. Get the downtime events for that shift AND for the whole week on the line (repeat failures matter).
2. Read the shift notes for the same scope, and the related work orders (including open ones).
3. For each failure mode involved, call get_failure_mode_profile to explain the physics, and compare with the notes
   (e.g. rpm, product type, temperature).
Return, ranked by lost minutes: each cause, the evidence (event ids, note ids, work order ids), whether it is
recurring, and the most likely root cause behind it (not just the symptom). Say how confident you are and why.
{COMMON_RULES}""",
    tools=[T["get_downtime_events"], T["get_shift_notes"], T["get_work_orders"], T["get_failure_mode_profile"],
           T["get_failure_rate_by_type"], T["get_kpi_trend"]],
    model="inherit",
)

KNOWLEDGE_AGENT = AgentDefinition(
    description="Finds the right SOP sections for a failure mode or situation and returns the steps with exact "
                "citations (SOP id and section number).",
    prompt=f"""You are the plant's document specialist. The SOPs are Markdown files in data/sops/.
1. Use Glob with path "data/sops" to list them, and Grep with path "data/sops" to find relevant sections.
2. Read the relevant SOP files.
3. Return the steps that apply, quoted briefly, each with a citation like [SOP-HDF-01 §3.5].
Only cite sections that exist. If no SOP covers something, say so clearly.
{COMMON_RULES}""",
    tools=["Read", "Glob", "Grep"],
    model="inherit",
)

REPORT_AGENT = AgentDefinition(
    description="Writes the two handover reports (plant manager and operators) as Markdown files in reports/.",
    prompt=f"""You write shift handover reports. You get the KPI summary, the root cause analysis and the SOP steps.
Write TWO Markdown files with the Write tool, using the exact file paths you are given (inside reports/).

1. Plant manager report (one page, plain business language):
   - Headline: OEE vs target, gap in pp.
   - The biggest loss (in minutes) and its estimated cost (assumed).
   - Root cause in one or two sentences, with evidence ids.
   - Trend: is this getting worse this week?
   - ONE decision needed from the manager, with the trade-off.
   - A small KPI table (OEE, A, P, Q, scrap, unplanned downtime, MTBF, MTTR, planned maintenance %).

2. Operator report (practical, short sentences, for the next shift):
   - What happened last shift (times, machines, minutes).
   - What to watch this shift (concrete signs and thresholds).
   - Which SOP steps to follow, with citations like [SOP-HDF-01 §3.5].
   - Open work orders that affect them.

Both reports: a header line with line, shift and date, and a footer saying the data is synthetic/public demo
data and that cost values are assumed. Keep numbers exactly as given; do not recalculate.
{COMMON_RULES}""",
    tools=["Write"],
    skills=["kpi-glossary"],
    model="inherit",
)

AGENTS = {
    "kpi-analyst": KPI_AGENT,
    "root-cause-analyst": ROOT_CAUSE_AGENT,
    "knowledge-agent": KNOWLEDGE_AGENT,
    "report-writer": REPORT_AGENT,
}

MAIN_PROMPT = f"""You are the plant analyst agent. You prepare shift handovers for a machining plant
by coordinating four specialist subagents with the Agent tool:
- kpi-analyst: all numbers.
- root-cause-analyst: why the numbers dropped.
- knowledge-agent: which SOP steps apply, with citations.
- report-writer: writes the two reports.

How to work:
1. Call list_available_shifts to resolve the line, date and shift (e.g. "last night" = the latest night shift).
2. Ask kpi-analyst for the KPIs.
3. Give the KPI summary to root-cause-analyst.
4. Give the failure modes and situations found to knowledge-agent.
5. Give everything to report-writer, with the two exact output paths.
6. If the root cause needs maintenance work that is not already covered by an open work order, OR an open
   preventive work order is overdue and keeps causing failures, call draft_work_order once. It only creates
   a draft. Never say a work order was submitted or approved.
7. Finish with a short summary: OEE vs target, biggest loss, root cause, decision needed, report paths, and any
   draft work order path (saying it needs human approval).

Each subagent starts with no memory of this conversation: pass it every fact it needs in your request.
You can read data and write only reports; any other action will be blocked.
{COMMON_RULES}"""

QA_PROMPT = f"""You are the plant analyst agent. Answer the user's question about the plant using the plant
tools (and the SOPs in data/sops/ if needed). Call list_available_shifts first to resolve dates.
Do not write any files. Give a short, direct answer with the key number and its unit.
{COMMON_RULES}"""


def build_options(mode: str = "handover", output_format: dict | None = None) -> ClaudeAgentOptions:
    """Options shared by the handover run and the eval (QA) run."""
    plant_tools = list(T.values())
    builtin = ["Read", "Glob", "Grep", "Skill"]
    if mode == "handover":
        builtin += ["Write", "Agent"]
    else:  # answering questions must never create work orders
        plant_tools.remove(T["draft_work_order"])
    return ClaudeAgentOptions(
        model=MODEL,
        system_prompt=MAIN_PROMPT if mode == "handover" else QA_PROMPT,
        cwd=str(data.ROOT),
        # Only load this project's settings and skills, not the user's global ones.
        setting_sources=["project"],
        skills=["kpi-glossary"],
        mcp_servers={tools.SERVER_NAME: tools.build_server()},
        agents=AGENTS if mode == "handover" else None,
        # The built-in tools the agent can see at all ...
        tools=builtin,
        # ... the ones that run without asking ...
        allowed_tools=builtin + plant_tools,
        # ... and anything else is refused, never prompted.
        disallowed_tools=["Bash", "Edit", "NotebookEdit", "WebFetch", "WebSearch"],
        permission_mode="dontAsk",
        hooks=guardrails.hooks(),
        max_turns=40,
        max_budget_usd=MAX_BUDGET_USD,
        output_format=output_format,
    )
