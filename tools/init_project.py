#!/usr/bin/env python3
"""复制独立项目；已有项目只添加缺少文件，不覆盖。"""
import argparse, json, os, shutil, sys, tempfile
from pathlib import Path
BASE=Path(__file__).resolve().parent.parent
TEMPLATE=BASE/'template'
sys.path.insert(0,str(TEMPLATE/'management'))
from core import validate

def safe_target(target):
 target=Path(os.path.abspath(os.path.expanduser(str(target))))
 for part in [target]+list(target.parents):
  if part.is_symlink() and str(part) not in ('/tmp','/var'): raise ValueError('目标及父路径不能是符号链接：'+str(part))
 target=target.resolve()
 if target==TEMPLATE or TEMPLATE in target.parents or target==BASE or BASE in target.parents: raise ValueError('请在模板包之外创建独立项目')
 if target.exists() and not target.is_dir(): raise ValueError('目标不是目录')
 return target

def initialize(target,name,mapping=None,dry_run=False):
 target=safe_target(target)
 existing=target.exists() and any(target.iterdir())
 if existing and mapping is None: raise ValueError('目标已有文件。请先检查原规范和目录，再使用 --mapping 映射 JSON；工具不会移动原文件')
 if existing:
  if not isinstance(mapping,dict) or mapping.get('reviewedExistingRules') is not True or not isinstance(mapping.get('directories'),dict) or not mapping['directories']: raise ValueError('映射须包含 reviewedExistingRules: true 及非空 directories 对象')
  from core import path_check
  for source,role in mapping['directories'].items():
   path_check(target,source,True)
   if not isinstance(role,str) or not role.strip(): raise ValueError('映射用途不能为空')
 state=target/'management/project.json'
 if state.exists(): validate(json.loads(state.read_text(encoding='utf8')),target)
 files=[];skipped=[]
 for src in sorted(TEMPLATE.rglob('*')):
  rel=src.relative_to(TEMPLATE)
  if '__pycache__' in rel.parts or src.name.startswith('.') or 'recovery' in rel.parts: continue
  dest=target/rel
  for p in [dest]+list(dest.parents):
   if p==target.parent: break
   if p.is_symlink(): raise ValueError('目标含符号链接，停止：'+str(p))
   if p!=dest and p.exists() and not p.is_dir(): raise ValueError('路径被现有文件占用：'+str(p))
  if src.is_dir():
   if dest.exists() and not dest.is_dir(): raise ValueError('目录位置已被文件占用：'+str(dest))
   continue
  if dest.exists(): skipped.append(str(rel))
  else: files.append((src,dest))
 if not dry_run:
  target.mkdir(parents=True,exist_ok=True)
  for src,dest in files:
   dest.parent.mkdir(parents=True,exist_ok=True)
   payload=src.read_bytes()
   if src==TEMPLATE/'management/project.json':
    data=json.loads(payload);data['project']['name']=name;payload=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf8')
   with dest.open('xb') as f: f.write(payload)
   shutil.copymode(src,dest)
  if existing:
   report=target/'10-plan/existing-structure-map.json'
   if not report.exists():
    with report.open('x',encoding='utf8') as f: json.dump(mapping,f,ensure_ascii=False,indent=2)
  validate(json.loads(state.read_text(encoding='utf8')),target)
 return {'target':str(target),'dryRun':dry_run,'added':[str(d.relative_to(target)) for s,d in files],'preserved':skipped,'note':'原有文件未覆盖、未搬移。若保留了旧管理代码，请人工核对与本模板的兼容性；不会自动升级。'}

def main():
 p=argparse.ArgumentParser(description='建立每项目独立的启动模板（只复制缺少文件）')
 p.add_argument('target');p.add_argument('--name',default='新项目');p.add_argument('--mapping',help='已有结构映射 JSON');p.add_argument('--dry-run',action='store_true');a=p.parse_args()
 try:
  mapping=json.loads(Path(a.mapping).read_text(encoding='utf8')) if a.mapping else None
  print(json.dumps(initialize(a.target,a.name,mapping,a.dry_run),ensure_ascii=False,indent=2))
 except Exception as e: print('初始化失败：'+str(e),file=sys.stderr);sys.exit(1)
if __name__=='__main__':main()
