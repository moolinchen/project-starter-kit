# Project Starter Kit 1.1.0

English | [简体中文](README.zh-CN.md)

## Hand it to your AI

The instructions and tools in this kit are written for AI agents to read. You can hand the kit straight to an AI and let it run everything — no need to click scripts yourself:

- By reading the project's `AGENTS.md` and `docs/AI接入.md` (AI integration guide), the AI learns where files go and how to record status.
- The AI can create projects, upgrade existing ones, record tasks / versions / reviews / deliverables, and generate cleanup previews entirely from the command line (`tools/init_project.py`, `tools/upgrade_project.py`, `management/cli.py`).
- **The web workbench is for people**: check progress, review images, accept deliverables.
- **Irreversible actions need human confirmation**: replacing management code during an upgrade (`--apply-code`) and running a cleanup deletion script. The tools never delete files on their own, and a deletion script must be run by a person who types `DELETE`.

Example instruction you can copy to your AI:

> The project starter kit is at <kit path>. First read its README.md and docs/AI接入.md, then create a new project named <project name> in <target directory> (show me a --dry-run first). After that, follow the rules in the project's AGENTS.md: put files in the matching folders, and record tasks, versions, reviews and deliverables with `python3 management/cli.py` — never edit the JSON by hand. At the end of each session, run `python3 management/core.py --preview` and report the validation result and the files eligible for cleanup. Stop and ask me before any `--apply-code` upgrade or file deletion.

AI agents don't always follow instructions perfectly, so verify key results in the workbench.

## Why this exists

When you work with AI on design docs, art, 3D or code, the same problems keep coming up:

- **Files end up everywhere**: briefs, project files, review images, deliverables and temporary caches all get mixed together; switch AI tools or come back a few weeks later and you can't find anything.
- **Version and review records are scattered**: which version was approved, by whom, and on what evidence lives only in chat history; once a new version is made, nobody can say whether it was reviewed again.
- **Deliverables are hard to find**: there's no single record of which file was actually delivered or whether it was accepted.
- Temporary files keep piling up: render caches, logs, test screenshots, scratch files from checks and more. With AI in the loop these easily run into hundreds or thousands of files, yet you don't dare delete them for fear of losing review evidence or key files and breaking the project.

How this kit handles it:

- Every project uses the same folder layout (00-brief to 90-tmp), so each kind of file has a fixed home and both AI and people follow the same rules.
- All status lives in a single `management/project.json`; every save is validated, logged to history, and the previous data is backed up.
- Registered versions can't be modified; a new version never inherits an earlier review result, and approving a version requires evidence file paths.
- A deliverable can only be accepted when its version has passed review; a project can be sealed, and sealed history can't be rewritten.
- Temporary material is registered in batches. Cleanup only produces a preview list, and anything still referenced by a review can't be cleaned up. You can generate a deletion script that requires manual confirmation.
- When reviewing images, compare the previous and current version of the same task side by side or as an overlay.
- Only Python 3.9+ and a browser are needed — no third-party dependencies, accounts or database; all data stays in the project on your machine. Every project is independent.

## Getting started

### Option 1: Hand it to your AI

Send the example instruction above to your AI (it needs to be able to read and write local files and run commands). It will create the project with `tools/init_project.py` and record work with `management/cli.py`. Open the workbench (see below) whenever you want to check progress or review images.

You can also install `skill/project-start-kit/` as a Skill in whatever way your AI tool supports, then just ask it to "create a new standalone project".

### Option 2: Manually

1. Start with the example: open `example-星港窗户演示` (Star Harbor Window demo). On macOS double-click `启动面板.command` (launch panel), on Windows double-click `启动面板.bat`, or run `python3 management/server.py`. Your browser will open `http://127.0.0.1:<port>`.
2. After editing in the web page, click 「确认修改」 (confirm changes), then 「保存到项目」 (save to project) to write to disk. To stop the server, press Ctrl+C in the launch window.
3. Create a new project: copy the whole `template` folder wherever you like and rename it; or double-click `新建项目.command` (new project) at the root (macOS); or run:

```sh
python3 tools/init_project.py /path/to/new-project --name "Project name" --dry-run
python3 tools/init_project.py /path/to/new-project --name "Project name"
```

Don't create real projects inside the kit itself. See [docs/快速开始.md](docs/快速开始.md) (quick start) for more.

## Folders and files

### Top level

| Path | Purpose |
|---|---|
| `template/` | Blank project template; copy it to start a new project |
| `example-星港窗户演示/` | A complete fictional example (Star Harbor Window demo) with work files, reviews, deliverables and cleanup states; open its workbench directly |
| `tools/` | Tools for creating and upgrading projects |
| `skill/project-start-kit/` | Optional AI Skill that teaches an AI how to create projects with this kit; not installed automatically |
| `docs/` | User documentation |
| `tests/` | Automated tests |
| `新建项目.command` | Interactive project creator for macOS (new project) |
| `CHANGELOG.md` | Release notes |
| `MANIFEST.sha256.json` | Checksums of every file, to confirm the kit is complete and unmodified |
| `LICENSE` | MIT license |

