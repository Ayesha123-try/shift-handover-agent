# Data provenance

Everything in `synthetic/` and `sops/` is **made up** for this project. It describes a fictional
plant with three machining lines (L1, L2, L3), five CNC machines and three shifts a day, from
2026-11-14 to 2026-11-20. It is not data from any real company.

## The story in the data

- CNC-21 on Line 2 overheats four times in the week (heat dissipation failure, HDF), each stop longer
  than the last: 25, 30, 35, 40 min.
- The preventive work order to replace its cooling fan filter (WO-1013) has been **overdue** since
  2026-11-12. The spare part is not in stock.
- CNC-22 on Line 2 has tool failures (TWF) because the tool life counter was not reset after tool changes.
- Only 37.5 % of work orders are preventive: the plant is reacting, not planning.

## Files

| File | What it is |
| --- | --- |
| `synthetic/production_log.csv` | One row per line and shift: planned time, run time, ideal cycle time, total/good/scrap/rework counts |
| `synthetic/downtime_events.csv` | Every stop: unplanned failures, changeovers, planned maintenance |
| `synthetic/work_orders.csv` | Corrective and preventive work orders, with repair minutes |
| `synthetic/shift_notes.csv` | What operators, shift leads and technicians wrote |
| `synthetic/rul_predictions.csv` | Placeholder remaining useful life per machine |
| `synthetic/ai4i_sample.csv` | Synthetic stand-in in the AI4I 2020 schema, built with the dataset's documented failure rules |
| `sops/*.md` | Three short standard operating procedures |

Regenerate with `python scripts/generate_synthetic_data.py`. The output is always the same (fixed seed).
If you change the data, `python -m pytest` tells you which eval answers need updating.

## Using the real public data

**AI4I 2020** (UCI Machine Learning Repository, "AI4I 2020 Predictive Maintenance Dataset",
CC BY 4.0): download `ai4i2020.csv` and put it at `data/raw/ai4i2020.csv`. The tools pick it up
automatically and say so in their output. You can also export it from your dbt gold layer with the
same column names.

**NASA C-MAPSS**: replace `synthetic/rul_predictions.csv` with your turbofan model's predictions,
keeping the columns `machine, line, predicted_rul_hours, model_confidence, as_of, source`.
