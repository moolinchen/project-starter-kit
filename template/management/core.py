"""工具无关状态验证与安全预览。仅使用 Python 标准库。"""
import copy
import hashlib
import json
import os
import re
import secrets
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

TEMPLATE_VERSION = '1.1.0'
# 1.0.0 与 1.1.0 的 project.json 字段完全相同；保留旧值以便未迁移数据仍可读。
SUPPORTED_TEMPLATE_VERSIONS = ('1.0.0', '1.1.0')
IMAGE_TYPES = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.svg': 'image/svg+xml', '.gif': 'image/gif'}

COLLECTIONS = ('tasks', 'versions', 'reviews', 'deliveries', 'settlements', 'batches', 'seals', 'history')
FIELDS = {
 'tasks': ('id','title','status','blocker','batchId'),
 'versions': ('id','taskId','label','paths','note'),
 'reviews': ('id','versionId','status','issues','evidence'),
 'deliveries': ('id','versionId','path','criteria','status'),
 'settlements': ('id','summary','amount','currency','evidence','note'),
 'batches': ('id','purpose','source','paths','retained','status','blocker','unique','running'),
}

def path_check(root, value, require_exists=False):
 if not isinstance(value,str) or not value or '\\' in value or '\x00' in value or ':' in value:
  raise ValueError('路径必须是项目内相对路径，使用 / 分隔')
 p=PurePosixPath(value)
 if p.is_absolute() or any(x in ('..','.') for x in value.split('/')) or any(not x for x in value.split('/')):
  raise ValueError('禁止绝对路径、空段、. 或 ..：'+value)
 current=Path(root)
 for part in p.parts:
  current=current/part
  if current.is_symlink(): raise ValueError('禁止符号链接：'+value)
 if require_exists and not current.exists(): raise ValueError('路径不存在：'+value)
 return current

def lines(value):
 return [v.strip() for v in value.splitlines() if v.strip()]

def validate(data, root):
 if not isinstance(data,dict): raise ValueError('项目数据必须是对象')
 if data.get('schemaVersion')!=1 or data.get('templateVersion') not in SUPPORTED_TEMPLATE_VERSIONS: raise ValueError('不支持的数据或模板版本；请手动迁移')
 if type(data.get('revision')) is not int or data['revision']<0: raise ValueError('revision 必须为非负整数')
 p=data.get('project')
 if not isinstance(p,dict) or not all(isinstance(p.get(k),str) for k in ('name','scope','acceptance','next','kind')) or not p['name'].strip(): raise ValueError('项目名称必填，项目描述字段必须是文本')
 for key in COLLECTIONS:
  if not isinstance(data.get(key),list): raise ValueError(key+' 必须是数组')
  if len(data[key])>10000: raise ValueError('记录过多')
  ids=[]
  for row in data[key]:
   if not isinstance(row,dict) or not isinstance(row.get('id'),str) or not re.fullmatch(r'[A-Za-z0-9_\-\u4e00-\u9fff]{1,100}',row['id']): raise ValueError(key+' 编号无效')
   ids.append(row['id'])
   for f in FIELDS.get(key,()):
    if f in ('unique','running'):
     if type(row.get(f)) is not bool: raise ValueError(f+' 必须为布尔值')
    elif not isinstance(row.get(f),str): raise ValueError(key+'.'+f+' 必须为文本')
   for f in ('paths','evidence','retained'):
    if f in row:
     for v in lines(row[f]): path_check(root,v)
   if 'path' in row: path_check(root,row['path'])
  if len(ids)!=len(set(ids)): raise ValueError(key+' 编号重复')
 lookup=lambda k:{r['id']:r for r in data[k]}
 tasks,versions,batches=lookup('tasks'),lookup('versions'),lookup('batches')
 enums={'tasks':('status',('待办','进行中','阻塞','完成')),'reviews':('status',('待审核','通过','退回')),'deliveries':('status',('待验收','已验收')),'batches':('status',('进行中','待确认','可清理'))}
 for key,(field,allowed) in enums.items():
  for row in data[key]:
   if row[field] not in allowed: raise ValueError(key+' 状态无效')
 for row in data['tasks']:
  if not row['title'].strip(): raise ValueError('任务标题必填')
  if row['batchId'] and row['batchId'] not in batches: raise ValueError('任务批次不存在')
 for row in data['versions']:
  if row['taskId'] not in tasks or not row['label'].strip() or not lines(row['paths']): raise ValueError('版本必须绑定任务、名称和工作文件')
 for row in data['reviews']+data['deliveries']:
  if row['versionId'] not in versions: raise ValueError('引用的具体版本不存在')
 review_versions=[r['versionId'] for r in data['reviews']]
 if len(review_versions)!=len(set(review_versions)): raise ValueError('一个版本只保留一条当前审核记录；历史在 history 中')
 for row in data['reviews']:
  if row['status']=='通过' and (not lines(row['evidence']) or not row['issues'].strip()): raise ValueError('审核通过需要结论和证据路径')
 for row in data['deliveries']:
  if not row['criteria'].strip(): raise ValueError('交付验收标准必填')
  if row['status']=='已验收' and not passed(data,row['versionId']): raise ValueError('交付验收前必须通过该版本审核')
 for row in data['settlements']:
  if not row['summary'].strip(): raise ValueError('结算汇总必填')
  if row['amount']:
   try:
    from decimal import Decimal
    amount=Decimal(row['amount'])
    if not amount.is_finite() or amount<0: raise ValueError()
   except Exception: raise ValueError('费用须为非负有限数字，或留空')
 for row in data['batches']:
  if not re.fullmatch(r'T[0-9]{3,}_[A-Za-z0-9_\-\u4e00-\u9fff]+',row['id']): raise ValueError('批次编号格式：T012_窗户玻璃调整')
  if not row['purpose'].strip() or not row['source'].strip() or not lines(row['paths']): raise ValueError('批次必须填写用途、来源/重建方式、具体路径')
  for v in lines(row['paths']):
   if not (v.startswith('40-review/'+row['id']+'/') or v=='40-review/'+row['id'] or v.startswith('90-tmp/'+row['id']+'/') or v=='90-tmp/'+row['id']): raise ValueError('批次路径必须在同编号的 40-review 或 90-tmp 下')
  if row['status']=='可清理' and (row['unique'] or row['running'] or row['blocker'].strip() or not lines(row['retained'])): raise ValueError('唯一副本、运行中、有阻碍或没有保留成果的批次不可清理')
 for seal in data['seals']:
  if not isinstance(seal.get('snapshot'),dict) or not isinstance(seal.get('createdAt'),str): raise ValueError('封版记录缺少快照/时间')
  snap=seal['snapshot']
  if not all(isinstance(snap.get(k),list) for k in ('versions','deliveries','reviews','settlements')): raise ValueError('封版快照结构无效')
 for item in preview(data,root)['items']:
  batch=next(b for b in data['batches'] if b['id']==item['batchId'])
  if batch['status']=='可清理' and not item['eligible']:
   raise ValueError('此批次不能标记可清理：'+item['path']+'；'+'；'.join(item['reasons']))
 return data

