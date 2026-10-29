---
name: design-assemblies
description: Arrange separate parts, define moving joints, check installation paths, and inspect motion or interference in assemblies.
---

# Design assemblies and motion

Keep each manufactured part, purchased component, and reference envelope separately named.
Group a purchased assembly as one unit for an exploded view.
A connector with many internal solids must not explode into its individual contacts.

Record each part location from a fixed reference point.
Record each moving joint axis, parent part, child part, rest position, and travel limits.
Use a real constraint solver for closed linkage loops when simple angle relationships do not determine the motion.
Do not substitute a convincing animation for a solved mechanism.

Keep three states separate:

- The assembled state defines fit and exported geometry.
- The inspection state separates or hides parts for review.
- The moving state applies the joint relationships for functional checks.

Keep inspection offsets out of the manufacturing exports.
Use exact solids to check overlap. Touching faces can have zero overlap volume but zero clearance.
Measure minimum separation where a positive clearance is required.
Account for intended contact and clearances by part pair. Do not ignore all collisions because one contact is expected.
Check insertion and removal paths as well as final placement.

For a sampled motion check, report the interval, range, smallest measured gap, and largest unexpected overlap.
Refine the sampling near a small gap or a rapid motion change.
Use continuous checks or a justified geometric bound when a missed contact would matter.
The geometry alone does not prove strength, friction, wear, or a cable bend limit.

Use `../inspect-3d/SKILL.md` for browser inspection and motion presentation.
Keep camera state, named views, and review notes with the model revision when useful.
