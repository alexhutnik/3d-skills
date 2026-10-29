# 3D Skills

Design, inspect, and check mechanical 3D parts with eight reusable skills and tested Python tools.

The first release is **v1.0.0**. This repository is private for now.
You need repository access to clone it or install its private marketplace.
Photogrammetry is outside this release.

## Choose an installation method

| Method | Best use | How changes reach the agent |
| --- | --- | --- |
| Plugin | Normal use and sharing | Install a release, then update the installed plugin. |
| Symbolic links | Local development | Edit the checkout. The links point to those files. |

Both methods use the same skill folders and Python tools.
Use one method per application. Duplicate installations can expose the same skills twice.
A plugin does not install Python dependencies or grant command permissions.

## Requirements

- Install Git and [uv](https://docs.astral.sh/uv/getting-started/installation/).
- Use an agent session that can run local commands and access the project files.
- Allow network access for the first dependency installation.
- Use a browser for visual reviews.

You do not need to install Python separately. `uv` can download the Python version specified by this repository.
The supported Python version is 3.13. Each executable skill has its own locked environment.
CAD dependencies require compatible binary packages for your operating system.
See [validation](docs/VALIDATION.md) for the tested platforms and remaining limits.

On macOS with Homebrew:

```sh
brew install uv git
```

For Linux and Windows, use the linked uv installation instructions.
On Windows, symbolic links can require Developer Mode or administrator rights. Prefer plugin installation if links are unavailable.
The commands below use a POSIX shell. Replace paths and shell syntax when using PowerShell.

For links or direct tool use, clone the release:

```sh
git clone --branch v1.0.0 https://github.com/alexhutnik/3d-skills.git
cd 3d-skills
uv sync --locked --no-dev
uv run --locked --no-dev python manage.py setup
uv run --locked --no-dev python manage.py doctor
```

The clone selects a fixed release. This prevents later commits from changing a working installation.
Use your normal GitHub authentication for private access. Do not put a token in a command or URL.

`setup` prepares both tool environments. To install only the tools you need:

```sh
uv run --locked --no-dev python manage.py setup --profile inspect
uv run --locked --no-dev python manage.py setup --profile print
```

A fixed-frame video export also needs FFmpeg and Playwright Chromium:

```sh
uv run --locked --no-dev python manage.py setup --profile inspect --browser
```

Install FFmpeg through your operating system package manager. HTML reviews do not need FFmpeg.

## Codex CLI

For plugin installation, download the release ZIP and extract it into a new folder.
Keep this folder free of development environments and generated files.
Register the extracted folder as a local marketplace:

```sh
codex plugin marketplace add /absolute/path/to/extracted-3d-skills
codex plugin add 3d-skills@alexhutnik-3d
```

Start a new session. Select `design-3d` from the skills list, or ask for a matching CAD task.
If your CLI does not have `plugin add`, install through the desktop application or use links.

For local development, link the skills to your project:

```sh
uv run --locked --no-dev python manage.py link --destination /absolute/project/.agents/skills
```

Start Codex in that project. Use `$design-3d` to select the linked skill.
Use `~/.agents/skills` as the destination only if you want the skills in every project.
The installer refuses existing skill folders and unrelated links. It does not replace them.

## Codex GUI

Use a local coding session in the Codex desktop application.
For linked skills, open the project configured above and start a new session.

For a plugin, register the extracted release with `codex plugin marketplace add` as shown above.
Restart the desktop application. Open its Plugins Directory and select **Alex Hutnik 3D Skills**.
Install **3D Skills**, then start a new local session.
Interface names can differ between desktop releases. Local skill folders remain an alternative.

Plugin installation copies files into a cache. It does not use the checkout's Python environments.
The skill instructions run `uv sync` inside the installed skill folder before using its tools.
The same rule applies after a plugin update.

## Claude CLI

Use Claude Code. Extract the release ZIP into a clean folder, then register and install it:

```sh
claude plugin marketplace add /absolute/path/to/extracted-3d-skills
claude plugin install 3d-skills@alexhutnik-3d
```

Start a new session. Invoke `/3d-skills:design-3d`.
For development without installation:

```sh
claude --plugin-dir /absolute/path/to/3d-skills
```

You can also link individual skills to a project:

```sh
uv run --locked --no-dev python manage.py link --destination /absolute/project/.claude/skills
```

Start Claude Code in that project. Invoke `/design-3d` for the linked skill.

## Claude GUI

For local CAD tools, prefer a local Claude Code session in the desktop application's Code tab.
Open the project with linked `.claude/skills`, or use the installed Claude Code plugin.
Start a new session and select the skill.

Claude also accepts a custom plugin file through **Customize → Plugins**.
Upload `3d-skills-v1.0.0.zip` from the GitHub release if you want that installation method.
A chat or Cowork session must have access to a compatible execution environment and the project files to run these scripts.
Installing instructions alone does not provide access to the Python environment on your computer.
Use a local Code session if the current session cannot run `uv` against the project files.

We validate the Claude manifests with the installed Claude CLI.
We do not claim that every desktop mode or account policy can execute CAD tools.

## Use the skills

| Skill | Task |
| --- | --- |
| `design-3d` | Select a CAD workflow and record dimensions. |
| `design-enclosures` | Fit enclosures around measured components. |
| `design-gears` | Define gears, placement, and interference checks. |
| `design-hinges` | Define hinges, pins, clearances, and travel. |
| `design-assemblies` | Arrange parts and inspect movement. |
| `design-decorative` | Create lettering, reliefs, and layered parts. |
| `inspect-3d` | Create an offline HTML review from STEP files. |
| `release-3d-print` | Compare STEP and STL files with stated requirements. |

Example request:

> Use design-3d to make a small enclosure. Keep the dimensions editable. Export STEP and STL, check both, and make an HTML review.

The design skills guide modeling decisions. They do not provide a universal part generator.
The Python scripts perform repeatable export and inspection tasks.
Read each skill's references for its command arguments and limits.

Generate a synthetic example and its offline review:

```sh
uv run --project skills/inspect-3d --locked --no-dev python skills/inspect-3d/examples/make_demo.py /absolute/project/demo
uv run --project skills/inspect-3d --locked --no-dev python skills/inspect-3d/scripts/export_review.py /absolute/project/demo/scene.json /absolute/project/demo/review.html
```

Open `review.html` in a browser. It contains its viewer and display geometry.
The viewer uses triangles. Keep the STEP files for exact measurements.

## Update and roll back

For a linked installation, update the checkout to a tested release:

```sh
git status --short
git fetch --tags origin
git switch --detach v1.0.0
uv run --locked --no-dev python manage.py setup
uv run --locked --no-dev python manage.py doctor
```

Replace `v1.0.0` with the desired release. Keep local changes on a development branch before switching.
Select the previous tag and repeat setup to roll back.
Links continue to point to the same checkout.

For plugins, replace the extracted source folder with a clean copy of the desired release.
Keep the same folder path. Then refresh the marketplace and installed plugin.
Codex desktop users can reinstall the local plugin through the Plugins Directory.
Codex CLI users can run:

```sh
codex plugin remove 3d-skills@alexhutnik-3d
codex plugin add 3d-skills@alexhutnik-3d
```

Claude CLI users can run:

```sh
claude plugin marketplace update alexhutnik-3d
claude plugin update 3d-skills@alexhutnik-3d
```

Restart the agent session after an update. Confirm the installed version before using it.
Do not edit cached plugin files. Put changes in the source checkout and create a new release.
A plugin installed from a ZIP needs a new ZIP for an update.
See [release instructions](docs/RELEASING.md) for the exact release process.

To remove linked skills:

```sh
uv run --locked --no-dev python manage.py unlink --destination /absolute/project/.agents/skills
```

Use the original destination. This command removes only links to the current checkout.
Remove plugins through the application's plugin manager.

## Test and contribute

```sh
uv sync --locked
uv run --locked python manage.py setup --dev --browser
uv run --locked python manage.py test --browser
uv run --locked python manage.py package
```

`manage.py test` runs Ruff and pytest in all three isolated environments.
Without `--browser`, it excludes only the browser tests.
Tests generate their own synthetic parts.
No test requires private projects, credentials, or an installed CAD application.

The release archive contains the skills, scripts, dependency locks, examples, and tests.
It excludes virtual environments and generated models.

See [the build plan](docs/PLAN.md), [validation](docs/VALIDATION.md), and [third-party notices](NOTICE.md).

Installation references: [OpenAI plugins](https://developers.openai.com/plugins/build/plugins),
[Claude plugins](https://code.claude.com/docs/en/plugins),
[Claude desktop plugins](https://support.claude.com/en/articles/13837440-use-plugins-in-claude).
