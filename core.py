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
        # 移除行首的任意空白（包括\t）、可选的 "- " 以及更多的空白
        cleaned_line = re.sub(r'^\s*-\s*', '', line)
        match = pattern.match(cleaned_line)
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
    except Exception as e:
        print(f"[Core Error] Failed to process file {md_file}: {e}")
    return blocks_with_props

def scan_and_parse_graph(graph_path: str) -> Dict[str, Any]:
    """
    扫描整个 Logseq 图谱目录，解析所有 Markdown 文件并返回缓存数据结构。

    Args:
        graph_path (str): Logseq 知识库的根目录路径。

    Returns:
        Dict[str, Any]: 缓存数据，格式为 {file_path: {"blocks": [...]}, ...}
    """
    graph_dir = Path(graph_path)
    cache_data = {}
    
    # 扫描 pages 和 journals 目录
    dirs_to_scan = []
    pages_dir = graph_dir / "pages"
    journals_dir = graph_dir / "journals"
    
    if pages_dir.exists():
        dirs_to_scan.append(pages_dir)
    if journals_dir.exists():
        dirs_to_scan.append(journals_dir)
    
    # 如果没有标准目录，扫描根目录
    if not dirs_to_scan:
        dirs_to_scan.append(graph_dir)
    
    # 收集所有 Markdown 文件
    md_files = []
    for scan_dir in dirs_to_scan:
        md_files.extend(scan_dir.glob("*.md"))
    
    # 使用线程池并行处理文件
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_process_single_file, f): f for f in md_files}
        for future in concurrent.futures.as_completed(futures):
            md_file = futures[future]
            try:
                blocks = future.result()
                if blocks:
                    cache_data[str(md_file)] = {"blocks": blocks}
            except Exception as e:
                print(f"[Core Error] Failed to process {md_file}: {e}")
    
    return cache_data