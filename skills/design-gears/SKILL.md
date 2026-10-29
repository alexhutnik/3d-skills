---
name: design-gears
description: Design and inspect gear pairs or gear trains. Check tooth geometry, centers, backlash units, phase, and sampled motion.
---

# Design gears

Read `../design-assemblies/SKILL.md` for moving assemblies.
Record tooth counts, gear type, ratio, module, pressure angle, thickness, bore, and intended load.
Module is the pitch diameter divided by tooth count, in millimeters for a metric gear.
Backlash is the gap between mating tooth flanks. Record how the selected library defines it.

Prefer a maintained gear library over a new tooth generator.
Check the installed API before using bd_warehouse or py_gearworks.
Older examples call py_gearworks `gggears`. Some backlash parameters are fractions of module, not millimeters.
See [the library source](https://github.com/GarryBGoode/py_gearworks).
Do not replace involute teeth with decorative triangles for a functional drive.

For standard external spur gears without profile shift, center distance is `module * (teeth_a + teeth_b) / 2`.
Profile shift, internal gears, and other gear types need their own geometry rules.
For external gears, driven angle changes by `-driver_angle * teeth_a / teeth_b`.
Choose the initial phase so that a tooth faces a space.
Model hub, bore, shaft fit, and retention separately from tooth geometry.

Check solid validity and tooth dimensions before adding cosmetic rounds.
Sample a complete repeating tooth cycle. Include the full intended motion for nonrepeating geometry.
Check interference, face overlap, shaft clearance, and clearance from the housing.
A positive gap everywhere can also mean the teeth do not engage. Check intended contact separately.
A volume collision check does not prove contact ratio, load capacity, wear, or noise.

Use the browser to show coupled rotation. Keep the numeric checks separate from the animation.
Print a small pair before committing to the complete mechanism.
