"""1.1.0 新功能测试：模板升级、CLI、图片只读服务、清理排序与删除脚本。仅标准库。"""
import io, json, os, shutil, subprocess, sys, tempfile, threading, unittest, urllib.error, urllib.request
from contextlib import redirect_stdout
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / 'template/management')); sys.path.insert(0, str(BASE / 'tools'))
import core, server, cli, upgrade_project

V100 = Path(os.environ.get('PROJECT_KIT_V100', '')) / 'example-星港窗户演示'  # 设置 PROJECT_KIT_V100=1.0.0 包目录以运行升级测试
NO_HTTP = os.environ.get('PROJECT_KIT_NO_HTTP') == '1'

def make_project(tmp, source=None):
    root = Path(tmp) / 'p'
    shutil.copytree(source or BASE / 'example-星港窗户演示', root, ignore=shutil.ignore_patterns('__pycache__', '.server.lock', 'recovery'))
    return root

def as_current(root):
    for rel in upgrade_project.CODE_FILES:
        shutil.copy2(BASE / 'template' / rel, root / rel)

class UpgradeTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.quiet = lambda *a: None
        if not os.environ.get('PROJECT_KIT_V100') or not V100.exists(): self.skipTest('缺少 1.0.0 示例副本（设置 PROJECT_KIT_V100）')
        self.root = make_project(self.t.name, V100)
        (self.root / '30-work/用户工作.txt').write_text('不要动')
        (self.root / 'AGENTS.md').write_text('用户自定义规则')
    def tearDown(self): self.t.cleanup()
    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
    def test_dry_run_writes_nothing(self):
        before = self.snapshot()
        r = upgrade_project.upgrade(self.root, dry_run=True, log=self.quiet)
        self.assertIn('management/cli.py', r['added']); self.assertIn('management/core.py', r['codeChanged']); self.assertIn('AGENTS.md', r['userFilesDiffer'])
        self.assertEqual(before, self.snapshot())
    def test_without_apply_code_only_adds_missing(self):
        old_core = (self.root / 'management/core.py').read_bytes()
        r = upgrade_project.upgrade(self.root, log=self.quiet)
        self.assertTrue((self.root / 'management/cli.py').exists()); self.assertEqual(old_core, (self.root / 'management/core.py').read_bytes())
        self.assertFalse(r['migrated']); self.assertEqual(json.loads((self.root / 'management/project.json').read_text())['templateVersion'], '1.0.0')
    def test_apply_code_backup_migrate_and_preserve_user_files(self):
        old_core = (self.root / 'management/core.py').read_bytes(); old_state = (self.root / 'management/project.json').read_bytes()
        r = upgrade_project.upgrade(self.root, apply_code=True, log=self.quiet)
        self.assertTrue(r['migrated']); b = self.root / r['backup']
        self.assertEqual((b / 'management/core.py').read_bytes(), old_core); self.assertEqual((b / 'project.json').read_bytes(), old_state)
        self.assertEqual((self.root / 'management/core.py').read_bytes(), (BASE / 'template/management/core.py').read_bytes())
        d = json.loads((self.root / 'management/project.json').read_text())
        self.assertEqual(d['templateVersion'], '1.1.0'); self.assertEqual(d['revision'], json.loads(old_state)['revision'] + 1)
        self.assertIn('模板升级', d['history'][-1]['action'])
        self.assertEqual((self.root / 'AGENTS.md').read_text(), '用户自定义规则'); self.assertEqual((self.root / '30-work/用户工作.txt').read_text(), '不要动')
        again = upgrade_project.upgrade(self.root, apply_code=True, log=self.quiet)
        self.assertEqual(again['added'] + again['codeChanged'], []); self.assertFalse(again['migrated'])
    def test_refuses_when_locked(self):
        (self.root / 'management/.server.lock').write_text('123')
        with self.assertRaises(ValueError): upgrade_project.upgrade(self.root, log=self.quiet)

class CliTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.root = make_project(self.t.name); as_current(self.root)
        shutil.copy2(self.root / '30-work/window-v002.svg', self.root / '30-work/window-v003.svg')
        (self.root / '40-review/accepted/V003.md').write_text('通过')
    def tearDown(self): self.t.cleanup()
    def run_cli(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf): code = cli.main(['--project', str(self.root), '--json', *args])
        return code, (json.loads(buf.getvalue()) if buf.getvalue().strip() else None)
    def state(self): return json.loads((self.root / 'management/project.json').read_text())
    def test_full_flow_offline(self):
        rev = self.state()['revision']
        self.assertEqual(self.run_cli('add-task', '--title', 'CLI 任务')[0], 0)
        code, out = self.run_cli('add-version', '--task', 'T012', '--path', '30-work/window-v003.svg', '--label', '第三版')
        self.assertEqual((code, out['id'], out['via']), (0, 'V003', 'offline-lock'))
        self.assertEqual(self.run_cli('submit-review', '--version', 'V003')[0], 0)
        self.assertEqual(self.run_cli('review', '--version', 'V003', '--result', 'pass', '--issues', 'ok')[0], 1)  # 缺证据
        self.assertEqual(self.run_cli('review', '--version', 'V003', '--result', 'pass', '--issues', 'ok', '--evidence', '40-review/accepted/V003.md')[0], 0)
        self.assertEqual(self.run_cli('add-deliverable', '--version', 'V003', '--path', '30-work/window-v003.svg', '--criteria', 'c', '--accepted')[0], 0)
        d = self.state(); self.assertEqual(d['revision'], rev + 5)
        self.assertTrue(all(h['action'].startswith('CLI：') for h in d['history'][-5:]))
        self.assertEqual(len(list((self.root / 'management/recovery').glob('r*.json'))), 5)
        self.assertFalse((self.root / 'management/.server.lock').exists())
        code, st = self.run_cli('status'); self.assertIn('V003', ''.join(st['versions']))
    def test_validation_and_immutability(self):
        self.assertEqual(self.run_cli('add-version', '--task', 'NOPE', '--path', '30-work/window-v003.svg')[0], 1)
        self.assertEqual(self.run_cli('add-version', '--task', 'T012', '--path', '../x.svg', '--allow-missing')[0], 1)
        self.assertEqual(self.run_cli('add-version', '--task', 'T012', '--path', '30-work/missing.svg')[0], 1)
        self.assertEqual(self.run_cli('add-version', '--task', 'T012', '--id', 'V001', '--path', '30-work/window-v003.svg')[0], 1)
        self.assertEqual(self.run_cli('add-deliverable', '--version', 'V001', '--path', '30-work/window-v001.svg', '--criteria', 'c', '--accepted')[0], 1)
        self.assertEqual(self.run_cli('review', '--version', 'V002', '--result', 'reject', '--issues', 'x')[0], 1)  # 交付已验收
        self.assertEqual(self.state()['revision'], json.loads((BASE / 'example-星港窗户演示/management/project.json').read_text())['revision'])
    def test_lock_conflict_and_stale_lock(self):
        (self.root / 'management/.server.lock').write_text(json.dumps({'kind': 'cli', 'pid': 1}))
        self.assertEqual(self.run_cli('add-task', '--title', 'x')[0], 2)
        (self.root / 'management/.server.lock').write_text('4242')  # 旧版服务
        self.assertEqual(self.run_cli('add-task', '--title', 'x')[0], 1)
        (self.root / 'management/.server.lock').write_text(json.dumps({'kind': 'server', 'pid': 1, 'port': 1}))
        self.assertEqual(self.run_cli('add-task', '--title', 'x')[0], 1)
    @unittest.skipIf(NO_HTTP, '沙箱禁止监听')
    def test_uses_running_server_api(self):
        server.ROOT = self.root
        http = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler); th = threading.Thread(target=http.serve_forever, daemon=True); th.start()
        try:
            with core.project_lock(self.root, 'server'):
                core.write_lock_port(self.root, http.server_port)
                code, out = self.run_cli('add-task', '--title', '经由服务')
                self.assertEqual((code, out['via']), (0, 'server'))
            self.assertEqual(self.state()['history'][-1]['action'], '保存')
        finally: http.shutdown(); http.server_close(); th.join()

