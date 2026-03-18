# -*- coding: utf-8 -*-
import datetime
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

from config import get_app_data_dir


CACHE_DIR_NAME = "cache"
CACHE_SCHEMA_VERSION = 3


def get_cache_dir() -> Path:
    cache_dir = get_app_data_dir() / CACHE_DIR_NAME
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _get_cache_filepath_for_graph(graph_path: str) -> Path:
    path_hash = hashlib.sha256(graph_path.encode("utf-8")).hexdigest()
    return get_cache_dir() / f"{path_hash}.json"


def build_cache_payload(graph_path: str, files: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": CACHE_SCHEMA_VERSION,
        "graph_path": graph_path,
        "generated_at": datetime.datetime.now().isoformat(),
        "files": files,
    }


def empty_cache_payload(graph_path: str) -> Dict[str, Any]:
    return build_cache_payload(graph_path, {})


def load_cache(graph_path: str) -> Dict[str, Any]:
    cache_file = _get_cache_filepath_for_graph(graph_path)
    payload = empty_cache_payload(graph_path)
    payload["_cache_exists"] = cache_file.exists()
    payload["_stale"] = False

    if not cache_file.exists():
        return payload

    try:
        with open(cache_file, "r", encoding="utf-8") as file:
            loaded = json.load(file)
    except (json.JSONDecodeError, OSError):
        payload["_stale"] = True
        return payload

    if (
        not isinstance(loaded, dict)
        or loaded.get("schema_version") != CACHE_SCHEMA_VERSION
        or not isinstance(loaded.get("files"), dict)
    ):
        payload["_stale"] = True
        return payload

    loaded["_cache_exists"] = True
    loaded["_stale"] = False
    return loaded


def save_cache(graph_path: str, cache_data: Dict[str, Any]) -> None:
    cache_file = _get_cache_filepath_for_graph(graph_path)
    payload = build_cache_payload(graph_path, cache_data.get("files", cache_data))
    with open(cache_file, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def get_all_blocks_from_cache(cache_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    all_blocks: List[Dict[str, Any]] = []
    for file_path, file_info in cache_data.get("files", {}).items():
        blocks = file_info.get("blocks", [])
        for block in blocks:
            item = dict(block)
            item["file_path"] = file_path
            all_blocks.append(item)
    return all_blocks


def clear_graph_cache(graph_path: str) -> bool:
    cache_file = _get_cache_filepath_for_graph(graph_path)
    if cache_file.exists():
        try:
            cache_file.unlink()
            return True
        except OSError:
            return False
    return True


def clear_all_cache() -> bool:
    cache_dir = get_cache_dir()
    if cache_dir.exists():
        try:
            shutil.rmtree(cache_dir)
            return True
        except OSError:
            return False
    return True
