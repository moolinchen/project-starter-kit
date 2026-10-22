# Project Starter Kit 1.1.0

English | [简体中文](README.zh-CN.md)

A local-first, per-project starter kit for independent creative and technical work (game design, art, 3D, code). Each project gets a fixed folder layout plus a small local web workbench for tracking tasks, immutable versions, reviews, deliverables, settlement notes and cleanup of temporary material. State lives in a single `management/project.json` inside the project.

> The documentation and UI are currently in Chinese. Daily use needs only **Python 3.9+** and a browser — no third-party dependencies, no accounts, no central database, nothing published to the internet.

## Features

- **Independent project template** (`template/`): copy it and each project is fully self-contained.
- **Local workbench** (`management/server.py` + `index.html`): overview, tasks, version review, deliverables, material batches, settlement and sealing. Saves go through validation, optimistic concurrency (etag / 409 on conflict), history entries, recovery backups and atomic writes.
- **Immutable versions and independent review**: a new version never inherits an earlier approval; approving requires evidence paths; sealed history cannot be rewritten.
- **Image review comparison** (1.1.0): for png/jpg/jpeg/webp/svg/gif versions, view the previous image version of the same task side by side or as an onion-skin overlay with an opacity slider.
- **Cleanup preview, never automatic deletion**: lists exact files, counts and bytes, sorted by size with category totals (1.1.0). It can generate a `cleanup-YYYYMMDD.sh/.bat` script under `90-tmp/` that only contains reviewable items and requires typing `DELETE`; the tool never runs it. There is no delete API.
- **AI-friendly CLI** (`management/cli.py`, 1.1.0): one-line commands for AI agents and scripts, handling token / etag / project lock automatically.
- **Template upgrade tool** (`tools/upgrade_project.py`, 1.1.0): bring an existing project up to the current template safely.
- **Initializer** (`tools/init_project.py`, macOS `新建项目.command`) and an optional installable Skill (`skill/project-start-kit/`).

## Quick start

Try the fictional example:

```sh
cd example-星港窗户演示
python3 management/server.py          # opens http://127.0.0.1:<port> in your browser
```

On macOS you can double-click `启动面板.command`; on Windows `启动面板.bat` or `py -3 management\server.py`. Edit, click “确认修改” (confirm), then “保存到项目” (save to project). Stop the server with Ctrl+C.

Create a new project — either copy the whole `template/` folder somewhere and rename it, or:

```sh
python3 tools/init_project.py /path/to/new-project --name "My Project" --dry-run
python3 tools/init_project.py /path/to/new-project --name "My Project"
```

`init_project.py` only adds missing files. For an existing directory, pass `--mapping mapping.json` describing how existing folders map to template roles (see `skill/project-start-kit/SKILL.md`). Don't create real projects inside the kit itself.

## Directory structure

```
.
├── template/                  # blank project template
│   ├── 00-brief/ 10-plan/ 30-work/ 40-review/ 50-versions/ 80-deliver/ 90-tmp/
│   ├── AGENTS.md  PROJECT.md
│   ├── management/            # server.py, core.py, cli.py, app.js, index.html,
│   │                          # style.css, project.json, PROTOCOL.md, SCHEMA.md
│   └── 启动面板.command / 启动面板.bat   # launchers
├── example-星港窗户演示/        # fictional, openable example project
├── tools/                     # init_project.py, upgrade_project.py
├── skill/project-start-kit/   # optional Skill (not installed automatically)
├── docs/                      # quick start, detailed guide, AI integration, test report (Chinese)
├── tests/                     # Python stdlib backend tests + Node UI logic tests
├── 新建项目.command            # macOS interactive project creator
├── CHANGELOG.md  LICENSE  MANIFEST.sha256.json
```

## Upgrading an existing project

Stop the project's workbench server first, then run from the kit:

```sh
python3 tools/upgrade_project.py <project-dir> --dry-run      # list differences only, writes nothing
python3 tools/upgrade_project.py <project-dir>                # only add missing files
python3 tools/upgrade_project.py <project-dir> --apply-code   # back up, replace management code, migrate project.json
```

Options: `--no-diff` (don't print diff bodies), `--json` (print a JSON result). Old code and the old `project.json` are backed up to `management/recovery/upgrade-<time>-from-<old-version>/`. `AGENTS.md`, `PROJECT.md` and folder READMEs are only reported for manual merging; work files are never read, moved or deleted. The tool refuses to run while the project lock exists.

## CLI (inside each project)

```sh
python3 management/cli.py status
python3 management/cli.py add-task --title "Title" [--status 进行中] [--batch T012_name]
python3 management/cli.py add-version --task T001 --path 30-work/file.svg [--path ...] [--label] [--note]
python3 management/cli.py submit-review --version V003 [--note]
python3 management/cli.py review --version V003 --result pass|reject --issues "conclusion" [--evidence path ...]
python3 management/cli.py add-deliverable --version V003 --path 80-deliver/file --criteria "criteria" [--accepted]
python3 management/cli.py preview-cleanup [--write-script]
```

Global options: `--project <dir>` (defaults to the project containing `cli.py`), `--json`. Exit codes: 0 success, 1 validation/other error, 2 conflict/lock held. When the server is running the CLI uses its local API; otherwise it takes the same project lock and writes through the same validated commit path. There is no delete command.

Validate a project with `python3 management/core.py` and preview cleanup with `python3 management/core.py --preview`. See `docs/AI接入.md` for a prompt you can give to any AI agent.

## Security notes

- The server listens **only on the loopback address `127.0.0.1`** (auto-selected free port, or `--port`). It checks the `Host` header and rejects cross-origin writes.
- Write requests require a per-session token (`X-Project-Token`) generated in memory at startup; **the token is never written to project files**. The lock file `management/.server.lock` stores only the lock kind, PID and port.
- `GET /files/<path>` is read-only and serves only regular image files inside the project; `..`, absolute paths, symlinks, hidden files and non-image types are rejected; SVG is served with a sandboxing CSP.
- Nothing is deleted automatically, no global config or caches are touched, and no payments are made.

## Testing

```sh
python3 tests/test_project.py
python3 tests/test_v110.py
node tests/test_ui_logic.js
```

Tests run against isolated temporary copies. See `docs/测试报告.md` for what was and wasn't verified (e.g. the Windows `.bat` scripts and the comparison slider's visuals in a real browser have not been checked manually).

## License

[MIT](LICENSE) © 2026 moolinchen
