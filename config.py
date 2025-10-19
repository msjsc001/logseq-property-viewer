# -*- coding: utf-8 -*-
import json
from pathlib import Path
from typing import Dict, Any
import datetime

CONFIG_FILE = Path.home() / ".logseq_query_config.json"

def load_config() -> Dict[str, Any]:
    """
    从用户主目录下的 .logseq_query_config.json 文件加载配置。
    
    如果文件不存在或内容为无效的 JSON，则返回一个空字典。

    Returns:
        Dict[str, Any]: 包含配置项的字典。
    """
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_config(config: Dict[str, Any]):
    """
    将给定的配置字典保存到 .logseq_query_config.json 文件中。

    Args:
        config (Dict[str, Any]): 需要保存的配置字典。
    """
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


# ---- 以下为“高级属性查询-列过滤”的持久化工具函数 ----

def get_column_filters(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取配置中的 column_filters 字段（若不存在则返回空字典）。"""
    cf = config.get("column_filters")
    return cf if isinstance(cf, dict) else {}

def _unique(seq):
    """保持顺序的去重"""
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out

def get_filters_for_path(graph_path: str) -> Dict[str, Any]:
    """
    读取指定 graph_path 的过滤配置。
    返回格式: {'selected': [...], 'seen': [...]}
    """
    config = load_config()
    cf = get_column_filters(config)
    entry = cf.get(graph_path)
    if isinstance(entry, dict):
        selected = entry.get("selected", [])
        seen = entry.get("seen", [])
        if not isinstance(selected, list):
            selected = []
        if not isinstance(seen, list):
            seen = []
        return {"selected": selected, "seen": seen}
    return {"selected": [], "seen": []}

def save_filters_for_path(graph_path: str, selected, seen) -> None:
    """
    持久化指定 graph_path 的列过滤状态：
    - selected: 当前勾选的列（保持顺序，去重）
    - seen: 已知道的列全集（保持顺序，去重）
    """
    config = load_config()
    cf = get_column_filters(config)
    selected_list = _unique(list(selected)) if isinstance(selected, (list, tuple)) else []
    seen_list = _unique(list(seen)) if isinstance(seen, (list, tuple)) else []
    cf[graph_path] = {
        "selected": selected_list,
        "seen": seen_list,
        "updated_at": datetime.datetime.now().isoformat(),
    }
    config["column_filters"] = cf
    save_config(config)

def clear_filters(graph_path: str = None) -> None:
    """
    清理列过滤偏好：
    - 指定 graph_path: 仅清除该路径的偏好
    - 未指定: 清除所有路径的偏好
    """
    config = load_config()
    if graph_path:
        cf = get_column_filters(config)
        if graph_path in cf:
            cf.pop(graph_path, None)
        config["column_filters"] = cf
    else:
        config["column_filters"] = {}
    save_config(config)