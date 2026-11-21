# SOP-HDF-01: Spindle overheating (heat dissipation failure)

> Synthetic SOP written for this demo project. Not from any real plant or machine maker.

- **Applies to:** CNC milling machines CNC-11, CNC-12, CNC-21, CNC-22, CNC-31
- **Failure mode:** HDF (heat dissipation failure)
- **Owner:** Maintenance
- **Revision:** 2 (2026-10-01)

## 1. Why it happens

1.1 The spindle cannot get rid of heat fast enough. This happens when the gap
between process temperature and air temperature is small (below about 8.6 K)
**and** the spindle runs slowly (below about 1380 rpm). Slow speed means less
air flow from the spindle fan.

1.2 The most common physical cause is a **clogged cooling fan filter**. Dust
and oil mist block the air flow.

1.3 Long runs of product type H at low rpm make it worse.

## 2. Warning signs (what operators should watch)

2.1 Spindle temperature on the HMI rising more than 5 °C above its normal value for this product.

2.2 Fan sounds louder or different than usual.

2.3 Visible dust on the fan grille or filter.

2.4 Two or more over-temperature alarms on the same machine in one week: tell the shift lead.

## 3. What to do when the over-temperature alarm comes on

3.1 **Stop the cycle safely** at the end of the current part. Do not open the door while the spindle turns.

3.2 Let the spindle cool with the fan running. Do not switch the machine off; the fan must keep running.

3.3 Call maintenance. Note the time of the alarm, the product and the spindle rpm in the shift notes.

3.4 Maintenance checks the fan grille and filter. If the filter is dirty, clean it with compressed air (from outside to inside) as a **temporary** fix only.

3.5 Restart only when the spindle temperature is back to normal. Run the first 5 parts at **85 % feed override** and check their dimensions.

3.6 Return to 100 % feed when temperature stays stable for 30 minutes.

## 4. Permanent fix

4.1 Replace the cooling fan filter. Interval: every 3 months, or sooner if alarms repeat.

4.2 If a filter replacement work order is overdue, the shift lead escalates to the maintenance planner the same day.

4.3 Keep at least one spare filter per machine in stock.

## 5. Do not

5.1 Do not bypass or reset the temperature alarm without cooling.

5.2 Do not raise the spindle speed above the program value to "cool" the machine. This changes part quality.