class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.root = make_project(self.t.name)
        self.d = json.loads((self.root / 'management/project.json').read_text())
        (self.root / '90-tmp/T013_试渲染缓存/big.bin').write_bytes(b'x' * 5000)
        (self.root / "90-tmp/T013_试渲染缓存/it's %odd%.log").write_text('q')
    def tearDown(self): self.t.cleanup()
    def test_sorted_and_totals(self):
        pv = core.preview(self.d, self.root); sizes = [i['bytes'] for i in pv['items']]
        self.assertEqual(sizes, sorted(sizes, reverse=True))
        s = pv['summary']; self.assertEqual(s['total']['bytes'], sum(sizes))
        self.assertEqual(sum(c['bytes'] for c in s['categories'].values()), s['total']['bytes'])
        self.assertEqual(s['total']['eligibleBytes'], sum(i['bytes'] for i in pv['items'] if i['eligible']))
        self.assertEqual(pv['items'][0]['fileDetails'][0]['path'], '90-tmp/T013_试渲染缓存/big.bin')
    def test_script_excludes_blocked_requires_confirmation_never_runs(self):
        r = core.cleanup_script(self.d, self.root, '20261022')
        self.assertEqual(r['sh'], '90-tmp/cleanup-20261022.sh'); self.assertFalse(r['executed'])
        sh = (self.root / r['sh']).read_text(); bat = (self.root / r['bat']).read_text(encoding='utf8')
        self.assertIn('big.bin', sh); self.assertNotIn('对比说明', sh); self.assertIn('DELETE', sh); self.assertIn('DELETE', bat)
        self.assertTrue((self.root / '90-tmp/T013_试渲染缓存/big.bin').exists())  # 未执行
        self.assertFalse(os.access(self.root / r['sh'], os.X_OK)); self.assertIn("it's %odd%.log", r['batSkipped'][0])
        r2 = core.cleanup_script(self.d, self.root, '20261022'); self.assertEqual(r2['sh'], '90-tmp/cleanup-20261022-2.sh')
        # 不输入 DELETE：不删除
        subprocess.run(['sh', str(self.root / r['sh'])], input='no\n', text=True, capture_output=True)
        self.assertTrue((self.root / '90-tmp/T013_试渲染缓存/big.bin').exists())
        # 输入 DELETE：只删列出的文件，被阻止的审核包仍在，特殊字符路径正确处理
        subprocess.run(['sh', str(self.root / r['sh'])], input='DELETE\n', text=True, capture_output=True)
        self.assertFalse((self.root / '90-tmp/T013_试渲染缓存/big.bin').exists()); self.assertFalse((self.root / "90-tmp/T013_试渲染缓存/it's %odd%.log").exists())
        self.assertTrue((self.root / '40-review/T012_窗户玻璃调整/对比说明.md').exists()); self.assertTrue((self.root / '90-tmp/T013_试渲染缓存').is_dir())
    def test_no_eligible_no_script(self):
        self.d['batches'][1]['status'] = '待确认'
        with self.assertRaises(ValueError): core.cleanup_script(self.d, self.root)

@unittest.skipIf(NO_HTTP, '沙箱禁止监听')
class FileServingTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.root = make_project(self.t.name); server.ROOT = self.root
        (self.root / 'secret.txt').write_text('s'); (self.root / '30-work/link.svg').symlink_to(self.root / '30-work/window-v001.svg')
        Path(self.t.name, 'outside.png').write_bytes(b'png')
        self.http = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler); self.th = threading.Thread(target=self.http.serve_forever, daemon=True); self.th.start()
        self.url = 'http://127.0.0.1:' + str(self.http.server_port)
    def tearDown(self): self.http.shutdown(); self.http.server_close(); self.th.join(); self.t.cleanup()
    def get(self, path):
        try:
            with urllib.request.urlopen(self.url + path) as r: return r.status, r.headers, r.read()
        except urllib.error.HTTPError as e: return e.code, e.headers, b''
    def test_serves_images_and_blocks_others(self):
        from urllib.parse import quote
        code, headers, body = self.get('/files/' + quote('30-work/window-v001.svg'))
        self.assertEqual(code, 200); self.assertEqual(headers['Content-Type'], 'image/svg+xml'); self.assertIn('sandbox', headers['Content-Security-Policy'])
        self.assertEqual(body, (self.root / '30-work/window-v001.svg').read_bytes())
        for bad in ('../outside.png', '%2e%2e/outside.png', '30-work/%2e%2e/%2e%2e/outside.png', '/etc/passwd', '30-work/link.svg', 'management/.server.lock', 'secret.txt', 'management/project.json', '30-work/nope.png', 'C:%2fx.png'):
            self.assertIn(self.get('/files/' + bad)[0], (400, 403, 404, 415), bad)
        req = urllib.request.Request(self.url + '/files/30-work/window-v001.svg', method='PUT')
        with self.assertRaises(urllib.error.HTTPError): urllib.request.urlopen(req)
    def test_cleanup_script_endpoint(self):
        got = json.load(urllib.request.urlopen(self.url + '/api/project'))
        req = urllib.request.Request(self.url + '/api/cleanup-script', json.dumps({'etag': got['etag']}).encode(), {'Content-Type': 'application/json', 'X-Project-Token': got['token']})
        out = json.load(urllib.request.urlopen(req)); self.assertTrue((self.root / out['sh']).exists()); self.assertFalse(out['executed'])
        req = urllib.request.Request(self.url + '/api/cleanup-script', b'{}', {'Content-Type': 'application/json'})
        with self.assertRaises(urllib.error.HTTPError) as e: urllib.request.urlopen(req)
        self.assertEqual(e.exception.code, 403)

if __name__ == '__main__': unittest.main(verbosity=2)
