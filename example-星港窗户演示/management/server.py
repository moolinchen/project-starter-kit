#!/usr/bin/env python3
"""单项目本地服务；仅监听回环地址，不执行删除。"""
import argparse, json, os, secrets, sys, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote
import core
from core import validate, preview, path_check, IMAGE_TYPES

ROOT=Path(__file__).resolve().parent.parent
TOKEN=secrets.token_urlsafe(32)
MAX_BODY=8*1024*1024
MAX_FILE=64*1024*1024

# 写入逻辑统一在 core.commit，CLI 离线写入走同一条路径。
def read(): return core.read_state(ROOT)
def update(body,seal=False): return core.commit(ROOT,body.get('data'),body.get('etag'),seal)

def project_file(rel):
 """只读提供项目内图片：拒绝绝对路径、..、符号链接、隐藏段，并确认真实路径仍在项目内。"""
 rel=unquote(rel)
 if any(part.startswith('.') for part in rel.split('/')): raise PermissionError('禁止访问隐藏文件')
 file=path_check(ROOT,rel,True)
 real=file.resolve(); root=ROOT.resolve()
 if root not in real.parents or not real.is_file(): raise PermissionError('只能读取项目内普通文件')
 ctype=IMAGE_TYPES.get(real.suffix.lower())
 if not ctype: raise LookupError('只提供图片预览（png/jpg/webp/svg/gif）')
 if real.stat().st_size>MAX_FILE: raise LookupError('文件超过 64 MiB，不在面板预览')
 return real,ctype

Conflict=core.Conflict

class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def response(self,status,data,ctype='application/json; charset=utf-8',sandbox=False):
  raw=data if isinstance(data,bytes) else json.dumps(data,ensure_ascii=False).encode('utf8')
  self.send_response(status); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(len(raw)))
  self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff')
  # 项目文件（尤其 SVG）使用沙箱 CSP，直接打开时也不能执行脚本。
  self.send_header('Content-Security-Policy',"default-src 'none'; style-src 'unsafe-inline'; sandbox" if sandbox else "default-src 'self'; img-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
  self.end_headers(); self.wfile.write(raw)
 def host_ok(self):
  return self.headers.get('Host') in ('127.0.0.1:'+str(self.server.server_port),'localhost:'+str(self.server.server_port))
 def do_GET(self):
  if not self.host_ok(): return self.response(403,{'error':'Host 不允许'})
  try:
   route=self.path.split('?')[0]
   if route=='/api/project':
    data,etag=read(); return self.response(200,{'data':data,'etag':etag,'token':TOKEN})
   if route=='/api/preview': return self.response(200,preview(read()[0],ROOT))
   if route.startswith('/files/'):
    try: file,ctype=project_file(route[len('/files/'):])
    except PermissionError as e: return self.response(403,{'error':str(e)})
    except LookupError as e: return self.response(415,{'error':str(e)})
    except ValueError as e: return self.response(404 if '不存在' in str(e) else 403,{'error':str(e)})
    return self.response(200,file.read_bytes(),ctype,True)
   assets={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/style.css':'style.css'}
   if route not in assets: return self.response(404,{'error':'未找到'})
   file=path_check(ROOT,'management/'+assets[route],True)
   ctype={'html':'text/html','js':'text/javascript','css':'text/css'}[file.suffix[1:]]+'; charset=utf-8'
   self.response(200,file.read_bytes(),ctype)
  except Exception as e: self.response(400,{'error':str(e)})
 def do_POST(self):
  if not self.host_ok() or self.headers.get('X-Project-Token')!=TOKEN: return self.response(403,{'error':'本地会话校验失败，请刷新页面'})
  if self.headers.get('Origin') not in (None,'http://127.0.0.1:'+str(self.server.server_port),'http://localhost:'+str(self.server.server_port)): return self.response(403,{'error':'禁止跨来源写入'})
  try:
   size=int(self.headers.get('Content-Length','0'))
   if not 0<size<=MAX_BODY: raise ValueError('请求为空或超过 8 MiB')
   body=json.loads(self.rfile.read(size))
   if self.path=='/api/save': result=update(body)
   elif self.path=='/api/seal': result=update(body,True)
   elif self.path=='/api/cleanup-script':
    # 只基于已保存的磁盘状态生成；从不执行脚本。
    data,etag=read()
    if body.get('etag') not in (None,etag): raise Conflict('磁盘数据已变化，请先保存或重新载入后再生成脚本')
    result=core.cleanup_script(data,ROOT)
   elif self.path=='/api/preview':
    validate(body['data'],ROOT); result=preview(body['data'],ROOT)
   else: return self.response(404,{'error':'没有该操作'})
   self.response(200,result)
  except Conflict as e: self.response(409,{'error':str(e)})
  except Exception as e: self.response(400,{'error':str(e)})

def main():
 parser=argparse.ArgumentParser(description='启动单项目中文管理面板')
 parser.add_argument('--port',type=int,default=0); parser.add_argument('--no-browser',action='store_true')
 args=parser.parse_args(); read()
 # 防止一个项目被两个服务同时持有；异常结束会留下锁，须确认旧进程已退出后人工移除。
 # SIGTERM 也走正常退出流程，释放项目锁。
 import signal
 def _term(*_): raise KeyboardInterrupt
 signal.signal(signal.SIGTERM,_term)
 try: ctx=core.project_lock(ROOT,'server'); ctx.__enter__()
 except core.Conflict: raise SystemExit('此项目已有服务锁或 CLI 正在写入。确认旧进程已退出后，删除 management/.server.lock 再启动。')
 try:
  server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
  core.write_lock_port(ROOT,server.server_port)  # 供 management/cli.py 找到正在运行的服务
  url='http://127.0.0.1:'+str(server.server_port)
  print('项目：'+str(ROOT)+'\n面板：'+url+'\n关闭：在此窗口按 Ctrl+C',flush=True)
  if not args.no_browser: webbrowser.open(url)
  try: server.serve_forever()
  except KeyboardInterrupt: pass
  finally: server.server_close()
 finally: ctx.__exit__(None,None,None)
if __name__=='__main__': main()
