---
name: design-enclosures
description: Design printed enclosures, covers, panel mounts, and fit coupons around actual components and mounting openings.
---

# Design enclosures

Read `../design-3d/SKILL.md` for project and tool selection.

Start with the mounting opening and the actual purchased components.
Keep the manufacturer file unchanged. Record its source, units, and measured features.
Use separate solids for reference components. Exclude them from printable exports.

Choose a fixed reference surface for each fit. Measure the interface from that surface.
For a flush flange, include its thickness and the compressed adhesive thickness in the recess depth.
Inspect the entire rear profile. A collar can be wider than the nominal barrel.
Give the flange a flat seating surface. Check the actual flat contact area after edge rounds and reliefs.
Check wall thickness beside each opening and between adjacent openings.

Use simple walls and ribs where they serve a load or retain a component.
Keep cutouts clear of cable bends, connector insertion paths, and assembly tools.
Check the assembled position and sampled insertion positions with the actual reference geometry.
State when cable geometry ends before the actual cable bend.
A sampled check can miss contact between samples. Use smaller intervals near narrow gaps.

Make a small coupon that preserves the actual recess, seating surface, local wall, and print orientation.
Expose the fit allowance and adhesive allowance separately.
Do not infer a friction fit from nominal opening dimensions alone.

Measure the rear collar and provide clearance behind the bonding shelf.
Keep project measurements with the project. Do not reuse dimensions without checking the actual component.

Use `../inspect-3d/SKILL.md` to review the assembled components and the seating surface.
Use `../release-3d-print/SKILL.md` for printable exports and orientation review.