### Project folders (inside template, the same for every project)

| Folder | What goes in it |
|---|---|
| `00-brief/` | Original briefs, contracts and references; kept by default |
| `10-plan/` | Plans, decision notes, and folder mappings when adopting an existing project |
| `30-work/` | Editable project files with all their dependencies (not just previews) |
| `40-review/` | Review comparison packages organized by task batch; `accepted/` holds selected evidence for approvals |
| `50-versions/` | Snapshots and rollback packages at key milestones — not every change |
| `80-deliver/` | Confirmed deliverables |
| `90-tmp/` | Intermediate output, caches and logs organized by batch; the main target of cleanup |
| `AGENTS.md` | Project rules for AI: what to read first, where files go, how to write status |
| `PROJECT.md` | Project entry point: how to start the workbench and what each folder is for |
| `启动面板.command` / `启动面板.bat` | Double-click to launch the workbench (macOS / Windows) |

### management/ (the workbench inside each project)

| File | Purpose |
|---|---|
| `project.json` | The project's single status record: overview, tasks, versions, reviews, deliverables, batches, settlement, sealing, history |
| `server.py` | Local web server providing the workbench page and save API |
| `index.html` / `app.js` / `style.css` | Workbench web page |
| `core.py` | Core logic for validation, saving, history and backups, and cleanup preview; can also be run directly to validate |
| `cli.py` | Command line for AI agents and scripts |
| `PROTOCOL.md` | Read/write rules and API description |
| `SCHEMA.md` | Field structure of `project.json` |
| `recovery/` (created at runtime) | Backups of previous data before each save, plus upgrade backups |

### tools/

| File | Purpose |
|---|---|
| `init_project.py` | Create a project, or add template files to an existing folder; only adds missing files, never overwrites |
| `upgrade_project.py` | Upgrade an existing project to the current template version |

### tests/

`test_project.py`, `test_v110.py` (Python standard library) and `test_ui_logic.js` (Node). Node isn't needed for daily use. The upgrade tests in `test_v110.py` require the `PROJECT_KIT_V100` environment variable pointing to a 1.0.0 kit; otherwise they are skipped.

### docs/

| File | Contents |
|---|---|
| `快速开始.md` (quick start) | Get going in five minutes |
| `详细指南.md` (detailed guide) | Saving and recovery, material archiving, cleanup, review comparison, upgrades, sealing, etc. |
| `AI接入.md` (AI integration) | Prompt for onboarding an AI, CLI command table, acceptance steps |
| `测试报告.md` (test report) | What has and hasn't been verified |

The docs are currently in Chinese.

## Upgrading an existing project

Existing projects don't follow template updates automatically. Stop the project's workbench first, then run:

```sh
python3 tools/upgrade_project.py <project-dir> --dry-run      # show differences only, writes nothing
python3 tools/upgrade_project.py <project-dir>                # only add missing files
python3 tools/upgrade_project.py <project-dir> --apply-code   # back up, replace management code, migrate project.json (needs human confirmation)
```

Old code is backed up to `management/recovery/upgrade-<time>-from-<old-version>/`. Editable files such as `AGENTS.md` and `PROJECT.md` only have their differences reported; work files are never touched.

## CLI

Run `python3 management/cli.py <command>` in the project folder:

| Command | Purpose |
|---|---|
| `status` | Summary of project, tasks, reviews and deliverables |
| `add-task` | Add a task |
| `add-version` | Register a version (immutable) |
| `submit-review` | Submit for review |
| `review` | Approve or reject (approval requires evidence paths) |
| `add-deliverable` | Register a deliverable |
| `preview-cleanup [--write-script]` | Cleanup preview; can generate a deletion script that requires typing DELETE and is never run automatically |

See [docs/AI接入.md](docs/AI接入.md) for options. The CLI has no delete command.

## Security

- The workbench listens only on the loopback address `127.0.0.1`, so other devices can't reach it; cross-origin writes are rejected.
- Writes require a session token generated fresh at each start; it stays in memory and is never written to any file.
- The image endpoint is read-only and serves only regular image files inside the project.
- Nothing is deleted automatically, no global settings or caches are changed, and no payments are involved.

## Attribution and commercial use

This project is released under the [MIT License](LICENSE): you may use, modify, distribute and use it commercially, as long as you keep the copyright notice `Copyright (c) 2026 moolinchen` and the full license text in your copies.

Suggested attribution:

> Based on [Project Starter Kit](https://github.com/moolinchen/project-starter-kit) (© 2026 moolinchen, MIT License).
