import datetime
import json
import os
import shutil
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List

from app_constants import APP_STORAGE_NAME


_CONFIG_LOCK = threading.Lock()


def get_app_data_dir() -> Path:
    """Return the per-user data directory used by the application."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", "")) / APP_STORAGE_NAME
    else:
        base = Path.home() / f".{APP_STORAGE_NAME.lower()}"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_log_dir() -> Path:
    log_dir = get_app_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


CONFIG_FILE = get_app_data_dir() / "config.json"
_OLD_CONFIG_FILE = Path.home() / ".logseq_query_config.json"


DEFAULT_CONFIG: Dict[str, Any] = {
    "graph_path": "",
    "language": "zh",
    "query_case_sensitive": False,
    "query_history": [],
    "global_hidden_columns": [],
    "column_configs": {},
    "sidebar_collapsed": False,
    "auto_update_enabled": False,
    "query_sort_memory": {},
    "column_filters": {},
}


if _OLD_CONFIG_FILE.exists() and not CONFIG_FILE.exists():
    try:
        shutil.move(str(_OLD_CONFIG_FILE), str(CONFIG_FILE))
    except OSError:
        pass


def _normalize_config(config: Dict[str, Any] | None) -> Dict[str, Any]:
    normalized = dict(DEFAULT_CONFIG)
    if isinstance(config, dict):
        normalized.update(config)
    normalized["query_history"] = [
        str(item)
        for item in normalized.get("query_history", [])
        if isinstance(item, str) and item.strip()
    ][:20]
    normalized["global_hidden_columns"] = [
        str(item)
        for item in normalized.get("global_hidden_columns", [])
        if isinstance(item, str) and item
    ]
    if not isinstance(normalized.get("column_configs"), dict):
        normalized["column_configs"] = {}
    if not isinstance(normalized.get("query_sort_memory"), dict):
        normalized["query_sort_memory"] = {}
    if not isinstance(normalized.get("column_filters"), dict):
        normalized["column_filters"] = {}
    normalized["sidebar_collapsed"] = bool(normalized.get("sidebar_collapsed", False))
    normalized["auto_update_enabled"] = bool(normalized.get("auto_update_enabled", False))
    normalized["query_case_sensitive"] = bool(normalized.get("query_case_sensitive", False))
    normalized["language"] = (
        normalized.get("language")
        if normalized.get("language") in {"zh", "en"}
        else "zh"
    )
    normalized["graph_path"] = str(normalized.get("graph_path", "") or "")
    return normalized


def load_config() -> Dict[str, Any]:
    with _CONFIG_LOCK:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as file:
                    return _normalize_config(json.load(file))
            except (json.JSONDecodeError, OSError):
                return dict(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)


def save_config(config: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_config(config)
    with _CONFIG_LOCK:
        with open(CONFIG_FILE, "w", encoding="utf-8") as file:
            json.dump(normalized, file, indent=4, ensure_ascii=False)
    return normalized


def update_config(partial: Dict[str, Any]) -> Dict[str, Any]:
    config = load_config()
    config.update(partial)
    return save_config(config)


def reset_config(
    *,
    clear_graph_path: bool = True,
    clear_preferences: bool = True,
    clear_history: bool = True,
) -> Dict[str, Any]:
    config = load_config()
    if clear_graph_path:
        config["graph_path"] = ""
    if clear_history:
        config["query_history"] = []
    if clear_preferences:
        config["language"] = DEFAULT_CONFIG["language"]
        config["query_case_sensitive"] = DEFAULT_CONFIG["query_case_sensitive"]
        config["global_hidden_columns"] = []
        config["column_configs"] = {}
        config["sidebar_collapsed"] = False
        config["auto_update_enabled"] = False
        config["query_sort_memory"] = {}
        config["column_filters"] = {}
    return save_config(config)


def clear_ui_preferences() -> Dict[str, Any]:
    return reset_config(
        clear_graph_path=False,
        clear_preferences=True,
        clear_history=False,
    )


def get_column_filters(config: Dict[str, Any]) -> Dict[str, Any]:
    column_filters = config.get("column_filters")
    return column_filters if isinstance(column_filters, dict) else {}


def _unique(seq: List[Any]) -> List[Any]:
    seen = set()
    out: List[Any] = []
    for item in seq:
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out


def get_filters_for_path(graph_path: str) -> Dict[str, Any]:
    config = load_config()
    column_filters = get_column_filters(config)
    entry = column_filters.get(graph_path)
    if isinstance(entry, dict):
        selected = entry.get("selected", [])
        seen = entry.get("seen", [])
        return {
            "selected": selected if isinstance(selected, list) else [],
            "seen": seen if isinstance(seen, list) else [],
        }
    return {"selected": [], "seen": []}


def save_filters_for_path(graph_path: str, selected, seen) -> None:
    config = load_config()
    column_filters = get_column_filters(config)
    column_filters[graph_path] = {
        "selected": _unique(list(selected)) if isinstance(selected, (list, tuple)) else [],
        "seen": _unique(list(seen)) if isinstance(seen, (list, tuple)) else [],
        "updated_at": datetime.datetime.now().isoformat(),
    }
    config["column_filters"] = column_filters
    save_config(config)


def clear_filters(graph_path: str | None = None) -> None:
    config = load_config()
    if graph_path:
        column_filters = get_column_filters(config)
        column_filters.pop(graph_path, None)
        config["column_filters"] = column_filters
    else:
        config["column_filters"] = {}
    save_config(config)


def get_sort_memory(config: Dict[str, Any]) -> Dict[str, Any]:
    sort_memory = config.get("query_sort_memory")
    return sort_memory if isinstance(sort_memory, dict) else {}


def _sanitize_sort_model(sort_model: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sanitized: List[Dict[str, Any]] = []
    for index, item in enumerate(sort_model or []):
        if not isinstance(item, dict):
            continue
        column_id = item.get("colId") or item.get("field")
        sort = item.get("sort")
        if not column_id or sort not in ("asc", "desc"):
            continue
        sort_index = item.get("sortIndex")
        sanitized.append(
            {
                "colId": str(column_id),
                "sort": sort,
                "sortIndex": sort_index if isinstance(sort_index, int) else index,
            }
        )
    return sanitized


def _sanitize_column_order(column_order: List[Any]) -> List[str]:
    if not isinstance(column_order, list):
        return []
    filtered = [str(item) for item in column_order if isinstance(item, str) and item]
    return _unique(filtered)


def get_sort_for_query(graph_path: str, query_raw: str) -> Dict[str, Any]:
    if not graph_path or not query_raw:
        return {"sortModel": [], "columnOrder": []}
    config = load_config()
    sort_memory = get_sort_memory(config)
    graph_entry = sort_memory.get(graph_path)
    if not isinstance(graph_entry, dict):
        return {"sortModel": [], "columnOrder": []}
    sort_info = graph_entry.get(query_raw)
    if not isinstance(sort_info, dict):
        return {"sortModel": [], "columnOrder": []}
    return {
        "sortModel": _sanitize_sort_model(sort_info.get("sortModel", [])),
        "columnOrder": _sanitize_column_order(sort_info.get("columnOrder", [])),
    }


def save_sort_for_query(
    graph_path: str,
    query_raw: str,
    sort_model: List[Dict[str, Any]] | None = None,
    column_order: List[str] | None = None,
) -> None:
    if not graph_path or not query_raw:
        return
    config = load_config()
    sort_memory = get_sort_memory(config)
    graph_entry = sort_memory.get(graph_path)
    if not isinstance(graph_entry, dict):
        graph_entry = {}
    entry = graph_entry.get(query_raw)
    if not isinstance(entry, dict):
        entry = {}
    if sort_model is not None:
        entry["sortModel"] = _sanitize_sort_model(sort_model)
    if column_order is not None:
        entry["columnOrder"] = _sanitize_column_order(column_order)
    entry["updated_at"] = datetime.datetime.now().isoformat()
    graph_entry[query_raw] = entry
    sort_memory[graph_path] = graph_entry
    config["query_sort_memory"] = sort_memory
    save_config(config)


def clear_sort_memory(graph_path: str | None = None) -> None:
    config = load_config()
    sort_memory = get_sort_memory(config)
    if graph_path:
        sort_memory.pop(graph_path.strip(), None)
    else:
        sort_memory = {}
    config["query_sort_memory"] = sort_memory
    save_config(config)


def get_language() -> str:
    return load_config().get("language", "zh")


def set_language(lang: str) -> Dict[str, Any]:
    return update_config({"language": lang if lang in {"zh", "en"} else "zh"})
