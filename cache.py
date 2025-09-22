# -*- coding: utf-8 -*-
import hashlib
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List

# --- 常量定义 ---
CACHE_DIR_NAME = ".logseq_tui_cache"

def get_cache_dir() -> Path:
    """获取并确保缓存目录存在。"""
    cache_dir = Path.cwd() / CACHE_DIR_NAME
    cache_dir.mkdir(exist_ok=True)
    return cache_dir

def _get_cache_filepath_for_graph(graph_path: str) -> Path:
    """根据给定的 graph 路径生成一个唯一的、安全的缓存文件名。"""
    # 使用路径的 SHA256 哈希值作为文件名，避免特殊字符问题
    path_hash = hashlib.sha256(graph_path.encode('utf-8')).hexdigest()
    return get_cache_dir() / f"{path_hash}.json"

def load_cache(graph_path: str) -> Dict[str, Any]:
    """
    加载指定 Logseq 库的缓存文件。

    Args:
        graph_path (str): Logseq 知识库的路径。

    Returns:
        Dict[str, Any]: 加载的缓存数据。如果缓存不存在或无效，则返回空字典。
    """
    cache_file = _get_cache_filepath_for_graph(graph_path)
    if not cache_file.exists():
        return {}
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        # 如果文件损坏或无法读取，当作没有缓存处理
        return {}

def save_cache(graph_path: str, cache_data: Dict[str, Any]) -> None:
    """
    将缓存数据保存到文件。

    Args:
        graph_path (str): Logseq 知识库的路径。
        cache_data (Dict[str, Any]): 要保存的缓存数据。
    """
    cache_file = _get_cache_filepath_for_graph(graph_path)
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=4)
    except IOError:
        # 在这里可以添加日志记录，通知用户缓存保存失败
        pass

def get_all_blocks_from_cache(cache_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    从缓存数据中提取并返回所有 block 的列表。
    """
    all_blocks = []
    for file_info in cache_data.values():
        all_blocks.extend(file_info.get("blocks", []))
    return all_blocks

def clear_all_cache() -> bool:
    """
    删除整个缓存目录。

    Returns:
        bool: 如果成功删除目录则返回 True，否则返回 False。
    """
    cache_dir = get_cache_dir()
    if cache_dir.exists():
        try:
            shutil.rmtree(cache_dir)
            return True
        except OSError:
            return False
    return True # 目录不存在，也算成功
