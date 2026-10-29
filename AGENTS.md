# Development rules

Use `uv run` for Python commands. Use pytest for tests.
Keep the complete plugin self-contained. Use the root Python project and its committed `uv.lock` for all executable skills.
Use Typer for command-line arguments. Keep generated models outside the skill folders.
Keep the original inputs unchanged during inspection and validation.
Do not require private projects, installed CAD applications, or account credentials for the default test suites.
Mark tests that require a browser or an optional external application.
Run `uv run --locked python manage.py test` before a release.
Run the browser tests before a release after installing Chromium.
Keep package versions equal. Start the version in this repository at `1.0.0`.
Do not publish a release if a required check fails.
