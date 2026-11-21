---
name: kpi-glossary
description: The plant's official KPI definitions (OEE, availability, performance, quality, MTBF, MTTR, scrap, FPY, maintenance mix, downtime cost, RUL). Load before calculating, comparing or explaining any production or maintenance KPI.
---

# KPI glossary: Shift Handover Agent

These are the plant's definitions. Always use them, and always say which
numbers a KPI came from. If a number is an assumption (such as the value of
one production hour), say that it is assumed.

> TODO (Ayesha): rewrite each "In plain words" line in your own words. That
> rewrite is your interview cheat sheet.

## Time model of a shift

```
Shift length (480 min)
 └─ minus planned stops (breaks, planned maintenance)  = Planned production time
     └─ minus unplanned stops and changeovers          = Run time
```

- **Planned stops** do not count against OEE: the plant never planned to run then.
- **Unplanned stops** (breakdowns) and **changeovers** are availability losses.

## OEE and its three factors

| KPI | Formula | In plain words |
| --- | --- | --- |
| Availability | Run time ÷ Planned production time | Of the time we planned to run, how much did we actually run? |
| Performance | (Ideal cycle time × Total count) ÷ Run time | While running, how close were we to the ideal speed? |
| Quality | Good count ÷ Total count | Of everything we made, how much was good the first time? |
| OEE | Availability × Performance × Quality | The share of planned time that made good parts at full speed. |

Rules:
- Use the same unit for time everywhere (seconds for cycle time × count, minutes ÷ 60 if needed).
- Performance above 100 % means the ideal cycle time is wrong. Flag it, don't hide it.
- **Good count** means good on the first pass. Reworked parts are not good count.
- World-class OEE is often quoted as 85 %. This plant's target is in `config/plant_assumptions.json`.

## The six big losses (how to name the biggest loss)

| OEE factor | Loss | Example from shift notes |
| --- | --- | --- |
| Availability | Breakdowns | Spindle overheated, line stopped 40 min |
| Availability | Setup and changeovers | Changeover to product type H |
| Performance | Small stops | Sensor jam cleared in 2 min, many times |
| Performance | Reduced speed | Ran at 80 % speed after a restart |
| Quality | Start-up rejects | Scrap while warming up after a stop |
| Quality | Production rejects | Burrs from a worn tool |

To find **the biggest loss**, convert each factor's loss to minutes of lost
good production:
- Availability loss = Planned production time − Run time
- Performance loss = Run time − (Ideal cycle time × Total count)
- Quality loss = Ideal cycle time × (Total count − Good count)

The largest of the three is the biggest loss.

## Quality detail

| KPI | Formula | Note |
| --- | --- | --- |
| Scrap rate | Scrap count ÷ Total count | Parts thrown away |
| Rework rate | Rework count ÷ Total count | Parts fixed and sold later |
| First pass yield (FPY) | Good first time ÷ Total count | Equals OEE Quality in this plant |

## Maintenance KPIs

| KPI | Formula | In plain words |
| --- | --- | --- |
| Unplanned downtime | Sum of unplanned stop minutes | Time lost to surprises |
| MTBF | Total run time ÷ Number of failures | How long, on average, the line runs before it breaks |
| MTTR | Total repair time ÷ Number of repairs | How long, on average, a fix takes |
| Planned maintenance % | Planned (preventive) work orders ÷ All work orders | Above ~80 % means we are ahead of problems; low means we are firefighting |

Rules:
- Only **unplanned failures** count as failures for MTBF. Changeovers and planned maintenance do not.
- MTTR uses repair time from the **work orders**, not from the stop length (the stop includes waiting for the technician).
- Higher MTBF is better. Lower MTTR is better.

## Failure modes (from the AI4I 2020 dataset)

| Code | Name | What triggers it in AI4I |
| --- | --- | --- |
| TWF | Tool wear failure | Tool wear reaches 200–240 min |
| HDF | Heat dissipation failure | Air–process temperature gap < 8.6 K **and** speed < 1380 rpm |
| PWF | Power failure | Power (torque × angular speed) < 3500 W or > 9000 W |
| OSF | Overstrain failure | Tool wear × torque > 11,000 (L), 12,000 (M), 13,000 (H) min·Nm |
| RNF | Random failure | 0.1 % chance, no clear cause |

Failure rate by type = failures of that type ÷ total records.

## Remaining useful life (RUL)

Predicted cycles (or hours) before an asset is likely to need maintenance. It
comes from the turbofan (NASA C-MAPSS) model and is mapped to plant assets as an
analogy. Always say it is a model estimate, and give the "as of" date.

## Downtime cost

Downtime cost = Unplanned downtime hours × Production value per hour.

The value per hour is an **assumption** from `config/plant_assumptions.json`.
Always write "assumed" next to any cost figure.

## Reporting conventions

- Percentages: one decimal (e.g. 72.4 %). Minutes: whole numbers. Cost: whole euros.
- Always show actual vs target, and the gap in percentage points (pp).
- Biggest loss first, then the cause, then the action.
