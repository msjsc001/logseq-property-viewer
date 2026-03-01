import subprocess
import time
import os
import sys
import socket
import threading
from contextlib import closing

# 尝试导入 pywebview
try:
    import webview
except ImportError:
    print("Error: 'pywebview' module not found. Please run 'pip install pywebview'")
    sys.exit(1)

def get_base_path():
    """获取基础路径（兼容 PyInstaller 打包）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后
        return sys._MEIPASS
    else:
        # 开发模式
        return os.path.dirname(os.path.abspath(__file__))

def check_port(host, port):
    """检查端口是否开放"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(1)
        return sock.connect_ex((host, port)) == 0

def wait_for_service(host, port, timeout=60):
    """等待服务启动"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if check_port(host, port):
            return True
        time.sleep(0.5)
    return False

def start_backend_thread():
    """在线程中运行后端（适用于打包模式）"""
    base_path = get_base_path()
    
    # 添加路径到 sys.path
    if base_path not in sys.path:
        sys.path.insert(0, base_path)
    
    backend_path = os.path.join(base_path, 'backend')
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    # 设置静态文件路径环境变量
    os.environ['STATIC_FILES_PATH'] = os.path.join(base_path, 'frontend', 'dist')
    
    # 导入并运行 uvicorn
    import uvicorn
    from backend.main import app
    
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

def start_backend_process():
    """启动后端进程（开发模式）"""
    print(">> Starting Backend (Port 8000)...")
    
    # 隐藏窗口标志（仅 Windows）
    startupinfo = None
    creationflags = 0
    if sys.platform == 'win32':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        creationflags = subprocess.CREATE_NO_WINDOW
    
    return subprocess.Popen(
        [sys.executable, "backend/main.py"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        env=os.environ.copy(),
        startupinfo=startupinfo,
        creationflags=creationflags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def main():
    is_frozen = getattr(sys, 'frozen', False)
    
    if not is_frozen:
        print("正在启动 Property Query 2.2.0 (开发模式)...")
    
    backend_proc = None
    backend_thread = None
    
    try:
        if is_frozen:
            # 打包模式：在线程中运行后端
            backend_thread = threading.Thread(target=start_backend_thread, daemon=True)
            backend_thread.start()
        else:
            # 开发模式：启动子进程
            backend_proc = start_backend_process()
        
        # 等待服务就绪
        if not is_frozen:
            print(">> Waiting for services to be ready...")
        
        if not wait_for_service("127.0.0.1", 8000):
            if not is_frozen:
                print("Error: Backend failed to start. Check console for errors.")
            raise Exception("Backend timeout")
        
        if not is_frozen:
            print(">> Services Ready! Launching Window...")
        
        # 获取用户数据目录用于持久化 localStorage
        from config import get_app_data_dir
        storage_path = str(get_app_data_dir())
        
        # 确保目录存在
        os.makedirs(storage_path, exist_ok=True)
        
        # 获取图标路径
        base_path = get_base_path()
        icon_path = os.path.join(base_path, 'icon.ico')
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.ico')
        if not os.path.exists(icon_path):
            icon_path = None
        
        # 创建并启动独立窗口（带图标）
        window = webview.create_window(
            'Property Query 2.2.0',
            'http://127.0.0.1:8000',
            width=1200,
            height=800,
            min_size=(800, 600)
        )
        
        # 使用指定的存储路径和图标启动
        start_params = {'storage_path': storage_path}
        if icon_path:
            start_params['icon'] = icon_path
        webview.start(**start_params)
        
    except Exception as e:
        if not is_frozen:
            print(f"Error: {e}")
    finally:
        if not is_frozen:
            print("\nClosing application...")
        
        # 终止后端进程（仅开发模式）
        if backend_proc and sys.platform == 'win32':
            subprocess.run(f"taskkill /F /T /PID {backend_proc.pid}", shell=True, 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif backend_proc:
            backend_proc.terminate()
        
        if not is_frozen:
            print("Done.")

if __name__ == "__main__":
    main()
