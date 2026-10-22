# Changelog / 更新记录

## 1.1.0 (2026-10-22)

- **Template upgrade tool** `tools/upgrade_project.py`: `--dry-run` lists differences only; the default run only adds missing files; `--apply-code` backs up old management code/protocol to `management/recovery/upgrade-<time>-from-<old>/`, replaces it, and migrates `templateVersion` in `project.json` (backup, history entry, revision +1). User-editable files (AGENTS.md, PROJECT.md, folder READMEs) are only reported; work files are never touched; refuses to run while the project lock exists.
- **AI CLI** `management/cli.py`: `status`, `add-task`, `add-version`, `submit-review`, `review`, `add-deliverable`, `preview-cleanup`. Uses the local API when the server is running, otherwise takes the same project lock and writes through `core.commit` (validation, history, recovery, atomic write). Write logic moved from `server.py` into shared `core.py`; the server lock is now JSON (includes port) and is released on SIGTERM.
- **Image review comparison**: the review page shows the previous image version of the same task side by side or as an onion-skin overlay slider (png/jpg/jpeg/webp/svg/gif). New read-only `GET /files/<relative path>` serves only regular image files inside the project; rejects traversal, symlinks and hidden files; SVG is served with a sandbox CSP.
- **Cleanup preview**: sorted by size with readable sizes, per-file details, category and total summaries; can generate `90-tmp/cleanup-YYYYMMDD.sh/.bat` containing only reviewable items, requiring typing `DELETE`, never executed automatically and never overwriting an existing script.
- `project.json` fields unchanged; templateVersion 1.0.0 and 1.1.0 are both accepted.
- The example project was upgraded with the upgrade tool.

## 1.0.0

- Initial release: per-project independent template, local workbench (Python standard library server + browser panel), tasks / immutable versions / reviews / deliverables / settlement / sealing, material batches and cleanup preview (no deletion), `tools/init_project.py`, macOS/Windows launchers, optional `project-start-kit` Skill, fictional example project.
