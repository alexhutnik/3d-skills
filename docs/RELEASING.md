# Release a version

Use a clean checkout. Never reuse or move a published release tag.

1. Update the version in all four `pyproject.toml` files and all three plugin manifests.
2. Update the Claude marketplace entry and `CHANGELOG.md`.
3. Run `uv lock` for each changed project and commit the resulting lockfiles.
4. Run the checks below.
5. Commit the release files and push the branch.
6. Wait for both GitHub check jobs to pass.
7. Create and push the version tag.
8. Wait for the release workflow to pass and check its attached ZIP and checksum.

```sh
uv run --locked python manage.py setup --dev --browser
uv run --locked python manage.py test --browser
uv run --locked python manage.py verify-tag v1.0.0
uv run --locked python manage.py package
uv run --locked python scripts/test_archive.py dist/3d-skills-v1.0.0.zip
claude plugin validate --strict .claude-plugin/plugin.json
claude plugin validate --strict .claude-plugin/marketplace.json
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

Replace the version for later releases. The workflow runs the tests again before publishing.
It creates a GitHub release with the complete source ZIP and SHA-256 checksum.
The repository's visibility controls access to the release.

Use a patch version for compatible fixes. Use a minor version for compatible additions.
Use a major version when an existing command, file format, or supported environment becomes incompatible.
Do not update dependencies silently within a published release.

The archive is also a plugin package. It retains every skill's scripts, references, and lockfile.
It does not contain Python, virtual environments, browsers, or CAD application binaries.
The archive test creates new environments from the included locks.

Before making the repository public, review the current files and Git history.
The current package includes an MIT license and third-party notices.
Changing visibility does not require a new installation format.
