# SOP-TWF-02: Tool wear and tool change

> Synthetic SOP written for this demo project. Not from any real plant or machine maker.

- **Applies to:** All CNC machines
- **Failure mode:** TWF (tool wear failure)
- **Owner:** Production (operators), supported by tooling
- **Revision:** 3 (2026-09-15)

## 1. Why it happens

1.1 Every cutting tool has a planned life in minutes of cutting. In our data,
tools fail between **200 and 240 minutes** of wear.

1.2 A worn tool cuts badly: burrs, poor surface, size out of tolerance. In the
end it chips or breaks.

1.3 The most common reason a tool runs past its life is that the **tool life
counter was not reset** at the last tool change, so the machine does not warn.

## 2. Warning signs

2.1 Tool life counter above 180 minutes.

2.2 Burrs on the part edges, or a change in cutting sound.

2.3 Spindle load (torque) rising for the same operation.

## 3. Planned tool change

3.1 Change the tool when the counter reaches **190 minutes**, at the end of a part.

3.2 Measure the new tool on the presetter. Enter the offset.

3.3 **Reset the tool life counter to 0.** Initial the tool change log. This step is mandatory.

3.4 Run one first-off part and check it before restarting the series.

## 4. After a tool breaks

4.1 Stop the machine. Check the part and the fixture for damage.

4.2 Quarantine all parts made since the last good check. Inspect them for burrs. Scrap parts that fail.

4.3 Change the tool as in section 3 (including the counter reset in 3.3).

4.4 Write in the shift notes: tool number, counter value at failure, number of parts scrapped.

## 5. Escalation

5.1 Two broken tools on one machine in a week: tooling checks the tool life setting and the counter reset process.
