import os
import socket
import subprocess
import sys
import threading
import time
import json
import urllib.error
import urllib.request
from contextlib import closing

from app_constants import APP_IDENTIFIER, APP_NAME, APP_VERSION
from app_logging import get_logger
from config import get_app_data_dir, get_log_dir

try:
    import webview
except ImportError:
    print("Error: 'pywebview' module not found. Please run 'pip install pywebview'")
    sys.exit(1)


logger = get_logger("property_query.launcher")


def get_base_path():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def find_free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return sock.getsockname()[1]


def wait_for_service(base_url: str, timeout: int = 60) -> bool:
    start_time = time.time()
    health_url = f"{base_url}/api/health"
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(health_url, timeout=1) as response:
                if response.status != 200:
                    time.sleep(0.5)
                    continue
                payload = json.loads(response.read().decode("utf-8"))
                if payload.get("app") == APP_IDENTIFIER:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
            time.sleep(0.5)
    return False


def start_backend_thread(port: int):
    base_path = get_base_path()
    if base_path not in sys.path:
        sys.path.insert(0, base_path)

    backend_path = os.path.join(base_path, "backend")
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    os.environ["STATIC_FILES_PATH"] = os.path.join(base_path, "frontend", "dist")
    os.environ["PROPERTY_QUERY_PORT"] = str(port)

    import uvicorn
    from backend.main import app

    logger.info("Starting embedded backend on port %s", port)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


def start_backend_process(port: int):
    startupinfo = None
    creationflags = 0
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        creationflags = subprocess.CREATE_NO_WINDOW

    log_dir = get_log_dir()
    log_file = open(log_dir / "backend-stdout.log", "a", encoding="utf-8")

    env = os.environ.copy()
    env["PROPERTY_QUERY_PORT"] = str(port)

    process = subprocess.Popen(
        [sys.executable, "backend/main.py"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        env=env,
        startupinfo=startupinfo,
        creationflags=creationflags,
        stdout=log_file,
        stderr=log_file,
    )
    return process, log_file


def ensure_supported_webview_runtime() -> dict:
    if sys.platform != "win32":
        return {}

    try:
        import webview.platforms.winforms as winforms
    except Exception as exc:
        raise RuntimeError("Failed to inspect the Windows WebView runtime") from exc

    if hasattr(winforms, "_is_chromium") and winforms._is_chromium():
        return {"gui": "edgechromium"}

    raise RuntimeError(
        "Microsoft Edge WebView2 runtime is required. Please install WebView2 and try again."
    )


def close_window_after_delay(window, delay_ms: int):
    if delay_ms <= 0:
        return

    time.sleep(delay_ms / 1000)
    try:
        window.destroy()
    except Exception:
        logger.exception("Failed to close the window during automated smoke testing")


def main():
    is_frozen = getattr(sys, "frozen", False)
    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    backend_process = None
    backend_log_handle = None
    auto_close_ms = max(int(os.environ.get("PROPERTY_QUERY_AUTO_CLOSE_MS", "0") or 0), 0)

    try:
        get_app_data_dir()
        get_log_dir()

        if is_frozen:
            backend_thread = threading.Thread(target=start_backend_thread, args=(port,), daemon=True)
            backend_thread.start()
        else:
            backend_process, backend_log_handle = start_backend_process(port)

        if not wait_for_service(base_url):
            raise RuntimeError("Backend handshake failed")

        base_path = get_base_path()
        icon_path = os.path.join(base_path, "icon.ico")
        if not os.path.exists(icon_path):
            icon_path = None

        window = webview.create_window(
            f"{APP_NAME} {APP_VERSION}",
            base_url,
            width=1280,
            height=860,
            min_size=(900, 640),
        )

        start_params = {
            "storage_path": str(get_app_data_dir()),
            "private_mode": False,
        }
        if icon_path:
            start_params["icon"] = icon_path

        start_params.update(ensure_supported_webview_runtime())

        if auto_close_ms > 0:
            webview.start(
                close_window_after_delay,
                (window, auto_close_ms),
                **start_params,
            )
        else:
            webview.start(**start_params)
    except Exception as exc:
        logger.exception("Application startup failed: %s", exc)
        if not is_frozen:
            print(f"Error: {exc}")
            print(f"See logs in {get_log_dir()}")
    finally:
        if backend_process:
            if sys.platform == "win32":
                subprocess.run(
                    f"taskkill /F /T /PID {backend_process.pid}",
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                backend_process.terminate()
        if backend_log_handle:
            backend_log_handle.close()


if __name__ == "__main__":
    main()
