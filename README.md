# Shift Handover Agent

An agent built with the **Claude Agent SDK** that reads a plant's machine data, maintenance
tickets and shift notes, calculates the key KPIs, finds the likely cause of downtime, and writes
two handover reports: a short one for the **plant manager** and a practical one for the
**next shift's operators**.

> Personal learning project. All plant data is **synthetic** (a fictional plant) or **public**
> (AI4I 2020 schema, NASA C-MAPSS model output shape). Cost figures are **assumed**.

## How it works

```mermaid
flowchart LR
    U([Task: "Handover for Line 2, night shift"]) --> M[Plant analyst<br/>main agent]
    M -->|Agent tool| K[kpi-analyst]
    M -->|Agent tool| R[root-cause-analyst]
    M -->|Agent tool| N[knowledge-agent]
    M -->|Agent tool| W[report-writer]
    M -->|draft only| D[(drafts/work_orders)]
    K --> T{{plant MCP tools<br/>OEE, MTBF/MTTR, mix, RUL}}
    R --> T2{{plant MCP tools<br/>events, notes, work orders,<br/>AI4I failure profiles}}
    N --> S[(data/sops/*.md<br/>Read / Grep / Glob)]
    W --> O[(reports/*.md)]
    D --> H([Human approves<br/>scripts/approve_work_order.py])
    G[[Hooks: audit log + path guard]] -.every tool call.- M
```

1. **Plant analyst** (main agent) resolves the shift and plans the work.
2. **kpi-analyst** calls the KPI tools: OEE and its factors, the three losses in minutes, MTBF, MTTR, maintenance mix, RUL.
3. **root-cause-analyst** links the losses to downtime events, shift notes, work orders and AI4I failure modes.
4. **knowledge-agent** finds the SOP steps and cites them (e.g. `[SOP-HDF-01 §3.5]`).
5. **report-writer** writes the two reports into `reports/`.
6. If maintenance work is needed, the agent **drafts** a work order. Only a human can approve it.

## Claude Agent SDK features used

| SDK feature | Where | What it does here |
| --- | --- | --- |
| Subagents (`AgentDefinition`) | [handover/agents.py](handover/agents.py) | Four specialists, each with only the tools it needs |
| Custom tools (in-process MCP) | [handover/tools.py](handover/tools.py) | 12 tools: `calculate_shift_kpis`, `calculate_mtbf_mttr`, `draft_work_order`, ... |
| Permissions | [handover/agents.py](handover/agents.py) | `permission_mode="dontAsk"`, explicit `allowed_tools`, `disallowed_tools` for Bash/Edit/web |
| Hooks | [handover/guardrails.py](handover/guardrails.py) | `PreToolUse` blocks paths outside the allowed folders; every call is logged to `logs/audit.jsonl` |
| Skills | [.claude/skills/kpi-glossary/SKILL.md](.claude/skills/kpi-glossary/SKILL.md) | The plant's KPI definitions, loaded by the agents |
| Budget cap | `max_budget_usd` | A run stops if it would cost more than $3 (change with `HANDOVER_MAX_BUDGET_USD`) |
| Structured output | [evals/run_evals.py](evals/run_evals.py) | Eval answers come back as JSON for automatic scoring |

## Guardrails

| Rule | How it is enforced |
| --- | --- |
| Read only `data/`, `config/`, `reports/`, `.claude/skills/` | `PreToolUse` hook denies anything else |
| Write only `.md` files in `reports/` | `PreToolUse` hook (also blocks `reports/../` tricks) |
| No shell, no editing, no web | `disallowed_tools` + `tools` list + hook |
| Unknown tools never prompt, they are refused | `permission_mode="dontAsk"` |
| Work orders are drafts only | `draft_work_order` writes `PENDING_HUMAN_APPROVAL`; approval is a separate human script the agent cannot run |
| Audit trail | Every attempted call, its decision, the subagent that made it, and its result go to `logs/audit.jsonl` |
| Only this project's settings load | `setting_sources=["project"]` |