def passed(data, version):
 return any(r['versionId']==version and r['status']=='通过' for r in data['reviews'])

def seal_check(data,root):
 if not data['project']['scope'].strip() or not data['project']['acceptance'].strip(): raise ValueError('封版前请填写范围与验收标准')
 if not data['tasks'] or any(t['status']!='完成' for t in data['tasks']): raise ValueError('封版前所有任务须完成')
 if not data['deliveries'] or any(d['status']!='已验收' for d in data['deliveries']): raise ValueError('封版前须有交付清单且全部验收')
 if not data['settlements']: raise ValueError('封版前须填写结项汇总；费用可留空')
 if any(b['status']=='进行中' or b['running'] for b in data['batches']): raise ValueError('仍有进行中的材料批次')
 for d in data['deliveries']:
  if not passed(data,d['versionId']): raise ValueError('封版交付版本未通过审核')
  path_check(root,d['path'],True)
  v=next(v for v in data['versions'] if v['id']==d['versionId'])
  for p in lines(v['paths']): path_check(root,p,True)
  review=next(r for r in data['reviews'] if r['versionId']==v['id'])
  for p in lines(review['evidence']): path_check(root,p,True)

def transition(old,new):
 # 版本登记和封版历史不可改写；新版本必须取得独立审核。
 oldv={v['id']:v for v in old['versions']}; newv={v['id']:v for v in new['versions']}
 for id,v in oldv.items():
  if newv.get(id)!=v: raise ValueError('已登记版本不可改写或移除，请登记新版本')
 if new['seals']!=old['seals']: raise ValueError('封版只能使用专用封版操作，且不可改写历史')
 if new['history']!=old['history']: raise ValueError('历史记录不可手动改写')


