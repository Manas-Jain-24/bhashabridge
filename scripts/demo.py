"""Run the local demo with dependency checks, logs, and managed child processes."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]


def available(port):
    with socket.socket() as probe:
        try: probe.bind(('127.0.0.1',port)); return True
        except OSError: return False


def stop(child):
    if child.poll() is not None: return
    if os.name=='nt':
        # Child is a process created by this launcher, still running at this PID.
        subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True,check=False)
    else:
        child.terminate()
        try: child.wait(timeout=5)
        except subprocess.TimeoutExpired: child.kill()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='Validate setup without starting servers')
    parser.add_argument('--smoke-test',action='store_true',help='Start both servers, verify the frontend API proxy, then stop them')
    parser.add_argument('--node',default=os.getenv('NODE_BINARY') or shutil.which('node'))
    parser.add_argument('--backend-port',type=int,default=8000)
    parser.add_argument('--frontend-port',type=int,default=5173)
    args=parser.parse_args()
    missing=[name for name in ('fastapi','uvicorn','sqlalchemy','pydantic_settings') if importlib.util.find_spec(name) is None]
    if missing: parser.error('Install backend/requirements-core.txt in this Python environment; missing '+', '.join(missing))
    if not args.node or not Path(args.node).is_file(): parser.error('Install Node.js or pass --node PATH / set NODE_BINARY')
    vite=ROOT/'frontend/node_modules/vite/bin/vite.js'
    if not vite.exists(): parser.error('Run npm ci in frontend/ first')
    manifest=ROOT/'data/processed/expanded/manifest.json'
    if not manifest.exists(): parser.error('Run scripts/expand_datasets.py first')
    if not (1<=args.backend_port<=65535 and 1<=args.frontend_port<=65535) or args.backend_port==args.frontend_port:
        parser.error('Choose distinct valid ports')
    print(json.dumps({'python':sys.executable,'node':str(args.node),'dataset_manifest':str(manifest),'setup':'ready'},indent=2),flush=True)
    if args.check: return
    if not available(args.backend_port) or not available(args.frontend_port): parser.error('A requested port is in use; choose --backend-port and --frontend-port')
    log_dir=ROOT/'.demo'; log_dir.mkdir(exist_ok=True)
    env=os.environ.copy(); env['PYTHONIOENCODING']='utf-8'; env['BACKEND_URL']=f'http://127.0.0.1:{args.backend_port}'
    children=[]
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    with (log_dir/'backend.log').open('a',encoding='utf-8') as api_log, (log_dir/'frontend.log').open('a',encoding='utf-8') as ui_log:
        try:
            children.append(subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(args.backend_port)],cwd=ROOT/'backend',env=env,stdout=api_log,stderr=subprocess.STDOUT,creationflags=flags))
            deadline=time.monotonic()+45
            while time.monotonic()<deadline:
                if children[0].poll() is not None: raise RuntimeError('Backend exited; inspect .demo/backend.log')
                try:
                    with urllib.request.urlopen(env['BACKEND_URL']+'/api/health',timeout=2) as response:
                        health=json.load(response)
                    if health['status']=='healthy': break
                except OSError: pass
                time.sleep(.3)
            else: raise RuntimeError('Backend did not become healthy; inspect .demo/backend.log')
            children.append(subprocess.Popen([args.node,str(vite),'--host','127.0.0.1','--port',str(args.frontend_port),'--strictPort'],cwd=ROOT/'frontend',env=env,stdout=ui_log,stderr=subprocess.STDOUT,creationflags=flags))
            deadline=time.monotonic()+45
            while time.monotonic()<deadline:
                if any(child.poll() is not None for child in children): raise RuntimeError('A demo server exited; inspect .demo logs')
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{args.frontend_port}/api/health',timeout=2) as response:
                        if json.load(response)['status']=='healthy': break
                except OSError: pass
                time.sleep(.3)
            else: raise RuntimeError('Frontend proxy did not become ready; inspect .demo/frontend.log')
            if args.smoke_test:
                print('Smoke check passed: backend health and frontend API proxy. Stopping managed servers.',flush=True)
                return
            print(f'Open http://127.0.0.1:{args.frontend_port}/ - Learn > Multilingual Arcade. Logs: {log_dir}. Ctrl+C stops both servers.',flush=True)
            while all(child.poll() is None for child in children): time.sleep(.5)
            raise RuntimeError('A server exited; inspect .demo logs')
        except KeyboardInterrupt: print('\nStopping the local demo…')
        finally:
            for child in reversed(children): stop(child)


if __name__=='__main__': main()
