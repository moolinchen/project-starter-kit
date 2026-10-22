#!/usr/bin/env python3
"""把已建项目与当前母版比较并按需升级。

- 缺少的模板文件：直接补上（不覆盖任何已有文件）。
- 管理代码与协议（management/*.py|js|html|css、PROTOCOL.md、SCHEMA.md、启动面板）有差异：显示 diff；
  只有加 --apply-code 才替换，替换前把旧文件备份到 management/recovery/upgrade-时间/。
- 用户可编辑文件（AGENTS.md、PROJECT.md、各目录 README）有差异：只报告，从不替换。
- project.json：只在管理代码已与母版一致时迁移 templateVersion；先备份，并追加 history。
- 从不读写、移动或删除 00-brief…90-tmp 中的用户工作文件。
"""
import argparse, difflib, filecmp, json, shutil, sys
from datetime import datetime
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
TEMPLATE = BASE / 'template'
sys.path.insert(0, str(TEMPLATE / 'management'))
import core  # 母版的 core：用于校验和迁移写入

CODE_FILES = {'management/PROTOCOL.md', 'management/SCHEMA.md', 'management/core.py', 'management/server.py', 'management/cli.py',
              'management/app.js', 'management/index.html', 'management/style.css', '启动面板.command', '启动面板.bat'}
STATE = 'management/project.json'

def template_files():
    for src in sorted(TEMPLATE.rglob('*')):
        rel = src.relative_to(TEMPLATE)
        if src.is_dir() or '__pycache__' in rel.parts or 'recovery' in rel.parts or any(p.startswith('.') for p in rel.parts): continue
        yield rel.as_posix(), src

def diff_text(old, new, rel):
    try:
        a = old.read_text(encoding='utf8').splitlines(keepends=True); b = new.read_text(encoding='utf8').splitlines(keepends=True)
    except UnicodeDecodeError:
        return '（二进制文件不同）\n'
    return ''.join(difflib.unified_diff(a, b, 'project/' + rel, 'template/' + rel))

def plan(root):
    root = Path(root).resolve()
    if not (root / STATE).is_file(): raise ValueError('不是由本模板建立的项目（缺少 management/project.json）；新项目请用 init_project.py')
    if root == TEMPLATE or TEMPLATE in root.parents: raise ValueError('不能升级母版本身')
    data = json.loads((root / STATE).read_text(encoding='utf8')); core.validate(data, root)
    missing, code, user = [], [], []
    for rel, src in template_files():
        dest = root / rel
        core.path_check(root, rel)  # 拒绝符号链接
        if rel == STATE: continue
        if not dest.exists(): missing.append(rel)
        elif not dest.is_file(): raise ValueError('模板文件位置被目录占用：' + rel)
        elif not filecmp.cmp(src, dest, shallow=False):
            (code if rel in CODE_FILES else user).append((rel, diff_text(dest, src, rel)))
    return root, data, missing, code, user

def upgrade(target, dry_run=False, apply_code=False, show_diff=True, log=print):
    root, data, missing, code, user = plan(target)
    if core.lock_info(root) is not None and not dry_run:
        raise ValueError('项目锁存在（服务或 CLI 正在运行）。请先关闭本项目的面板服务再升级。')
    old_version = data['templateVersion']
    code_current_after = not code or apply_code
    migrate = old_version != core.TEMPLATE_VERSION and code_current_after
    log(f'项目：{root}\n当前模板版本：{old_version} → 母版 {core.TEMPLATE_VERSION}' + ('（仅预览，不写入）' if dry_run else ''))
    log(f'\n[补充缺少文件] {len(missing)} 个' + ''.join('\n  + ' + m for m in missing))
    log(f'\n[管理代码/协议有差异] {len(code)} 个' + ('，将备份后替换' if apply_code and code else '，需加 --apply-code 才替换' if code else ''))
    for rel, d in code:
        log('  ~ ' + rel)
        if show_diff: log(d.rstrip('\n'))
    log(f'\n[用户可编辑文件有差异，不替换] {len(user)} 个' + ''.join('\n  ! ' + r for r, _ in user))
    if any(r == 'AGENTS.md' for r, _ in user):
        log('  提示：1.1.0 的 AGENTS.md 新增“写状态优先使用 management/cli.py”一行，可人工合并。')
    log('\n[project.json] ' + ('已是 ' + old_version if old_version == core.TEMPLATE_VERSION else
        f'将迁移 templateVersion {old_version}→{core.TEMPLATE_VERSION}（先备份，追加 history，revision+1）' if migrate else
        '管理代码未升级，暂不迁移（旧代码只认旧版本号）'))
    result = {'root': str(root), 'dryRun': dry_run, 'added': missing, 'codeChanged': [r for r, _ in code],
              'codeReplaced': [], 'userFilesDiffer': [r for r, _ in user], 'migrated': False, 'backup': None}
    if dry_run: return result
    backup = None
    def backup_dir():
        nonlocal backup
        if backup is None:
            backup = core.path_check(root, 'management/recovery') / ('upgrade-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '-from-' + old_version)
            backup.mkdir(parents=True, exist_ok=False)
        return backup
    with core.project_lock(root, 'upgrade'):
        for rel in missing:
            src = TEMPLATE / rel; dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open('xb') as f: f.write(src.read_bytes())
            shutil.copymode(src, dest)
        if apply_code:
            for rel, _ in code:
                src = TEMPLATE / rel; dest = root / rel
                keep = backup_dir() / rel; keep.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest, keep)
                core.atomic(dest, src.read_bytes()); shutil.copymode(src, dest)
                result['codeReplaced'].append(rel)
        if migrate:
            shutil.copy2(root / STATE, backup_dir() / 'project.json')
            core.migrate(root, core.TEMPLATE_VERSION)
            result['migrated'] = True
        core.validate(json.loads((root / STATE).read_text(encoding='utf8')), root)
    result['backup'] = str(backup.relative_to(root)) if backup else None
    log('\n完成。' + (f'旧文件备份在 {result["backup"]}（不会自动删除）。' if backup else '') + ' 已运行校验：通过。')
    return result

def main():
    p = argparse.ArgumentParser(description='把已建项目升级到当前母版（不碰用户工作文件，不删除任何文件）')
    p.add_argument('project'); p.add_argument('--dry-run', action='store_true', help='只列出差异，不写入')
    p.add_argument('--apply-code', action='store_true', help='备份后替换有差异的管理代码与协议，并迁移 project.json')
    p.add_argument('--no-diff', action='store_true', help='不打印 diff 正文'); p.add_argument('--json', action='store_true', help='最后输出 JSON 结果')
    a = p.parse_args()
    try:
        r = upgrade(a.project, a.dry_run, a.apply_code, not a.no_diff)
        if a.json: print(json.dumps(r, ensure_ascii=False, indent=2))
    except Exception as e:
        print('升级失败：' + str(e), file=sys.stderr); sys.exit(1)

if __name__ == '__main__': main()
