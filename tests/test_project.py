import copy, importlib.util, json, os, shutil, subprocess, sys, tempfile, threading, unittest, urllib.request, urllib.error
from pathlib import Path
BASE=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(BASE/'template/management'));sys.path.insert(0,str(BASE/'tools'))
import core, server, init_project

class ProjectTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='project-kit-test-');self.root=Path(self.temp.name)/'project';shutil.copytree(BASE/'example-星港窗户演示',self.root,ignore=shutil.ignore_patterns('__pycache__','.server.lock','recovery'))
  server.ROOT=self.root;self.d=json.loads((self.root/'management/project.json').read_text());self.d['seals']=[];self.d['history']=[];self.d['revision']=0
  (self.root/'management/project.json').write_text(json.dumps(self.d,ensure_ascii=False))
 def tearDown(self):self.temp.cleanup()
 def save(self,d=None,etag=None):return server.update({'data':copy.deepcopy(d or self.d),'etag':etag or server.read()[1]})
 def test_save_reopen_backup_and_noop(self):
  self.d['project']['next']='重新载入后应存在';out=self.save();self.assertEqual(out['data']['revision'],1)
  self.assertEqual(json.loads((self.root/'management/project.json').read_text())['project']['next'],'重新载入后应存在')
  self.assertEqual(len(list((self.root/'management/recovery').glob('*.json'))),1)
  self.assertTrue(self.save(out['data'])['unchanged'])
 def test_conflict_and_duplicate_request(self):
  etag=server.read()[1];self.d['project']['next']='A';self.save(etag=etag)
  with self.assertRaises(server.Conflict):self.save(etag=etag)
 def test_external_edit_conflict(self):
  etag=server.read()[1];(self.root/'management/project.json').write_text(json.dumps(self.d)+' ')
  with self.assertRaises(server.Conflict):self.save(etag=etag)
 def test_new_version_never_inherits_pass(self):
  self.d['versions'].append({'id':'V003','taskId':'T012','label':'第三版','paths':'30-work/window-v003.svg','note':''})
  self.assertFalse(core.passed(self.d,'V003'));self.d['deliveries'][0]['versionId']='V003'
  with self.assertRaises(ValueError):self.save()
 def test_version_immutable(self):
  self.d['versions'][0]['label']='覆盖旧版'
  with self.assertRaises(ValueError):self.save()
 def test_review_and_delivery_validation(self):
  self.d['reviews'][1]['evidence']=''
  with self.assertRaises(ValueError):core.validate(self.d,self.root)
  self.d['reviews'][1]['status']='退回'
  with self.assertRaises(ValueError):core.validate(self.d,self.root)
 def test_path_escape_absolute_windows_and_symlink(self):
  for p in ('../outside','/tmp/a','C:/a','30-work/../a','30-work//a','30-work\\a'):
   with self.assertRaises(ValueError):core.path_check(self.root,p)
  (self.root/'90-tmp/link').symlink_to('/tmp',target_is_directory=True)
  with self.assertRaises(ValueError):core.path_check(self.root,'90-tmp/link/anything')
 def test_cleanup_exact_counts_and_references(self):
  out=core.preview(self.d,self.root)['items'];review,tmp=out
  self.assertFalse(review['eligible']);self.assertTrue(any('引用' in r for r in review['reasons']))
  self.assertTrue(tmp['eligible']);self.assertEqual(tmp['fileCount'],1);self.assertEqual(tmp['files'],['90-tmp/T013_试渲染缓存/render.log']);self.assertEqual(tmp['bytes'],(self.root/tmp['files'][0]).stat().st_size)
 def test_cleanup_blocks_unique_running_retained_missing_links(self):
  b=self.d['batches'][1]
  for key in ('unique','running'):
   b[key]=True
   with self.assertRaises(ValueError):core.validate(self.d,self.root)
   b[key]=False
  b['retained']='30-work/missing.svg';self.assertFalse(core.preview(self.d,self.root)['items'][1]['eligible'])
  b['retained']='30-work/window-v002.svg'
  (self.root/'90-tmp/T013_试渲染缓存/link').symlink_to('/tmp',target_is_directory=True)
  self.assertFalse(core.preview(self.d,self.root)['items'][1]['eligible'])
 def test_cleanup_overlap_and_keep_inside(self):
  b=self.d['batches'][1];b['paths']+='\n90-tmp/T013_试渲染缓存/render.log'
  out=core.preview(self.d,self.root)['items'];self.assertFalse(out[1]['eligible']);self.assertFalse(out[2]['eligible'])
  b['paths']='90-tmp/T013_试渲染缓存';b['retained']='90-tmp/T013_试渲染缓存/render.log'
  self.assertFalse(core.preview(self.d,self.root)['items'][1]['eligible'])
 def test_seal_validation_snapshot_duplicate_history(self):
  etag=server.read()[1];out=server.update({'data':copy.deepcopy(self.d),'etag':etag},True)
  self.assertEqual(out['data']['seals'][0]['snapshot']['deliveries'][0]['versionId'],'V002')
  with self.assertRaises(ValueError):server.update({'data':out['data'],'etag':out['etag']},True)
  change=copy.deepcopy(out['data']);change['seals']=[]
  with self.assertRaises(ValueError):self.save(change)
  change=copy.deepcopy(out['data']);change['project']['next']='继续新阶段';saved=self.save(change)
  self.assertEqual(saved['data']['seals'][0],out['data']['seals'][0])
 def test_seal_missing_file_and_incomplete(self):
  d=copy.deepcopy(self.d);d['tasks'][0]['status']='进行中'
  with self.assertRaises(ValueError):core.seal_check(d,self.root)
  (self.root/'80-deliver/window-final.svg').unlink()
  with self.assertRaises(ValueError):core.seal_check(self.d,self.root)
 def test_import_export_roundtrip(self):
  roundtrip=json.loads(json.dumps(self.d,ensure_ascii=False));core.validate(roundtrip,self.root);self.assertEqual(roundtrip,self.d)
 def test_init_nonempty_does_not_overwrite(self):
  target=Path(self.temp.name)/'existing';target.mkdir();(target/'AGENTS.md').write_text('原规则');(target/'旧工程').mkdir();(target/'旧工程/a.txt').write_text('旧材料')
  with self.assertRaises(ValueError):init_project.initialize(target,'接入')
  mapping={'reviewedExistingRules':True,'directories':{'旧工程':'30-work 原有工程'}}
  plan=init_project.initialize(target,'接入',mapping,True);self.assertIn('AGENTS.md',plan['preserved']);self.assertFalse((target/'management').exists())
  init_project.initialize(target,'接入',mapping);self.assertEqual((target/'AGENTS.md').read_text(),'原规则');self.assertEqual((target/'旧工程/a.txt').read_text(),'旧材料')
  again=init_project.initialize(target,'另一个名字',mapping);self.assertEqual(again['added'],[]);self.assertEqual(json.loads((target/'management/project.json').read_text())['project']['name'],'接入')
 def test_referenced_batch_cannot_be_marked_cleanable(self):
  self.d['batches'][0]['status']='可清理';self.d['batches'][0]['blocker']=''
  with self.assertRaises(ValueError):core.validate(self.d,self.root)
 def test_init_symlink_no_write(self):
  target=Path(self.temp.name)/'link';target.symlink_to(self.root,target_is_directory=True)
  with self.assertRaises(ValueError):init_project.initialize(target,'bad')
 def test_template_example_isolation(self):
  blank=json.loads((BASE/'template/management/project.json').read_text());example=json.loads((BASE/'example-星港窗户演示/management/project.json').read_text())
  self.assertFalse(blank['tasks']);self.assertTrue(example['tasks']);self.assertEqual(blank['revision'],0)
 @unittest.skipIf(os.environ.get('PROJECT_KIT_NO_HTTP')=='1','当前沙箱禁止监听端口；HTTP 已在首次完整运行中通过')
 def test_http_security_save_and_no_delete(self):
  http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start();url='http://127.0.0.1:'+str(http.server_port)
  def request(path,body=None,token=True):
   headers={'Content-Type':'application/json'}
   if token:headers['X-Project-Token']=server.TOKEN
   req=urllib.request.Request(url+path,json.dumps(body).encode() if body else None,headers)
   return json.load(urllib.request.urlopen(req))
  try:
   loaded=request('/api/project');d=loaded['data'];d['project']['next']='HTTP 落盘'
   with self.assertRaises(urllib.error.HTTPError) as err:request('/api/save',{'data':d,'etag':loaded['etag']},False)
   self.assertEqual(err.exception.code,403)
   result=request('/api/save',{'data':d,'etag':loaded['etag']});self.assertEqual(result['data']['project']['next'],'HTTP 落盘')
   with self.assertRaises(urllib.error.HTTPError) as err:request('/api/delete',{'data':d})
   self.assertEqual(err.exception.code,404)
  finally:http.shutdown();http.server_close();thread.join()

if __name__=='__main__':unittest.main(verbosity=2)
