import os,sys,time,subprocess

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def log(s):
    print('[monitor]%s'% s)
   
class MyFileSystemEventHandler(FileSystemEventHandler):
    def __init__(self,fn):
        super(MyFileSystemEventHandler,self).__init__()
        self.restart = fn
        
    def on_any_event(self,event):
        if event.src_path.endswith('.py'):
            log('Python源文件已更改:%s' % event.src_path)
            self.restart()
command = ['echo','ok']
process = None

def kill_process():
    global process
    if process:
        log('杀死进程 [%s]...' %process.pid)
        process.kill()
        process.wait()
        log('流程以打代码结束 %s' % process.returncode)
        process = None

def start_process():
    global process,command
    log('开始处理%s...'%''.join(command))
    process = subprocess.Popen(command,stdin=sys.stdin,stdout=sys.stdout,stderr=sys.stderr)
    
def restart_process():
    kill_process()
    start_process()
    
def start_watch(path,callback):
    observer = Observer()
    observer.schedule(MyFileSystemEventHandler(restart_process),path,recursive=True)
    observer.start()
    log('看目录%s...' % path)
    start_process()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ =='__main__':
    argv = sys.argv[1:]
    if not argv:
        print('用法：./pymonitor 你的脚本.py')
        exit(0)
    if argv[0] != 'python':
        argv.insert(0,'python')
    command = argv
    path = os.path.abspath('.')
    start_watch(path,None)
        