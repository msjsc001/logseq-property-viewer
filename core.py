# -*- coding: utf-8 -*-
import re
from pathlib import Path
from typing import List, Dict, Any, Callable
import concurrent.futures

def parse_properties(block_content: str) -> Dict[str, str]:
    """
    从单个文本块中解析出 Logseq 属性。

    Args:
        block_content (str): 单个 Logseq 文本块的内容。

    Returns:
        Dict[str, str]: 解析出的属性键值对字典。
    """
    properties = {}
    # 匹配 key:: value 格式
    pattern = re.compile(r'^\s*(\S+)::\s*(.*)')
    lines = block_content.split('\n')
    for line in lines:
        # 移除前面的 "- "
        match = pattern.match(line.lstrip('- '))
        if match:
            key, value = match.group(1).strip(), match.group(2).strip()
            # 确保键和值都存在
            if key and value:
                properties[key] = value
    return properties

def _process_single_file(md_file: Path) -> List[Dict[str, Any]]:
    """
    (内部函数) 读取并解析单个 Markdown 文件。

    Args:
        md_file (Path): 指向 .md 文件的 Path 对象。

    Returns:
        List[Dict[str, Any]]: 在该文件中找到的、包含属性的块的列表。
    """
    page_name = md_file.stem
    blocks_with_props = []
    try:
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        blocks = re.split(r'\n(?=- )', '\n' + content)

        for block_content in blocks:
            if "::" not in block_content:
                continue
            
            properties = parse_properties(block_content)
            if properties:
                blocks_with_props.append({
                    "page": page_name,
                    "content": block_content,
                    "properties": properties
                })
    except Exception:
        pass # 忽略单个文件错误
    return blocks_with_props

# 【重构】 scan_and_process_files 函数已被移除。
# 其功能现在由 ui.py 中的缓存逻辑 (run_build_cache)
# 和查询逻辑 (_perform_search_on_cache) 共同承担，
# 实现了更高效的增量更新和缓存查询。