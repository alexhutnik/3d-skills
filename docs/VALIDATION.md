# Validation scope

The automated suites use pytest. They do not require a model provider or an agent account.

| Suite | Checks |
| --- | --- |
| Package | Links, conflicts, rollback, removal, versions, references, complete reproducible ZIP. |
| Inspection | STEP transforms, source hashes, invalid scenes, HTML escaping, output safety. |
| Browser | Offline rendering, fresh reopening, visibility, rotation, separation, playback, recording. |
| Print | Valid exports, open surfaces, reversed faces, extra bodies, translation, wrong dimensions, invalid input. |

Local validation uses macOS on Apple silicon and Python 3.13.
GitHub checks target Linux and macOS. Windows has not been validated for this release.

Python tests verify repeatable tool behavior. They do not prove that every agent chooses the correct design.
Physical fit, strength, heat resistance, and printer behavior still require project checks and physical samples.
Browser tests use software rendering. A user's graphics driver can produce different results.

## Manual release review

Generate the synthetic example described in the README. Open the HTML in a browser.
Check the assembled view, exploded view, part visibility, and labels.
Validate the Claude manifests with the installed CLI.
Check plugin discovery in the target Codex or Claude client before relying on that client for a new workflow.
Installing a plugin does not prove that a chat session can run local Python or native CAD applications.

## Local results for 1.0.0

The local suites include two browser tests.
The extracted release passed its tests with newly created Python environments.
Codex CLI discovered the marketplace entry as version 1.0.0. The temporary registration was removed after the check.
Both Claude manifests passed strict validation with the installed Claude CLI.
The synthetic example produced an HTML review and a two-second MP4. The rendered model was inspected.
Desktop installation through the graphical interface has not been tested in this session.
