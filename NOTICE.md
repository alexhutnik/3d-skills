# Source and dependency notices

Alex Hutnik's 3D project supplied the original nine skills and Python helpers.
This package removes private project dependencies and adds portable setup and tests.
The original research record states that no upstream skill files were copied.

The included `box.sat` fixture describes a synthetic 20 × 30 × 10 mm box.
OpenCADStudio generated it during a conversion investigation. It contains no purchased component geometry.
The example enclosure parameters are synthetic and do not describe a particular commercial component.

The MIT license covers this repository's original instructions, code, and fixtures.
Dependencies retain their own licenses. The lockfiles identify their exact distributions.
Installing a dependency does not change its license.
The offline viewer embeds K3D assets and retains the available K3D dependency notices in its HTML output.

OpenCADStudio is an optional external application. This repository does not distribute it.
The cq-acis converter is experimental. Its tests cover the included fixture, not every ACIS surface.
