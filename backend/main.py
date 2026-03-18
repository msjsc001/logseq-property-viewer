# -*- coding: utf-8 -*-
import asyncio
import os
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

import cache
import config
import core
from app_constants import APP_IDENTIFIER, APP_NAME, APP_VERSION
from app_logging import get_logger
from backend.file_watcher import file_watcher
from backend.query_engine import QuerySyntaxError, search_blocks


logger = get_logger("property_query.api")
_executor = ThreadPoolExecutor(max_workers=4)


async def run_in_executor(func: Callable, *args, **kwargs):
    loop = asyncio.get_running_loop()
    if kwargs:
        return await loop.run_in_executor(_executor, partial(func, *args, **kwargs))
    return await loop.run_in_executor(_executor, func, *args)


def _rebuild_cache_sync(graph_path: str) -> Dict[str, Any]:
    files = core.scan_and_parse_graph(graph_path)
    payload = cache.build_cache_payload(graph_path, files)
    cache.save_cache(graph_path, payload)
    return {
        "payload": payload,
        "file_count": len(files),
        "indexed_file_count": sum(1 for item in files.values() if item.get("blocks")),
        "block_count": sum(len(item.get("blocks", [])) for item in files.values()),
    }


async def ensure_cache_ready(graph_path: str) -> Dict[str, Any]:
    payload = await run_in_executor(cache.load_cache, graph_path)
    if payload.get("_stale") or not payload.get("_cache_exists"):
        logger.info("Cache miss or stale cache detected for %s. Rebuilding...", graph_path)
        result = await run_in_executor(_rebuild_cache_sync, graph_path)
        return result["payload"]
    return payload


def _validate_graph_path(graph_path: str) -> str:
    if not graph_path or not Path(graph_path).is_dir():
        raise HTTPException(status_code=400, detail="Graph path not configured or invalid")
    return graph_path