def references(data):
 refs=[]
 for key in ('versions','reviews','deliveries','settlements'):
  for row in data[key]:
   for field in ('paths','path','evidence'):
    for p in lines(row.get(field,'')): refs.append((p,key+'/'+row['id']))
 for seal in data['seals']:
  snap=seal['snapshot']
  for key in ('versions','reviews','deliveries','settlements'):
   for row in snap.get(key,[]):
    for field in ('paths','path','evidence'):
     for p in lines(row.get(field,'')): refs.append((p,'封版/'+seal['id']))
 for batch in data['batches']:
  for p in lines(batch['retained']): refs.append((p,'批次保留/'+batch['id']))
 return refs

def overlap(a,b): return a==b or a.startswith(b+'/') or b.startswith(a+'/')

def preview(data,root):
 refs=references(data); result=[]
 for batch in data['batches']:
  for value in lines(batch['paths']):
   reasons=[]; count=0; size=0; files=[]
   if batch['status']!='可清理': reasons.append('批次未确认为可清理')
   if batch['unique']: reasons.append('可能是唯一副本')
   if batch['running']: reasons.append('材料仍在运行中')
   if batch['blocker']: reasons.append('阻碍：'+batch['blocker'])
   if not lines(batch['retained']): reasons.append('未登记保留成果')
   for p in lines(batch['retained']):
    try: path_check(root,p,True)
    except ValueError as e: reasons.append('保留成果不可用：'+str(e))
    if overlap(value,p): reasons.append('清理范围包含保留成果：'+p)
   for p,ref in refs:
    if overlap(value,p): reasons.append('仍被引用：'+ref+' → '+p)
   try:
    target=path_check(root,value,True)
    # 不跟随符号链接；逐层遍历，遇链接整批阻止。
    pending=[target]
    while pending:
     p=pending.pop()
     if p.is_symlink(): reasons.append('含符号链接：'+str(p.relative_to(root))); continue
     if p.is_dir(): pending.extend(sorted(p.iterdir()))
     elif p.is_file():
      count+=1; size+=p.stat().st_size; files.append(str(p.relative_to(root)))
     else: reasons.append('非普通文件：'+str(p.relative_to(root)))
   except (ValueError,OSError) as e: reasons.append(str(e))
   details=sorted(([f,(Path(root)/f).stat().st_size] for f in files),key=lambda x:(-x[1],x[0]))
   result.append({'batchId':batch['id'],'path':value,'category':value.split('/')[0],'fileCount':count,'bytes':size,'human':human(size),'files':sorted(files),'fileDetails':[{'path':f,'bytes':b} for f,b in details],'eligible':not reasons,'reasons':reasons,'basis':batch['purpose']+'；重建/来源：'+batch['source'],'retained':lines(batch['retained'])})
 # 重叠候选不能作为可直接执行的清单。
 for i,row in enumerate(result):
  if any(i!=j and overlap(row['path'],other['path']) for j,other in enumerate(result)):
   row['eligible']=False; row['reasons'].append('与其他清理范围重叠，请合并批次路径')
 result.sort(key=lambda r:(-r['bytes'],r['path']))
 return {'mode':'preview-only','items':result,'summary':summarize(result),'notice':'仅为当前时刻预览，不执行删除；人工操作前重新检查引用、运行状态及备份。'}

def human(n):
 for unit in ('B','KB','MB','GB'):
  if n<1024 or unit=='GB': return (str(n) if unit=='B' else '%.1f'%n)+' '+unit
  n/=1024

def summarize(items):
 # 按分类（40-review / 90-tmp）汇总；重叠范围本身已被阻止，总计可能重复计算重叠部分。
 cats={}
 total={'items':0,'files':0,'bytes':0,'eligibleItems':0,'eligibleFiles':0,'eligibleBytes':0}
 for r in items:
  c=cats.setdefault(r['category'],{k:0 for k in total})
  for t in (c,total):
   t['items']+=1; t['files']+=r['fileCount']; t['bytes']+=r['bytes']
   if r['eligible']: t['eligibleItems']+=1; t['eligibleFiles']+=r['fileCount']; t['eligibleBytes']+=r['bytes']
 for t in list(cats.values())+[total]: t['human']=human(t['bytes']); t['eligibleHuman']=human(t['eligibleBytes'])
 return {'categories':dict(sorted(cats.items(),key=lambda kv:-kv[1]['bytes'])),'total':total}

# ---------- 删除脚本（只生成，不执行） ----------
BAT_UNSAFE=set('%!^&|<>"')

def _sh_quote(v): return "'"+v.replace("'","'\\''")+"'"

