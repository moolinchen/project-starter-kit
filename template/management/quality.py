#!/usr/bin/env python3
"""Optional local quality gates. Python 3.9+, no third-party dependencies."""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

LEVELS = ("quick", "verify", "release")
ROOT = Path(__file__).resolve().parent.parent
CONFIG = "management/quality.local.json"
TAIL_BYTES = 4096


def checked_dir(root, value):
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("cwd must be a project-relative POSIX path")
    path = Path(value)
    if path.is_absolute() or path.drive or ".." in path.parts:
        raise ValueError("cwd must stay inside the project")
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("symlink cwd is not allowed")
    if not current.is_dir() or not current.resolve().is_relative_to(root):
        raise ValueError("cwd missing or outside project")
    return current


def load(root):
    path = root / CONFIG
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("symlink config is not allowed")
    if not path.exists():
        return []
    config = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or config.get("schemaVersion") != 1:
        raise ValueError("unsupported quality configuration")
    steps = config.get("steps")
    if not isinstance(steps, list):
        raise ValueError("steps must be an array")
    names = set()
    result = []
    for step in steps:
        if not isinstance(step, dict):
            raise ValueError("step must be an object")
        name, level, argv = step.get("name"), step.get("level"), step.get("argv")
        timeout = step.get("timeout", 120)
        if not isinstance(name, str) or not name or len(name) > 80 or name in names:
            raise ValueError("step names must be unique and at most 80 characters")
        if level not in LEVELS or not isinstance(argv, list) or not argv:
            raise ValueError("invalid level or argv")
        if any(not isinstance(a, str) or not a or "\0" in a for a in argv):
            raise ValueError("argv must contain nonempty strings")
        if type(timeout) is not int or not 1 <= timeout <= 3600:
            raise ValueError("timeout must be 1..3600 seconds")
        cwd = checked_dir(root, step.get("cwd"))
        names.add(name)
        result.append((name, level, argv, cwd, timeout))
    return result


def run(root, level, approved=False):
    root = root.resolve()
    steps = load(root)
    selected = [s for s in steps if LEVELS.index(s[1]) <= LEVELS.index(level)]
    # Never imply that an empty configuration or an absent tier was verified.
    missing = [tier for tier in LEVELS[:LEVELS.index(level) + 1]
               if not any(s[1] == tier for s in selected)]
    if not approved:
        return {"status": "plan", "level": level, "missingLevels": missing,
                "steps": [{"name": n, "level": l, "argv": a,
                           "cwd": str(c.relative_to(root)), "timeout": t}
                          for n, l, a, c, t in selected]}, 0
    results = []
    for name, tier, argv, cwd, timeout in selected:
        # Run only trusted, reviewed project commands; this is not a sandbox.
        with tempfile.TemporaryFile() as log:
            try:
                proc = subprocess.run(argv, cwd=cwd, shell=False, stdin=subprocess.DEVNULL,
                                      stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
                status = "pass" if proc.returncode == 0 else "fail"
                code = proc.returncode
            except subprocess.TimeoutExpired:
                status, code = "timeout", None
            except OSError as exc:
                status, code = "unavailable", None
                log.write(str(exc).encode("utf-8", errors="replace"))
            item = {"name": name, "level": tier, "status": status, "exitCode": code}
            if status != "pass":
                size = log.seek(0, 2)
                log.seek(max(0, size - TAIL_BYTES))
                item["tail"] = log.read(TAIL_BYTES).decode("utf-8", errors="replace")
                item["truncated"] = size > TAIL_BYTES
            results.append(item)
        if status != "pass":
            return {"status": "failed", "level": level, "missingLevels": missing,
                    "steps": results, "notRun": [s[0] for s in selected[len(results):]]}, 1
    return {"status": "incomplete" if missing else "pass", "level": level,
            "missingLevels": missing, "steps": results}, 2 if missing else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("level", choices=LEVELS, default="quick", nargs="?")
    parser.add_argument("--run", action="store_true", help="execute reviewed local commands")
    args = parser.parse_args()
    try:
        result, code = run(ROOT, args.level, args.run)
    except (ValueError, OSError) as exc:
        result, code = {"status": "configuration-error", "error": str(exc)}, 2
    print(json.dumps(result, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
