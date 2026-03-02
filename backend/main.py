# -*- coding: utf-8 -*-
import sys
import os
import asyncio
import re
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 将根目录添加到 sys.path 以便引用原有模块
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

# 导入核心模块
import config
import cache
import core

# --- 内联的核心函数 (原 logic_adapter) ---
_executor = ThreadPoolExecutor(max_workers=4)

async def run_in_executor(func: Callable, *args):
    """在线程池中运行同步函数"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, func, *args)

async def handle_build_cache(graph_path: str, progress_callback: Callable[[str], None] = None) -> int:
    """重建缓存"""
    def _build():
        if progress_callback:
            progress_callback(f"Scanning {graph_path}...")
        cache_data = core.scan_and_parse_graph(graph_path)
        cache.save_cache(graph_path, cache_data)
        return len(cache_data)
    return await run_in_executor(_build)

def _perform_search_on_cache(all_blocks: List[Dict], query: str) -> List[Dict]:
    """执行搜索 (同步)"""
    query = query.strip()
    if not query:
        return []
    
    results = []
    # 解析查询条件
    if query.startswith("has:"):
        key = query[4:].strip()
        for block in all_blocks:
            props = block.get("properties", {})
            if key in props:
                results.append(block)
    elif ":" in query:
        parts = query.split(":", 1)
        key = parts[0].strip()
        value = parts[1].strip() if len(parts) > 1 else ""
        for block in all_blocks:
            props = block.get("properties", {})
            if key in props and value.lower() in str(props[key]).lower():
                results.append(block)
    else:
        # 全文搜索
        for block in all_blocks:
            props = block.get("properties", {})
            for k, v in props.items():
                if query.lower() in str(k).lower() or query.lower() in str(v).lower():
                    results.append(block)
                    break
    return results

# --- FastAPI App ---
app = FastAPI(title="Logseq Query API", version="2.2.1")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---

class ConfigUpdate(BaseModel):
    graph_path: str

class SearchRequest(BaseModel):
    query: str
    graph_path: Optional[str] = None

# --- API Endpoints ---

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "2.2.1"}

@app.get("/api/config")
async def get_config():
    """获取当前配置"""
    try:
        cfg = await run_in_executor(config.load_config)
        return cfg
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config")
async def update_config(data: ConfigUpdate):
    """更新配置"""
    try:
        cfg = await run_in_executor(config.load_config)
        cfg["graph_path"] = data.graph_path
        await run_in_executor(config.save_config, cfg)
        return {"status": "success", "config": cfg}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cache/build")
async def build_cache(graph_path: str = Body(..., embed=True)):
    """重建指定路径的缓存"""
    if not graph_path or not Path(graph_path).is_dir():
        raise HTTPException(status_code=400, detail="Invalid graph path")
    
    try:
        # 定义一个简单的回调函数用于接收进度（目前仅打印）
        def progress_callback(msg):
            print(f"[Cache Build] {msg}")
            
        file_count = await handle_build_cache(graph_path, progress_callback)
        return {"status": "success", "file_count": file_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cache/clear")
async def clear_cache_endpoint():
    """清除缓存文件"""
    try:
        await run_in_executor(cache.clear_all_cache)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config/clear-sort-memory")
async def clear_sort_memory():
    """清除排序记忆"""
    try:
        from config import clear_sort_memory as do_clear
        await run_in_executor(do_clear)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reset-all")
async def reset_all_data():
    """恢复出厂设置 - 清除所有配置、缓存、搜索记录"""
    try:
        # 1. 清除缓存目录
        await run_in_executor(cache.clear_all_cache)
        
        # 2. 重置配置文件为空
        empty_config = {}
        await run_in_executor(config.save_config, empty_config)
        
        return {"status": "success", "message": "所有数据已清除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config/auto-update")
async def set_auto_update(data: dict = Body(...)):
    """设置自动更新选项 - 使用文件系统监听"""
    from file_watcher import file_watcher
    
    try:
        enabled = data.get("enabled", False)
        cfg = await run_in_executor(config.load_config)
        cfg["auto_update_enabled"] = enabled
        await run_in_executor(config.save_config, cfg)
        
        # 启动或停止文件监听
        graph_path = cfg.get("graph_path")
        if enabled and graph_path:
            file_watcher.start_watching(graph_path)
        else:
            file_watcher.stop_watching()
        
        return {"status": "success", "watching": file_watcher.is_watching()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/check-updates")
async def check_for_updates():
    """获取文件监听器状态和待更新文件数"""
    from file_watcher import file_watcher
    
    status = file_watcher.get_status()
    return {
        "needs_update": status["pending_count"] > 0,
        "changed_count": status["pending_count"],
        "watching": status["watching"],
        "enabled": status["enabled"]
    }

@app.post("/api/apply-updates")
async def apply_incremental_updates():
    """应用增量更新 - 只处理变动的文件"""
    from file_watcher import file_watcher
    
    try:
        pending_files = file_watcher.get_pending_changes()
        
        if not pending_files:
            return {"status": "success", "updated_count": 0, "message": "没有待更新的文件"}
        
        cfg = await run_in_executor(config.load_config)
        graph_path = cfg.get("graph_path")
        
        if not graph_path:
            return {"status": "error", "message": "未配置数据源路径"}
        
        # 加载现有缓存
        cache_data = await run_in_executor(cache.load_cache, graph_path)
        
        updated_count = 0
        for file_path in pending_files:
            file_path = Path(file_path)
            
            if not file_path.exists():
                # 文件已删除，从缓存中移除
                file_key = str(file_path)
                if file_key in cache_data:
                    del cache_data[file_key]
                    updated_count += 1
            else:
                # 文件新建或修改，重新解析
                try:
                    blocks = core.parse_file_for_properties(str(file_path))
                    cache_data[str(file_path)] = {
                        "blocks": blocks,
                        "mtime": file_path.stat().st_mtime
                    }
                    updated_count += 1
                except Exception as e:
                    print(f"[IncrementalUpdate] Error parsing {file_path}: {e}")
        
        # 保存更新后的缓存
        await run_in_executor(cache.save_cache, graph_path, cache_data)
        
        # 清空待处理队列
        file_watcher.clear_pending_changes()
        
        return {"status": "success", "updated_count": updated_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/open-data-dir")
async def open_data_dir():
    """打开用户数据存储目录"""
    import subprocess
    import platform
    from config import get_app_data_dir
    
    data_dir = str(get_app_data_dir())
    try:
        if platform.system() == "Windows":
            os.startfile(data_dir)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", data_dir])
        else:
            subprocess.Popen(["xdg-open", data_dir])
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 用户偏好存储 API ---

@app.get("/api/preferences")
async def get_preferences():
    """获取用户偏好（查询历史、全局隐藏列等）"""
    try:
        cfg = await run_in_executor(config.load_config)
        graph_path = cfg.get("graph_path", "")
        # 如果获取不到 graph_path 默认返回 main
        graph_name = os.path.basename(graph_path.strip(os.sep)) if graph_path else "main"
        
        return {
            "query_history": cfg.get("query_history", []),
            "global_hidden_columns": cfg.get("global_hidden_columns", []),
            "column_configs": cfg.get("column_configs", {}),
            "sidebar_collapsed": cfg.get("sidebar_collapsed", False),
            "auto_update_enabled": cfg.get("auto_update_enabled", False),
            "graph_name": graph_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/preferences/query-history")
async def save_query_history(data: dict = Body(...)):
    """保存查询历史"""
    try:
        history = data.get("history", [])
        cfg = await run_in_executor(config.load_config)
        cfg["query_history"] = history[:20]  # 最多保存20条
        await run_in_executor(config.save_config, cfg)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/preferences/global-hidden-columns")
async def save_global_hidden_columns(data: dict = Body(...)):
    """保存全局隐藏列"""
    try:
        columns = data.get("columns", [])
        cfg = await run_in_executor(config.load_config)
        cfg["global_hidden_columns"] = columns
        await run_in_executor(config.save_config, cfg)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/preferences/column-config")
async def save_column_config(data: dict = Body(...)):
    """保存某个查询的列配置"""
    try:
        query_key = data.get("query_key", "")
        column_config = data.get("config", {})
        cfg = await run_in_executor(config.load_config)
        if "column_configs" not in cfg:
            cfg["column_configs"] = {}
        cfg["column_configs"][query_key] = column_config
        await run_in_executor(config.save_config, cfg)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/preferences/sidebar")
async def save_sidebar_state(data: dict = Body(...)):
    """保存侧边栏折叠状态"""
    try:
        collapsed = data.get("collapsed", False)
        cfg = await run_in_executor(config.load_config)
        cfg["sidebar_collapsed"] = collapsed
        await run_in_executor(config.save_config, cfg)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search")
async def search(req: SearchRequest):
    """执行高级查询"""
    path = req.graph_path
    if not path:
        # 尝试从配置加载默认路径
        cfg = config.load_config()
        path = cfg.get("graph_path")
    
    if not path or not Path(path).is_dir():
        raise HTTPException(status_code=400, detail="Graph path not configured or invalid")
    
    try:
        # 1. 确保缓存是最新的（可选，这里为了性能假设已手动更新，或者可以静默更新）
        # 这里为了响应速度，假设用户已点击更新缓存，或者前端单独调用 build_cache
        # 但为了用户体验，我们可以做一次轻量级检查或静默更新（视 logic_adapter 实现而定）
        # 暂时直接加载缓存
        
        cache_data = await run_in_executor(cache.load_cache, path)
        all_blocks = await run_in_executor(cache.get_all_blocks_from_cache, cache_data)
        results = await run_in_executor(_perform_search_on_cache, all_blocks, req.query)
        
        # 展平结果以便前端表格展示
        flat_results = []
        if results:
            for i, item in enumerate(results):
                flat_item = {
                    'id': i, 
                    'page': item.get('page', ''), 
                    'content': item.get('content', '')
                }
                # 提取属性，防止覆盖内置保留字段
                properties = item.get('properties', {})
                if properties:
                    reserved_keys = {'id', 'page', 'content', '_missing', 'key'}
                    for k, v in properties.items():
                        if k in reserved_keys:
                            flat_item[f"prop_{k}"] = v
                        else:
                            flat_item[k] = v
                
                # 传递 file_path 以便前端后续扩展使用
                file_path = item.get('file_path')
                if file_path:
                    flat_item['file_path'] = file_path
                
                flat_results.append(flat_item)
                
        return {"results": flat_results, "count": len(flat_results)}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_stats():
    """获取所有属性键的统计信息"""
    from collections import Counter
    
    cfg = config.load_config()
    path = cfg.get("graph_path")
    
    if not path or not Path(path).is_dir():
        raise HTTPException(status_code=400, detail="Graph path not configured")
    
    try:
        cache_data = await run_in_executor(cache.load_cache, path)
        all_blocks = await run_in_executor(cache.get_all_blocks_from_cache, cache_data)
        
        # 统计所有属性键
        key_counter = Counter()
        key_unique_values = {}
        
        for block in all_blocks:
            props = block.get('properties', {})
            for key, value in props.items():
                key_counter[key] += 1
                if key not in key_unique_values:
                    key_unique_values[key] = set()
                key_unique_values[key].add(str(value))
        
        keys = [
            {"key": k, "count": v, "uniqueValues": len(key_unique_values.get(k, set()))}
            for k, v in key_counter.most_common()  # 返回全部，按次数排序
        ]
        
        return {"keys": keys, "total": len(keys)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats/values/{key}")
async def get_value_distribution(key: str):
    """获取指定属性键的值分布"""
    from collections import Counter
    
    cfg = config.load_config()
    path = cfg.get("graph_path")
    
    if not path or not Path(path).is_dir():
        raise HTTPException(status_code=400, detail="Graph path not configured")
    
    try:
        cache_data = await run_in_executor(cache.load_cache, path)
        all_blocks = await run_in_executor(cache.get_all_blocks_from_cache, cache_data)
        
        value_counter = Counter()
        for block in all_blocks:
            props = block.get('properties', {})
            if key in props:
                value_counter[str(props[key])] += 1
        
        values = [
            {"value": v, "count": c}
            for v, c in value_counter.most_common()  # 返回全部，按次数排序
        ]
        
        return {"values": values, "total": len(values)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 静态文件托管 (必须在 API 路由之后) ---
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 支持 PyInstaller 打包：优先使用环境变量指定的路径
static_dir_path = os.environ.get('STATIC_FILES_PATH', str(ROOT_DIR / "frontend" / "dist"))
static_dir = Path(static_dir_path)

if static_dir.exists():
    # 1. 优先挂载 assets 目录 (Vite 构建产物默认在 assets 下)
    assets_dir = static_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # 2. 根路径返回 index.html
    @app.get("/")
    async def serve_root():
        return FileResponse(static_dir / "index.html")

    # 3. 其他路径：尝试查找文件，找不到则返回 index.html (SPA 支持)
    @app.get("/{path:path}")
    async def serve_static_or_fallback(path: str):
        # 排除 API 路径
        if path.startswith("api/"):
            raise HTTPException(status_code=404)
        
        file_path = static_dir / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        
        return FileResponse(static_dir / "index.html")
        
    print(f"Static files configured from {static_dir}")
else:
    print(f"Warning: Static directory not found at {static_dir}")

# --- 启动入口 ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
