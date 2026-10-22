#!/usr/bin/env python3
"""给 AI 与脚本用的一行命令接口。

与面板走同一条校验/写入路径：服务运行中时调用其本机 API（自动取 token/etag）；
服务未运行时取得同一把项目锁，用 core.commit 写入（校验、history、recovery 备份、原子替换）。
不提供删除命令。仅使用 Python 标准库。
"""
import argparse, copy, json, sys, urllib.error, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import core

EXIT_ERROR, EXIT_CONFLICT = 1, 2

class CliError(Exception): pass

def out(obj, as_json):
    if as_json: print(json.dumps(obj, ensure_ascii=False, indent=2))
    else:
        for k, v in obj.items():
            if isinstance(v, (dict, list)): v = json.dumps(v, ensure_ascii=False)
            print(f'{k}: {v}')

def need_core():
    if not hasattr(core, 'commit'):
        raise CliError('management/core.py 版本过旧，请先用模板包 tools/upgrade_project.py --apply-code 升级')

# ---------- 与服务通信 ----------
def http(port, path, body=None, token=None):
    url = f'http://127.0.0.1:{port}{path}'
    headers = {'Content-Type': 'application/json'}
    if token: headers['X-Project-Token'] = token
    req = urllib.request.Request(url, json.dumps(body).encode() if body is not None else None, headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        try: msg = json.load(e).get('error', '')
        except Exception: msg = ''
        if e.code == 409: raise core.Conflict(msg or '冲突')
        raise CliError(f'服务返回 {e.code}：{msg}')
    except (urllib.error.URLError, OSError) as e:
        raise CliError(f'项目锁显示服务在端口 {port} 运行，但无法连接（{e}）。若服务已崩溃，确认进程已退出后人工删除 management/.server.lock')

def running_server(root):
    info = core.lock_info(root)
    if info is None: return None
    if info.get('kind') == 'server' and isinstance(info.get('port'), int): return info['port']
    if info.get('kind') == 'cli': raise core.Conflict(f'另一个 CLI 写入正在进行（PID {info.get("pid")}），请稍后重试')
    raise CliError('检测到项目锁，但无法得知服务端口（可能是 1.0.0 旧服务）。请关闭服务后再用 CLI，或在面板中操作')

def load(root):
    port = running_server(root)
    if port:
        got = http(port, '/api/project')
        return got['data'], {'port': port, 'etag': got['etag'], 'token': got['token']}
    data, etag = core.read_state(root)
    return data, {'port': None, 'etag': etag}

def mutate(root, fn, action):
    """fn(data) 修改副本并返回结果说明。服务在跑走 API，否则持锁走 core.commit。"""
    need_core()
    port = running_server(root)
    if port:
        got = http(port, '/api/project'); data = copy.deepcopy(got['data'])
        info = fn(data)
        res = http(port, '/api/save', {'data': data, 'etag': got['etag']}, got['token'])
        via = 'server'
    else:
        with core.project_lock(root, 'cli'):
            old, etag = core.read_state(root); data = copy.deepcopy(old)
            info = fn(data)
            res = core.commit(root, data, etag, action='CLI：' + action)
        via = 'offline-lock'
    info.update({'ok': True, 'via': via, 'revision': res['data']['revision'], 'unchanged': bool(res.get('unchanged'))})
    return info

# ---------- 工具函数 ----------
def next_id(rows, prefix):
    n = 1
    while any(r['id'] == f'{prefix}{n:03d}' for r in rows): n += 1
    return f'{prefix}{n:03d}'

def find(rows, key, value, label):
    for r in rows:
        if r.get(key) == value: return r
    raise CliError(f'{label}不存在：{value}')

def check_paths(root, paths, must_exist):
    for p in paths:
        core.path_check(root, p, must_exist)
    return '\n'.join(paths)

# ---------- 命令 ----------
def cmd_status(root, a):
    data, conn = load(root)
    reviews = {r['versionId']: r['status'] for r in data['reviews']}
    return {
        'project': data['project']['name'], 'templateVersion': data['templateVersion'], 'revision': data['revision'],
        'server': conn['port'] or '未运行（离线模式，写入时会加项目锁）',
        'tasks': [f"{t['id']} [{t['status']}] {t['title']}" + (f" 阻碍：{t['blocker']}" if t['blocker'] else '') for t in data['tasks']],
        'versions': [f"{v['id']} ({v['taskId']}) {v['label']} → 审核：{reviews.get(v['id'], '未提交')}" for v in data['versions']],
        'deliveries': [f"{d['id']} {d['versionId']} {d['path']} [{d['status']}]" for d in data['deliveries']],
        'pendingReviews': [r['versionId'] for r in data['reviews'] if r['status'] == '待审核'],
        'seals': len(data['seals']),
    }

def cmd_add_task(root, a):
    def fn(d):
        tid = a.id or next_id(d['tasks'], 'T')
        d['tasks'].append({'id': tid, 'title': a.title, 'status': a.status, 'blocker': a.blocker or '', 'batchId': a.batch or ''})
        return {'action': 'add-task', 'id': tid}
    return mutate(root, fn, '新增任务 ' + a.title)

def cmd_add_version(root, a):
    def fn(d):
        find(d['tasks'], 'id', a.task, '任务')
        vid = a.id or next_id(d['versions'], 'V')
        paths = check_paths(root, a.path, not a.allow_missing)
        d['versions'].append({'id': vid, 'taskId': a.task, 'label': a.label or vid, 'paths': paths, 'note': a.note or ''})
        return {'action': 'add-version', 'id': vid, 'paths': a.path}
    return mutate(root, fn, '登记版本')

def cmd_submit_review(root, a):
    def fn(d):
        find(d['versions'], 'id', a.version, '版本')
        cur = [r for r in d['reviews'] if r['versionId'] == a.version]
        if cur:
            r = cur[0]
            if r['status'] == '通过': raise CliError(f'{a.version} 已通过审核；新的工作结果请登记新版本')
            r['status'] = '待审核'
            if a.note: r['issues'] = a.note
            return {'action': 'submit-review', 'id': r['id'], 'resubmitted': True}
        rid = next_id(d['reviews'], 'R')
        d['reviews'].append({'id': rid, 'versionId': a.version, 'status': '待审核', 'issues': a.note or '', 'evidence': ''})
        return {'action': 'submit-review', 'id': rid}
    return mutate(root, fn, '提交审核 ' + a.version)

def cmd_review(root, a):
    status = {'pass': '通过', 'reject': '退回'}[a.result]
    def fn(d):
        find(d['versions'], 'id', a.version, '版本')
        evidence = check_paths(root, a.evidence or [], True)
        if status == '通过' and (not a.issues.strip() or not evidence):
            raise CliError('通过需要 --issues 结论和至少一个 --evidence 证据路径')
        cur = [r for r in d['reviews'] if r['versionId'] == a.version]
        if cur: r = cur[0]
        else:
            r = {'id': next_id(d['reviews'], 'R'), 'versionId': a.version, 'status': '', 'issues': '', 'evidence': ''}
            d['reviews'].append(r)
        if status == '退回':
            for dl in d['deliveries']:
                if dl['versionId'] == a.version and dl['status'] == '已验收':
                    raise CliError(f'交付 {dl["id"]} 已验收；退回前先把它改回待验收（协议要求）')
        r.update({'status': status, 'issues': a.issues, 'evidence': evidence or r['evidence']})
        return {'action': 'review', 'id': r['id'], 'result': status}
    return mutate(root, fn, f'审核 {a.version} {status}')

def cmd_add_deliverable(root, a):
    def fn(d):
        find(d['versions'], 'id', a.version, '版本')
        check_paths(root, [a.path], not a.allow_missing)
        did = a.id or next_id(d['deliveries'], 'D')
        d['deliveries'].append({'id': did, 'versionId': a.version, 'path': a.path, 'criteria': a.criteria, 'status': '已验收' if a.accepted else '待验收'})
        return {'action': 'add-deliverable', 'id': did}
    return mutate(root, fn, '新增交付')

def cmd_preview_cleanup(root, a):
    data, _ = load(root)
    if a.write_script:
        need_core()
        return core.cleanup_script(data, root)
    pv = core.preview(data, root)
    if a.json: return pv
    t = pv['summary']['total']
    rows = [f"{'可人工复核' if i['eligible'] else '禁止清理'}  {i['human']:>9}  {i['fileCount']} 个文件  {i['path']}" + ('' if i['eligible'] else '  ← ' + '；'.join(i['reasons'])) for i in pv['items']]
    cats = [f"{k}: {v['human']}（可复核 {v['eligibleHuman']}）" for k, v in pv['summary']['categories'].items()]
    return {'items(按大小)': rows, 'categories': cats, 'total': f"{t['human']}，其中可人工复核 {t['eligibleHuman']} / {t['eligibleFiles']} 个文件", 'notice': pv['notice']}

def build_parser():
    p = argparse.ArgumentParser(description='项目工作台 CLI（AI 友好；不需要手动处理 token/etag；无删除命令）')
    p.add_argument('--project', help='项目根目录（默认为本文件所在项目）')
    p.add_argument('--json', action='store_true', help='以 JSON 输出')
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('status', help='项目摘要')
    s = sub.add_parser('add-task', help='新增任务'); s.add_argument('--title', required=True); s.add_argument('--id'); s.add_argument('--status', default='待办', choices=['待办', '进行中', '阻塞', '完成']); s.add_argument('--blocker'); s.add_argument('--batch')
    s = sub.add_parser('add-version', help='登记不可变版本（绑定任务与文件）'); s.add_argument('--task', required=True); s.add_argument('--path', action='append', required=True, help='可重复'); s.add_argument('--label'); s.add_argument('--note'); s.add_argument('--id'); s.add_argument('--allow-missing', action='store_true', help='允许登记尚不存在的路径')
    s = sub.add_parser('submit-review', help='把版本提交为待审核'); s.add_argument('--version', required=True); s.add_argument('--note')
    s = sub.add_parser('review', help='审核结论'); s.add_argument('--version', required=True); s.add_argument('--result', required=True, choices=['pass', 'reject']); s.add_argument('--issues', required=True); s.add_argument('--evidence', action='append', help='证据路径，可重复；pass 必填')
    s = sub.add_parser('add-deliverable', help='新增交付项'); s.add_argument('--version', required=True); s.add_argument('--path', required=True); s.add_argument('--criteria', required=True); s.add_argument('--accepted', action='store_true', help='直接标为已验收（需该版本已通过）'); s.add_argument('--id'); s.add_argument('--allow-missing', action='store_true')
    s = sub.add_parser('preview-cleanup', help='清理预览（按大小排序，带分类汇总）'); s.add_argument('--write-script', action='store_true', help='生成需输入 DELETE 确认的删除脚本到 90-tmp（不执行）')
    return p

COMMANDS = {'status': cmd_status, 'add-task': cmd_add_task, 'add-version': cmd_add_version, 'submit-review': cmd_submit_review,
            'review': cmd_review, 'add-deliverable': cmd_add_deliverable, 'preview-cleanup': cmd_preview_cleanup}

def main(argv=None):
    a = build_parser().parse_args(argv)
    root = Path(a.project).resolve() if a.project else Path(__file__).resolve().parent.parent
    try:
        out(COMMANDS[a.cmd](root, a), a.json); return 0
    except core.Conflict as e:
        print('冲突：' + str(e), file=sys.stderr); return EXIT_CONFLICT
    except (CliError, ValueError, OSError) as e:
        print('失败：' + str(e), file=sys.stderr); return EXIT_ERROR

if __name__ == '__main__':
    sys.exit(main())
