# -*- coding: utf-8 -*-
"""
文件系统监听器 - 使用 watchdog 实现零轮询的文件变动检测
"""
import os
import time
import threading
from pathlib import Path
from typing import Set, Dict, Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent

class LogseqFileHandler(FileSystemEventHandler):
    """处理 Logseq 笔记文件变动"""
    
    def __init__(self, on_change_callback: Callable[[str, str], None]):
        """
        Args:
            on_change_callback: 文件变动回调函数，参数为 (file_path, event_type)
        """
        super().__init__()
        self.on_change_callback = on_change_callback
        self._debounce_timer: Optional[threading.Timer] = None
        self._pending_changes: Dict[str, str] = {}  # file_path -> event_type
        self._lock = threading.Lock()
        self._debounce_seconds = 2.0  # 防抖时间，合并频繁变动
    
    def _schedule_callback(self):
        """安排延迟回调，实现防抖"""
        with self._lock:
            if self._debounce_timer:
                self._debounce_timer.cancel()
            
            self._debounce_timer = threading.Timer(
                self._debounce_seconds, 
                self._process_changes
            )
            self._debounce_timer.start()
    
    def _process_changes(self):
        """处理积累的变动"""
        with self._lock:
            changes = self._pending_changes.copy()
            self._pending_changes.clear()
        
        for file_path, event_type in changes.items():
            try:
                self.on_change_callback(file_path, event_type)
            except Exception as e:
                print(f"[FileWatcher] Error processing change for {file_path}: {e}")
    
    def _is_markdown(self, path: str) -> bool:
        """检查是否为 Markdown 文件"""
        return path.lower().endswith('.md')
    
    def on_modified(self, event):
        if event.is_directory:
            return
        if self._is_markdown(event.src_path):
            with self._lock:
                self._pending_changes[event.src_path] = 'modified'
            self._schedule_callback()
    
    def on_created(self, event):
        if event.is_directory:
            return
        if self._is_markdown(event.src_path):
            with self._lock:
                self._pending_changes[event.src_path] = 'created'
            self._schedule_callback()
    
    def on_deleted(self, event):
        if event.is_directory:
            return
        if self._is_markdown(event.src_path):
            with self._lock:
                self._pending_changes[event.src_path] = 'deleted'
            self._schedule_callback()


class FileWatcherService:
    """文件监听服务 - 单例模式"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._observer: Optional[Observer] = None
        self._watching_path: Optional[str] = None
        self._enabled = False
        self._changed_files: Set[str] = set()
        self._changes_lock = threading.Lock()
        self._on_change_callbacks: list = []
    
    def _handle_file_change(self, file_path: str, event_type: str):
        """处理单个文件变动"""
        print(f"[FileWatcher] Detected {event_type}: {file_path}")
        with self._changes_lock:
            self._changed_files.add(file_path)
        
        # 调用注册的回调
        for callback in self._on_change_callbacks:
            try:
                callback(file_path, event_type)
            except Exception as e:
                print(f"[FileWatcher] Callback error: {e}")
    
    def start_watching(self, graph_path: str) -> bool:
        """开始监听指定目录"""
        if not graph_path or not Path(graph_path).is_dir():
            print(f"[FileWatcher] Invalid path: {graph_path}")
            return False
        
        # 如果已经在监听同一个路径，不需要重启
        if self._observer and self._watching_path == graph_path:
            print(f"[FileWatcher] Already watching: {graph_path}")
            return True
        
        # 停止现有监听
        self.stop_watching()
        
        try:
            self._observer = Observer()
            handler = LogseqFileHandler(self._handle_file_change)
            
            # 监听 pages 和 journals 目录
            pages_dir = Path(graph_path) / "pages"
            journals_dir = Path(graph_path) / "journals"
            
            watched_count = 0
            for folder in [pages_dir, journals_dir]:
                if folder.exists():
                    self._observer.schedule(handler, str(folder), recursive=False)
                    watched_count += 1
                    print(f"[FileWatcher] Watching: {folder}")
            
            if watched_count == 0:
                print(f"[FileWatcher] No valid directories to watch in {graph_path}")
                return False
            
            self._observer.start()
            self._watching_path = graph_path
            self._enabled = True
            print(f"[FileWatcher] Started watching {graph_path}")
            return True
            
        except Exception as e:
            print(f"[FileWatcher] Failed to start: {e}")
            return False
    
    def stop_watching(self):
        """停止监听"""
        if self._observer:
            try:
                self._observer.stop()
                self._observer.join(timeout=3)
            except Exception as e:
                print(f"[FileWatcher] Error stopping: {e}")
            finally:
                self._observer = None
                self._watching_path = None
                self._enabled = False
                print("[FileWatcher] Stopped")
    
    def get_pending_changes(self) -> Set[str]:
        """获取待处理的变动文件列表"""
        with self._changes_lock:
            return self._changed_files.copy()
    
    def get_pending_count(self) -> int:
        """获取待处理变动数量"""
        with self._changes_lock:
            return len(self._changed_files)
    
    def clear_pending_changes(self):
        """清空待处理变动"""
        with self._changes_lock:
            self._changed_files.clear()
    
    def is_enabled(self) -> bool:
        """是否启用"""
        return self._enabled
    
    def is_watching(self) -> bool:
        """是否正在监听"""
        return self._observer is not None and self._observer.is_alive()
    
    def get_status(self) -> dict:
        """获取状态信息"""
        return {
            "enabled": self._enabled,
            "watching": self.is_watching(),
            "path": self._watching_path,
            "pending_count": self.get_pending_count()
        }
    
    def register_callback(self, callback: Callable[[str, str], None]):
        """注册变动回调"""
        if callback not in self._on_change_callbacks:
            self._on_change_callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[str, str], None]):
        """注销变动回调"""
        if callback in self._on_change_callbacks:
            self._on_change_callbacks.remove(callback)


# 全局单例
file_watcher = FileWatcherService()