def cleanup_script(data,root,today=None):
 """把当前预览中「可人工复核」的确切文件写成 90-tmp/cleanup-YYYYMMDD.sh/.bat；被阻止项不写入；工具从不执行它。"""
 root=Path(root); validate(data,root); pv=preview(data,root)
 files=[]; excluded=[]
 for item in pv['items']:
  if not item['eligible']: excluded.append({'path':item['path'],'reasons':item['reasons']}); continue
  for d in item['fileDetails']: files.append((d['path'],d['bytes']))
 if not files: raise ValueError('当前没有可人工复核的清理文件；被阻止项不会写入脚本')
 day=today or datetime.now().strftime('%Y%m%d')
 tmp=path_check(root,'90-tmp',True); n=1
 while True:
  stem='cleanup-'+day+('' if n==1 else '-'+str(n))
  if not (tmp/(stem+'.sh')).exists() and not (tmp/(stem+'.bat')).exists(): break
  n+=1
 total=sum(b for _,b in files)
 head='项目清理脚本（由预览生成于 '+datetime.now().isoformat(timespec='seconds')+'）；共 '+str(len(files))+' 个文件，'+human(total)
 sh=['#!/bin/sh','# '+head,'# 本工具从不执行此脚本。运行前请重新生成预览并核对清单；只删除下列普通文件，不删除目录。','set -u','cd "$(dirname "$0")/.." || exit 1','echo '+_sh_quote(head),'cat <<\'LIST\'']
 sh+=[p+'  ('+human(b)+')' for p,b in files]+['LIST','printf "确认删除以上文件请输入 DELETE：" ','read answer','if [ "$answer" != "DELETE" ]; then echo "已取消，未删除任何文件"; exit 1; fi']
 for p,b in files:
  q=_sh_quote(p)
  sh.append('if [ -f '+q+' ] && [ ! -L '+q+' ]; then rm -- '+q+' && echo "已删除 "'+q+'; else echo "跳过（不存在或非普通文件）："'+q+'; fi')
 bat_files=[(p,b) for p,b in files if not (set(p)&BAT_UNSAFE)]
 skipped=[p for p,b in files if set(p)&BAT_UNSAFE]
 bat=['@echo off','chcp 65001 >nul','setlocal DisableDelayedExpansion','rem '+head,'rem 本工具从不执行此脚本。运行前请重新生成预览并核对清单；只删除下列普通文件。','cd /d "%~dp0.." || exit /b 1']
 bat+=['echo '+p.replace('/','\\') for p,_ in bat_files]
 if skipped: bat+=['echo 含特殊字符的 '+str(len(skipped))+' 个文件未写入此脚本，请人工处理']
 bat+=['set /p answer=确认删除以上文件请输入 DELETE：','if not "%answer%"=="DELETE" (echo 已取消，未删除任何文件 & exit /b 1)']
 for p,_ in bat_files:
  w=p.replace('/','\\'); bat.append('if exist "'+w+'" del /q "'+w+'"')
 shp=tmp/(stem+'.sh'); batp=tmp/(stem+'.bat')
 with open(shp,'x',encoding='utf8',newline='\n') as f: f.write('\n'.join(sh)+'\n')
 with open(batp,'x',encoding='utf8',newline='') as f: f.write('\r\n'.join(bat)+'\r\n')
 return {'sh':str(shp.relative_to(root)),'bat':str(batp.relative_to(root)),'fileCount':len(files),'bytes':total,'human':human(total),'excluded':excluded,'batSkipped':skipped,'executed':False,'notice':'脚本未执行。运行需输入 DELETE 确认；被阻止的项目未写入。'}

# ---------- 统一写入路径（服务、CLI、升级工具共用） ----------
STATE_LOCK=threading.Lock()
class Conflict(Exception): pass

def stamp(): return datetime.now(timezone.utc).isoformat()
def fingerprint(raw): return hashlib.sha256(raw).hexdigest()

def read_state(root):
 root=Path(root); path_check(root,'management/project.json',True)
 raw=(root/'management/project.json').read_bytes()
 data=json.loads(raw); validate(data,root)
 return data,fingerprint(raw)

def atomic(path,raw):
 fd,name=tempfile.mkstemp(prefix='.save-',dir=str(path.parent))
 try:
  with os.fdopen(fd,'wb') as f: f.write(raw); f.flush(); os.fsync(f.fileno())
  os.replace(name,path)
 finally:
  if os.path.exists(name): os.unlink(name)

