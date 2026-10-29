---
name: design-hinges
description: Design printed hinges, knuckles, hinge pins, clearances, travel stops, and installation paths.
---

# Design hinges

Read `../design-assemblies/SKILL.md` for joint placement and collision checks.
Choose an inserted pin, a captive printed pin, or a flexible hinge from the intended use.
Do not assume a flexible hinge will survive repeated bending in the selected material.

Record the axis, travel range, pin diameter, bore allowance, axial gap, and minimum knuckle wall.
Distinguish the gap along the axis from the clearance around the pin.
For an inserted pin, show a clear insertion path and a method that prevents unwanted pin movement.
For a captive printed hinge, check every trapped gap and its print direction.
Do not add supports that cannot be removed from the joint.

Build each leaf and the pin as separate parts.
Place the axis outside the wall when the wall would block the requested opening angle.
Check alternating knuckles for axial overlap.
Check the leaves, knuckles, housing, and stops through the intended travel.
Include both travel endpoints and small intervals near the closed position.
Report the angular interval. A sampled sweep does not prove continuous clearance.

State which surfaces carry the load. Avoid sharp changes where a knuckle meets its leaf.
Make a short coupon with the actual pin, bore, gaps, and knuckle attachment.
Check free motion after cooling. Adjust the fit parameters from the sample.
If the hinge must carry a specified load, calculate or test that load separately.

Use `../inspect-3d/SKILL.md` to show the axis, pin installation, and closed and open positions.
Use `../release-3d-print/SKILL.md` to review the gaps in sliced layers.