def _open_directory(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(str(path))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def _clear_logs() -> None:
    log_dir = config.get_log_dir()
    if log_dir.exists():
        shutil.rmtree(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)


def _normalize_key(value: str) -> str:
    return value.casefold().replace("-", "").replace("_", "").replace(" ", "")


def _normalize_property_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _collect_property_aggregates(all_blocks: list[dict]) -> Dict[str, Any]:
    key_counter: Counter[str] = Counter()
    key_unique_values: Dict[str, set[str]] = defaultdict(set)
    key_values: Dict[str, Counter[str]] = defaultdict(Counter)
    value_counter: Counter[str] = Counter()
    value_keys: Dict[str, Counter[str]] = defaultdict(Counter)
    case_groups: Dict[str, set[str]] = defaultdict(set)
    synonym_groups: Dict[str, set[str]] = defaultdict(set)
    empty_values: Counter[str] = Counter()

    for block in all_blocks:
        for key, value in block.get("properties", {}).items():
            string_value = _normalize_property_value(value)
            key_counter[key] += 1
            key_unique_values[key].add(string_value)
            key_values[key][string_value] += 1
            value_counter[string_value] += 1
            value_keys[string_value][key] += 1
            case_groups[key.casefold()].add(key)
            synonym_groups[_normalize_key(key)].add(key)
            if not string_value.strip():
                empty_values[key] += 1

    return {
        "key_counter": key_counter,
        "key_unique_values": key_unique_values,
        "key_values": key_values,
        "value_counter": value_counter,
        "value_keys": value_keys,
        "case_groups": case_groups,
        "synonym_groups": synonym_groups,
        "empty_values": empty_values,
    }


def _build_key_stats(aggregates: Dict[str, Any]) -> list[dict]:
    key_counter: Counter[str] = aggregates["key_counter"]
    key_unique_values: Dict[str, set[str]] = aggregates["key_unique_values"]
    return [
        {
            "key": key,
            "count": count,
            "uniqueValues": len(key_unique_values.get(key, set())),
        }
        for key, count in key_counter.most_common()
    ]


def _build_key_value_distribution(aggregates: Dict[str, Any], key: str) -> Dict[str, Any]:
    key_values: Dict[str, Counter[str]] = aggregates["key_values"]
    values = [
        {"value": value, "count": count}
        for value, count in key_values.get(key, Counter()).most_common()
    ]
    return {"values": values, "total": len(values)}


def _build_global_value_stats(aggregates: Dict[str, Any]) -> Dict[str, Any]:
    value_counter: Counter[str] = aggregates["value_counter"]
    value_keys: Dict[str, Counter[str]] = aggregates["value_keys"]
    values = []
    for value, count in value_counter.most_common():
        key_counts = value_keys.get(value, Counter())
        values.append(
            {
                "value": value,
                "count": count,
                "keyCount": len(key_counts),
                "topKeys": [
                    {"key": key, "count": key_count}
                    for key, key_count in key_counts.most_common(3)
                ],
            }
        )
    return {"values": values, "total": len(values)}


def _build_value_key_distribution(aggregates: Dict[str, Any], value: str) -> Dict[str, Any]:
    value_keys: Dict[str, Counter[str]] = aggregates["value_keys"]
    keys = [
        {"key": key, "count": count}
        for key, count in value_keys.get(value, Counter()).most_common()
    ]
    return {"value": value, "keys": keys, "total": len(keys)}


def _build_diagnostics(aggregates: Dict[str, Any]) -> Dict[str, Any]:
    key_counter: Counter[str] = aggregates["key_counter"]
    key_unique_values: Dict[str, set[str]] = aggregates["key_unique_values"]
    case_groups: Dict[str, set[str]] = aggregates["case_groups"]
    synonym_groups: Dict[str, set[str]] = aggregates["synonym_groups"]
    empty_values: Counter[str] = aggregates["empty_values"]

    case_conflicts = [
        {
            "normalizedKey": normalized,
            "variants": sorted(variants),
            "count": sum(key_counter[item] for item in variants),
        }
        for normalized, variants in case_groups.items()
        if len(variants) > 1
    ]
    suspected_synonyms = [
        {"normalizedKey": normalized, "variants": sorted(variants)}
        for normalized, variants in synonym_groups.items()
        if len(variants) > 1
    ]
    low_signal_keys = [
        {
            "key": key,
            "count": count,
            "uniqueValues": len(key_unique_values.get(key, set())),
        }
        for key, count in key_counter.items()
        if count >= 5 and len(key_unique_values.get(key, set())) / max(count, 1) <= 0.2
    ]
    singleton_keys = [
        {"key": key, "count": count}
        for key, count in key_counter.items()
        if count == 1
    ]

    return {
        "emptyValues": [
            {"key": key, "count": count}
            for key, count in empty_values.most_common()
        ],
        "caseConflicts": sorted(case_conflicts, key=lambda item: item["count"], reverse=True),
        "suspectedSynonyms": sorted(
            suspected_synonyms,
            key=lambda item: len(item["variants"]),
            reverse=True,
        ),
        "lowSignalKeys": sorted(low_signal_keys, key=lambda item: item["count"], reverse=True),
        "singletonKeys": sorted(singleton_keys, key=lambda item: item["key"]),
    }


def _flatten_search_result(item: Dict[str, Any], index: int) -> Dict[str, Any]:
    flat_item: Dict[str, Any] = {
        "id": index,
        "page": item.get("page", ""),
        "block_content": item.get("block_content", ""),
        "content": item.get("block_content", ""),
        "file_path": item.get("file_path", ""),
        "line_start": item.get("line_start"),
        "line_end": item.get("line_end"),
        "block_path": item.get("block_path", ""),
        "properties": item.get("properties", {}),
    }
    reserved_keys = {
        "id",
        "page",
        "block_content",
        "content",
        "file_path",
        "line_start",
        "line_end",
        "block_path",
        "properties",
        "_missing",
        "key",
    }
    for key, value in item.get("properties", {}).items():
        target_key = f"prop_{key}" if key in reserved_keys else key
        flat_item[target_key] = value
    return flat_item


app = FastAPI(title=f"{APP_NAME} API", version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConfigUpdate(BaseModel):
    graph_path: str


class SearchRequest(BaseModel):
    query: str
    graph_path: Optional[str] = None
    case_sensitive: bool = False


class AutoUpdateRequest(BaseModel):
    enabled: bool


class QueryHistoryRequest(BaseModel):
    history: list[str]


class HiddenColumnsRequest(BaseModel):
    columns: list[str]


class ColumnConfigRequest(BaseModel):
    query_key: str
    config: dict[str, Any]


class SidebarStateRequest(BaseModel):
    collapsed: bool


class LanguageRequest(BaseModel):
    language: str


class QueryCaseSensitiveRequest(BaseModel):
    case_sensitive: bool


class ResetAllRequest(BaseModel):
    clear_cache: bool = True
    clear_logs: bool = True
    clear_graph_path: bool = True
    clear_preferences: bool = True
    clear_history: bool = True


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": APP_VERSION, "app": APP_IDENTIFIER}


@app.get("/api/config")
async def get_config():
    return await run_in_executor(config.load_config)


@app.post("/api/config")
async def update_config(data: ConfigUpdate):
    graph_path = data.graph_path.strip()
    if graph_path and not Path(graph_path).is_dir():
        raise HTTPException(status_code=400, detail="Invalid graph path")

    current = await run_in_executor(config.load_config)
    previous_path = current.get("graph_path", "")
    updated = await run_in_executor(config.update_config, {"graph_path": graph_path})

    if updated.get("auto_update_enabled"):
        if graph_path:
            file_watcher.start_watching(graph_path)
        else:
            file_watcher.stop_watching()
    elif previous_path and previous_path != graph_path:
        file_watcher.clear_pending_changes()

    return {
        "status": "success",
        "config": updated,
        "watching": file_watcher.is_watching(),
    }


@app.post("/api/cache/build")
async def build_cache(graph_path: str = Body(..., embed=True)):
    _validate_graph_path(graph_path)
    result = await run_in_executor(_rebuild_cache_sync, graph_path)
    return {
        "status": "success",
        "file_count": result["file_count"],
        "indexed_file_count": result["indexed_file_count"],
        "block_count": result["block_count"],
    }


@app.post("/api/cache/clear")
async def clear_cache_endpoint():
    await run_in_executor(cache.clear_all_cache)
    return {"status": "success"}


@app.post("/api/config/clear-sort-memory")
async def clear_sort_memory():
    await run_in_executor(config.clear_sort_memory)
    return {"status": "success"}


@app.post("/api/reset-all")
async def reset_all_data(data: ResetAllRequest | None = None):
    options = data or ResetAllRequest()

    if options.clear_cache:
        await run_in_executor(cache.clear_all_cache)
    if options.clear_logs:
        await run_in_executor(_clear_logs)

    await run_in_executor(
        config.reset_config,
        clear_graph_path=options.clear_graph_path,
        clear_preferences=options.clear_preferences,
        clear_history=options.clear_history,
    )

    file_watcher.stop_watching()
    file_watcher.clear_pending_changes()
    file_watcher.set_last_apply_failures([])

    return {"status": "success", "message": "所有数据已清除"}


@app.post("/api/config/auto-update")
async def set_auto_update(data: AutoUpdateRequest):
    updated = await run_in_executor(config.update_config, {"auto_update_enabled": data.enabled})
    graph_path = updated.get("graph_path", "")
    watching = False
    if data.enabled and graph_path:
        watching = file_watcher.start_watching(graph_path)
    else:
        file_watcher.stop_watching()
    return {"status": "success", "watching": watching}


@app.get("/api/check-updates")
async def check_for_updates():
    status = file_watcher.get_status()
    return {
        "needs_update": status["pending_count"] > 0,
        "changed_count": status["pending_count"],
        "watching": status["watching"],
        "enabled": status["enabled"],
        "failed_count": status["failed_count"],
        "watch_path": status["path"],
    }


@app.post("/api/apply-updates")
async def apply_incremental_updates():
    cfg = await run_in_executor(config.load_config)
    graph_path = _validate_graph_path(cfg.get("graph_path", ""))
    pending_files = file_watcher.get_pending_changes()

    if not pending_files:
        return {
            "status": "success",
            "updated_count": 0,
            "failed_count": 0,
            "skipped_count": 0,
            "failures": [],
        }

    payload = await ensure_cache_ready(graph_path)
    files = dict(payload.get("files", {}))
    updated_count = 0
    skipped_count = 0
    failures: list[str] = []

    for pending_file in pending_files:
        if not core.is_path_in_graph_scope(graph_path, pending_file):
            skipped_count += 1
            continue

        file_path = Path(pending_file)
        try:
            if not file_path.exists():
                if files.pop(str(file_path), None) is not None:
                    updated_count += 1
                else:
                    skipped_count += 1
                continue

            blocks = await run_in_executor(core.parse_file_for_properties, str(file_path))
            files[str(file_path)] = {
                "blocks": blocks,
                "mtime": file_path.stat().st_mtime,
            }
            updated_count += 1
        except Exception as exc:
            logger.exception("Incremental update failed for %s: %s", pending_file, exc)
            failures.append(str(file_path))

    await run_in_executor(cache.save_cache, graph_path, {"files": files})
    file_watcher.clear_pending_changes()
    file_watcher.set_last_apply_failures(failures)

    return {
        "status": "success",
        "updated_count": updated_count,
        "failed_count": len(failures),
        "skipped_count": skipped_count,
        "failures": failures[:10],
    }


@app.post("/api/open-data-dir")
async def open_data_dir():
    try:
        _open_directory(config.get_app_data_dir())
        return {"status": "success"}
    except Exception as exc:
        logger.exception("Failed to open data dir: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to open data directory")


@app.post("/api/open-log-dir")
async def open_log_dir():
    try:
        _open_directory(config.get_log_dir())
        return {"status": "success"}
    except Exception as exc:
        logger.exception("Failed to open log dir: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to open log directory")


@app.get("/api/preferences")
async def get_preferences():
    cfg = await run_in_executor(config.load_config)
    graph_path = cfg.get("graph_path", "")
    graph_name = Path(graph_path).name if graph_path else "main"
    return {
        "query_history": cfg.get("query_history", []),
        "global_hidden_columns": cfg.get("global_hidden_columns", []),
        "column_configs": cfg.get("column_configs", {}),
        "sidebar_collapsed": cfg.get("sidebar_collapsed", False),
        "auto_update_enabled": cfg.get("auto_update_enabled", False),
        "query_case_sensitive": cfg.get("query_case_sensitive", False),
        "graph_name": graph_name,
        "language": cfg.get("language", "zh"),
        "data_dir": str(config.get_app_data_dir()),
        "log_dir": str(config.get_log_dir()),
        "cache_version": cache.CACHE_SCHEMA_VERSION,
    }


@app.post("/api/preferences/query-history")
async def save_query_history(data: QueryHistoryRequest):
    updated = await run_in_executor(config.update_config, {"query_history": data.history[:20]})
    return {"status": "success", "history": updated.get("query_history", [])}


@app.post("/api/preferences/global-hidden-columns")
async def save_global_hidden_columns(data: HiddenColumnsRequest):
    updated = await run_in_executor(config.update_config, {"global_hidden_columns": data.columns})
    return {"status": "success", "columns": updated.get("global_hidden_columns", [])}


@app.post("/api/preferences/column-config")
async def save_column_config(data: ColumnConfigRequest):
    cfg = await run_in_executor(config.load_config)
    column_configs = dict(cfg.get("column_configs", {}))
    column_configs[data.query_key] = data.config
    await run_in_executor(config.update_config, {"column_configs": column_configs})
    return {"status": "success"}


@app.post("/api/preferences/sidebar")
async def save_sidebar_state(data: SidebarStateRequest):
    await run_in_executor(config.update_config, {"sidebar_collapsed": data.collapsed})
    return {"status": "success"}


@app.post("/api/preferences/language")
async def save_language(data: LanguageRequest):
    updated = await run_in_executor(config.set_language, data.language)
    return {"status": "success", "language": updated.get("language", "zh")}


@app.post("/api/preferences/query-case-sensitive")
async def save_query_case_sensitive(data: QueryCaseSensitiveRequest):
    updated = await run_in_executor(
        config.update_config,
        {"query_case_sensitive": data.case_sensitive},
    )
    return {
        "status": "success",
        "query_case_sensitive": updated.get("query_case_sensitive", False),
    }


@app.post("/api/search")
async def search(req: SearchRequest):
    cfg = await run_in_executor(config.load_config)
    graph_path = _validate_graph_path(req.graph_path or cfg.get("graph_path", ""))

    try:
        payload = await ensure_cache_ready(graph_path)
        all_blocks = await run_in_executor(cache.get_all_blocks_from_cache, payload)
        results = await run_in_executor(
            search_blocks,
            all_blocks,
            req.query,
            case_sensitive=req.case_sensitive,
        )
    except QuerySyntaxError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": exc.code, "message": exc.message},
        )
    except Exception as exc:
        logger.exception("Search failed: %s", exc)
        raise HTTPException(status_code=500, detail="Search failed")

    flat_results = [_flatten_search_result(item, index) for index, item in enumerate(results)]
    return {"results": flat_results, "count": len(flat_results)}


@app.get("/api/stats")
async def get_stats():
    cfg = await run_in_executor(config.load_config)
    graph_path = _validate_graph_path(cfg.get("graph_path", ""))
    payload = await ensure_cache_ready(graph_path)
    all_blocks = await run_in_executor(cache.get_all_blocks_from_cache, payload)
    aggregates = _collect_property_aggregates(all_blocks)
    keys = _build_key_stats(aggregates)
    return {"keys": keys, "total": len(keys)}


@app.get("/api/stats/values/{key}")
async def get_value_distribution(key: str):
    cfg = await run_in_executor(config.load_config)
    graph_path = _validate_graph_path(cfg.get("graph_path", ""))
    payload = await ensure_cache_ready(graph_path)
    all_blocks = await run_in_executor(cache.get_all_blocks_from_cache, payload)
    aggregates = _collect_property_aggregates(all_blocks)
    return _build_key_value_distribution(aggregates, key)


@app.get("/api/stats/global-values")
async def get_global_value_stats():
    cfg = await run_in_executor(config.load_config)
    graph_path = _validate_graph_path(cfg.get("graph_path", ""))
    payload = await ensure_cache_ready(graph_path)
    all_blocks = await run_in_executor(cache.get_all_blocks_from_cache, payload)
    aggregates = _collect_property_aggregates(all_blocks)
    return _build_global_value_stats(aggregates)


@app.get("/api/stats/value-keys")
async def get_value_key_distribution(value: str):
    cfg = await run_in_executor(config.load_config)
    graph_path = _validate_graph_path(cfg.get("graph_path", ""))
    payload = await ensure_cache_ready(graph_path)
    all_blocks = await run_in_executor(cache.get_all_blocks_from_cache, payload)
    aggregates = _collect_property_aggregates(all_blocks)
    return _build_value_key_distribution(aggregates, value)


@app.get("/api/stats/diagnostics")
async def get_stats_diagnostics():
    cfg = await run_in_executor(config.load_config)
    graph_path = _validate_graph_path(cfg.get("graph_path", ""))
    payload = await ensure_cache_ready(graph_path)
    all_blocks = await run_in_executor(cache.get_all_blocks_from_cache, payload)
    aggregates = _collect_property_aggregates(all_blocks)
    return _build_diagnostics(aggregates)


static_dir_path = os.environ.get("STATIC_FILES_PATH", str(ROOT_DIR / "frontend" / "dist"))
static_dir = Path(static_dir_path)

if static_dir.exists():
    assets_dir = static_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/")
    async def serve_root():
        return FileResponse(static_dir / "index.html")

    @app.get("/{path:path}")
    async def serve_static_or_fallback(path: str):
        if path.startswith("api/"):
            raise HTTPException(status_code=404)

        file_path = static_dir / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(static_dir / "index.html")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PROPERTY_QUERY_PORT", "8000"))
    uvicorn.run(app, host="127.0.0.1", port=port, reload=False, log_level="warning")