def persist(root,data,oldraw):
 # 备份是恢复文件，不是第二个动态数据源。
 root=Path(root); backup=path_check(root,'management/recovery')
 backup.mkdir(exist_ok=True)
 name='r'+str(json.loads(oldraw)['revision'])+'-'+secrets.token_hex(4)+'.json'
 atomic(backup/name,oldraw)
 atomic(root/'management/project.json',(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf8'))

def commit(root,new,etag,seal=False,action=None):
 root=Path(root)
 with STATE_LOCK:
  old,current=read_state(root)
  if etag!=current: raise Conflict('磁盘数据已变化，请先导出未保存草稿，再重新载入合并')
  validate(new,root)
  if new['revision']!=old['revision']: raise Conflict('revision 已变化')
  transition(old,new)
  if seal:
   if new!=old: raise ValueError('请先保存修改，再封版')
   seal_check(new,root)
   snap={k:copy.deepcopy(new[k]) for k in ('project','tasks','versions','reviews','deliveries','settlements','batches')}
   if new['seals'] and new['seals'][-1]['snapshot']==snap: raise ValueError('当前状态已封版，无需重复操作')
   new['seals'].append({'id':'S'+str(len(new['seals'])+1).zfill(3),'createdAt':stamp(),'snapshot':snap})
  elif new==old: return {'data':old,'etag':current,'unchanged':True}
  new['revision']=old['revision']+1
  new['history']=copy.deepcopy(old['history'])+[{'id':'H'+secrets.token_hex(8),'createdAt':stamp(),'action':action or ('封版' if seal else '保存'),'fromRevision':old['revision'],'toRevision':new['revision']}]
  # 防止非合作外部写入发生在读取与落盘之间。
  raw=(root/'management/project.json').read_bytes()
  if fingerprint(raw)!=current: raise Conflict('保存前磁盘已变化')
  persist(root,new,raw)
  saved,etag=read_state(root); return {'data':saved,'etag':etag}

def migrate(root,target=TEMPLATE_VERSION):
 """仅升级 templateVersion（1.0.0→1.1.0 无字段变化）；先备份，追加 history。"""
 root=Path(root)
 with STATE_LOCK:
  raw=(root/'management/project.json').read_bytes(); old=json.loads(raw); validate(old,root)
  if old['templateVersion']==target: return None
  new=copy.deepcopy(old); new['templateVersion']=target; new['revision']=old['revision']+1
  new['history']=old['history']+[{'id':'H'+secrets.token_hex(8),'createdAt':stamp(),'action':'模板升级 '+old['templateVersion']+'→'+target,'fromRevision':old['revision'],'toRevision':new['revision']}]
  validate(new,root); persist(root,new,raw); return new

LOCK_NAME='management/.server.lock'
def lock_info(root):
 """返回锁内容：服务写入 JSON {kind,pid,port}；1.0.0 服务只写 PID。"""
 p=Path(root)/LOCK_NAME
 if not p.exists(): return None
 text=p.read_text(encoding='utf8',errors='replace').strip()
 try:
  info=json.loads(text)
  if isinstance(info,dict): return info
 except ValueError: pass
 return {'kind':'unknown','pid':text}

@contextmanager
def project_lock(root,kind='cli',port=None):
 """与服务共用同一把项目锁文件，阻止服务与离线写入同时进行。"""
 root=Path(root); path_check(root,LOCK_NAME); lock=root/LOCK_NAME
 try: fd=os.open(str(lock),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 except FileExistsError: raise Conflict('项目锁已存在（management/.server.lock）：服务或其他写入正在进行。确认旧进程已退出后再人工移除。')
 try:
  with os.fdopen(fd,'w') as f: json.dump({'kind':kind,'pid':os.getpid(),'port':port},f)
  yield lock
 finally: lock.unlink(missing_ok=True)

def write_lock_port(root,port):
 lock=Path(root)/LOCK_NAME
 atomic(lock,json.dumps({'kind':'server','pid':os.getpid(),'port':port}).encode())

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description='校验项目 JSON 和路径（不修改文件）')
 parser.add_argument('root',nargs='?',default=str(Path(__file__).resolve().parent.parent))
 parser.add_argument('--preview',action='store_true')
 parser.add_argument('--write-script',action='store_true',help='在 90-tmp 生成需手动输入确认的删除脚本（不执行）')
 args=parser.parse_args(); root=Path(args.root).resolve()
 try:
  data=json.loads((root/'management/project.json').read_text(encoding='utf8')); validate(data,root)
  if args.write_script: print(json.dumps(cleanup_script(data,root),ensure_ascii=False,indent=2))
  else: print(json.dumps(preview(data,root),ensure_ascii=False,indent=2) if args.preview else '校验通过')
 except Exception as e:
  print('校验失败：'+str(e)); raise SystemExit(1)