## KPIs

Defined in the [KPI glossary](.claude/skills/kpi-glossary/SKILL.md) and coded as pure functions in
[handover/kpis.py](handover/kpis.py): availability, performance, quality, OEE, the three OEE losses in
minutes, unplanned downtime, MTBF, MTTR, scrap rate, first pass yield, planned maintenance share,
failure rate by type, RUL, and downtime cost.

One finding from the data: on Line 2's night shift of 2026-11-20 the visible 40-minute overheating stop
is **not** the biggest loss. Running at reduced speed after the restart cost more (88 min performance loss
vs 85 min availability loss). The KPI tools find this; a quick read of the shift notes would miss it.

## Data

| Data | Source | File |
| --- | --- | --- |
| Production log (per line and shift) | Synthetic | `data/synthetic/production_log.csv` |
| Downtime events | Synthetic, hand-written | `data/synthetic/downtime_events.csv` |
| Work orders | Synthetic, hand-written | `data/synthetic/work_orders.csv` |
| Shift notes | Synthetic, hand-written | `data/synthetic/shift_notes.csv` |
| SOPs | Synthetic, hand-written | `data/sops/` |
| Machine sensor data and failure types | AI4I 2020 (public). A synthetic stand-in with the same schema and failure rules is used until you add the real file | `data/raw/ai4i2020.csv` or `data/synthetic/ai4i_sample.csv` |
| Remaining useful life | Placeholder in the shape of a NASA C-MAPSS turbofan model output | `data/synthetic/rul_predictions.csv` |
| Targets and cost per hour | Assumed | `config/plant_assumptions.json` |

See [data/README.md](data/README.md) for details and how to plug in the real AI4I and C-MAPSS data.

## Run it

Requires Python 3.10+ and an Anthropic API key. The Agent SDK ships with its own Claude Code binary.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

Handover for the latest shift on Line 2:

```powershell
python -m handover.main
```

A specific shift, or a single question:

```powershell
python -m handover.main --line L1 --date 2026-11-18 --shift late
python -m handover.main --ask "Which failure type caused the most downtime this week?"
```

Review the drafted work orders (the human step):

```powershell
python scripts/approve_work_order.py
python scripts/approve_work_order.py <draft-file>.json --approve --by "Your Name"
```

Model: `claude-opus-5-5` by default. Set `$env:HANDOVER_MODEL = "claude-sonnet-5-5"` for a cheaper run.

## Tests and evals

```powershell
python -m pytest                 # 43 offline tests, no API calls
python -m evals.run_evals        # 10 known-answer questions through the agent (uses the API)
```

The offline tests check the KPI formulas against hand calculations (including a textbook OEE
example and one shift worked by hand), the internal consistency of the synthetic data, the guardrail
rules, the tool handlers, and that the eval's expected answers still match the data.

The eval asks questions such as *"What was the OEE of Line 2 last night?"* and *"Which failure type
caused the most downtime?"*, scores the answers automatically, and saves results to `evals/results/`.

## Project layout

```
.claude/skills/kpi-glossary/   KPI definitions (Agent Skill)
config/                        Assumed targets and costs
data/                          Synthetic data, SOPs, (optional) raw public data
handover/                      kpis.py, plant.py, tools.py, agents.py, guardrails.py, main.py
scripts/                       Data generator, human approval script
tests/                         Offline tests
evals/                         Known-answer questions and runner
reports/                       Agent output (the only folder it may write to)
drafts/work_orders/            Draft work orders waiting for a human
logs/audit.jsonl               Audit trail of every tool call
```

## Limitations

- One fictional plant, one week of data, three lines. Real plants need MES/CMMS connectors.
- RUL is a placeholder mapped from a turbofan model by analogy, not a model of these machines.
- The root cause is the agent's best explanation from the evidence, with a confidence level, not proof.
