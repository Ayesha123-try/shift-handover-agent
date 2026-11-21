# SOP-DRV-03: Spindle overload and power faults

> Synthetic SOP written for this demo project. Not from any real plant or machine maker.

- **Applies to:** All CNC machines
- **Failure modes:** OSF (overstrain failure), PWF (power failure)
- **Owner:** Maintenance (electrical) and production
- **Revision:** 1 (2026-08-20)

## 1. Overstrain (OSF)

1.1 **Why:** the tool is pushed too hard. The load grows with tool wear times
torque. Limits in our data: 11,000 min·Nm for product L, 12,000 for M, 13,000 for H.
A worn tool on a heavy cut is the classic cause.

1.2 **What to do:**
- 1.2.1 Stop the cycle. Do not restart the same cut at once.
- 1.2.2 Check tool wear (see SOP-TWF-02). Change the tool if it is near its life limit.
- 1.2.3 If it happens again with a new tool, reduce depth of cut and tell the process engineer.

## 2. Power faults (PWF)

2.1 **Why:** the spindle needs power outside the safe band (below 3500 W or
above 9000 W), or the drive loses power because of a loose connection.

2.2 **What to do:**
- 2.2.1 Stop the machine and call an electrician. Operators do not open the electrical cabinet.
- 2.2.2 The electrician reads the drive fault code, checks motor cable connectors and resets the drive.
- 2.2.3 After the restart, watch the spindle load for the first 30 minutes.

## 3. Record

3.1 Write the fault code, time and duration in the shift notes and the work order.
