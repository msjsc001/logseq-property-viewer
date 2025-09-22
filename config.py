# -*- coding: utf-8 -*-
import json
from pathlib import Path
from typing import Dict, Any

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