# -*- coding: utf-8 -*-
import json
from pathlib import Path
from typing import Dict, Any, List
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


# ---- 以下为“高级属性查询-排序记忆”的持久化工具函数 ----

def get_sort_memory(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取配置中的 query_sort_memory 字段（若不存在则返回空字典）。"""
    qsm = config.get("query_sort_memory")
    return qsm if isinstance(qsm, dict) else {}


def _sanitize_sort_model(sort_model: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """清理排序模型，确保字段合法且顺序稳定。"""
    sanitized: List[Dict[str, Any]] = []
    for index, item in enumerate(sort_model or []):
        if not isinstance(item, dict):
            continue
        col = item.get("colId") or item.get("field")
        sort = item.get("sort")
        if not col or sort not in ("asc", "desc"):
            continue
        sort_index = item.get("sortIndex")
        sanitized.append({
            "colId": str(col),
            "sort": sort,
            "sortIndex": sort_index if isinstance(sort_index, int) else index,
        })
    return sanitized


def _sanitize_column_order(column_order: List[Any]) -> List[str]:
    """清理列顺序列表，仅保留非空字符串并保持原有顺序。"""
    if not isinstance(column_order, list):
        return []
    filtered = [str(item) for item in column_order if isinstance(item, str) and item]
    return _unique(filtered)


def get_sort_for_query(graph_path: str, query_raw: str) -> Dict[str, Any]:
    """
    读取指定 graph_path + 查询原文的排序配置。
    返回格式: {'sortModel': [...], 'columnOrder': [...]}
    """
    if not graph_path or not query_raw:
        return {"sortModel": [], "columnOrder": []}
    config = load_config()
    qsm = get_sort_memory(config)
    entry = qsm.get(graph_path)
    if not isinstance(entry, dict):
        return {"sortModel": [], "columnOrder": []}
    sort_info = entry.get(query_raw)
    if not isinstance(sort_info, dict):
        return {"sortModel": [], "columnOrder": []}
    sort_model = sort_info.get("sortModel")
    column_order = sort_info.get("columnOrder")
    return {
        "sortModel": _sanitize_sort_model(sort_model) if isinstance(sort_model, list) else [],
        "columnOrder": _sanitize_column_order(column_order),
    }


def save_sort_for_query(
    graph_path: str,
    query_raw: str,
    sort_model: List[Dict[str, Any]] = None,
    column_order: List[str] = None,
) -> None:
    """
    保存指定 graph_path + 查询原文的排序配置。
    sort_model 来自 Ag-Grid 的 getSortModel 数据；column_order 为当前显示列顺序。
    允许仅更新其中一项。
    """
    if not graph_path or not query_raw:
        return
    graph_key = graph_path.strip()
    query_key = query_raw.strip()
    config = load_config()
    qsm = get_sort_memory(config)
    graph_entry = qsm.get(graph_key)
    if not isinstance(graph_entry, dict):
        graph_entry = {}
    entry = graph_entry.get(query_key)
    if not isinstance(entry, dict):
        entry = {}
    if sort_model is not None:
        entry["sortModel"] = _sanitize_sort_model(sort_model)
    if column_order is not None:
        entry["columnOrder"] = _sanitize_column_order(column_order)
    entry["updated_at"] = datetime.datetime.now().isoformat()
    graph_entry[query_key] = entry
    qsm[graph_key] = graph_entry
    config["query_sort_memory"] = qsm
    save_config(config)


def clear_sort_memory(graph_path: str = None) -> None:
    """
    清除排序记忆：
    - 指定 graph_path: 仅清除该路径下所有查询的排序记忆
    - 未指定: 清除所有路径的排序记忆
    """
    config = load_config()
    qsm = get_sort_memory(config)
    if graph_path:
        graph_key = graph_path.strip()
        if graph_key in qsm:
            qsm.pop(graph_key, None)
    else:
        qsm = {}
    config["query_sort_memory"] = qsm
    save_config(config)