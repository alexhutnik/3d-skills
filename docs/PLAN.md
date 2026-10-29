# Release plan

Build one source repository for nine CAD skills. Start at version 1.0.0.
Keep the GitHub repository private. Exclude photogrammetry.

1. Extract the skills without private models, measurements, or research dependencies.
2. Keep each executable skill self-contained with Python 3.13 and a locked uv environment.
3. Provide plugin manifests for Codex and Claude. Provide safe symbolic-link installation for development.
4. Document setup, updates, rollback, and removal for CLI and desktop users.
5. Test the Python scripts with pytest and independent synthetic geometry.
6. Check the browser viewer with network access disabled.
7. Check package versions, references, and complete release contents.
8. Test an extracted release archive without the original repository.
9. Run automated checks on GitHub and publish the private v1.0.0 release after they pass.

The current 3D project keeps its existing skills during this work.
Installation into that project remains a separate choice.

## Release checks

- Installation refuses conflicting files and rolls back partial link creation.
- Uninstallation preserves unrelated files.
- Export checks reject invalid meshes and incorrect requirements.
- Conversion preserves the source and rejects incorrect units or volume.
- Inspection preserves source files and produces an offline browser review.
- OCS protocol tests check revision tracking, incomplete operations, and verified saves.
- The package contains all runtime files and tests, with matching versions.
- The release process checks the tag against the package version.
