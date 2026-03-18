# -*- coding: utf-8 -*-
import concurrent.futures
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List


BLOCK_BULLET_PATTERN = re.compile(r"^(?P<indent>\s*)(?:[-*+]|\d+\.)\s+(?P<text>.*)$")
PROPERTY_PATTERN = re.compile(r"^\s*([^:\n]+?)::\s*(.*)$")
EXCLUDED_DIR_NAMES = {
    ".git",
    ".idea",
    ".obsidian",
    ".vscode",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "frontend",
}


def _indent_width(indent: str) -> int:
    return len(indent.replace("\t", "    "))


def discover_scan_roots(graph_path: str) -> List[Path]:
    graph_dir = Path(graph_path)
    pages_dir = graph_dir / "pages"
    journals_dir = graph_dir / "journals"

    roots = [directory for directory in (pages_dir, journals_dir) if directory.is_dir()]
    return roots if roots else [graph_dir]


def should_exclude_directory(directory: Path, graph_root: Path) -> bool:
    if directory.name in EXCLUDED_DIR_NAMES:
        return True
    if directory.name.startswith(".") and directory != graph_root:
        return True
    return False


def iter_markdown_files(graph_path: str) -> Iterable[Path]:
    graph_root = Path(graph_path).resolve()
    seen: set[Path] = set()

    for root in discover_scan_roots(graph_path):
        root = root.resolve()
        if not root.exists():
            continue

        for path in root.rglob("*.md"):
            if path in seen:
                continue
            relative_parts = path.relative_to(graph_root).parts if path.is_relative_to(graph_root) else ()
            if any(part in EXCLUDED_DIR_NAMES for part in relative_parts[:-1]):
                continue
            if any(part.startswith(".") for part in relative_parts[:-1]):
                continue
            seen.add(path)
            yield path


def is_path_in_graph_scope(graph_path: str, file_path: str | Path) -> bool:
    graph_root = Path(graph_path).resolve()
    target = Path(file_path).resolve()
    if target.suffix.lower() != ".md":
        return False

    for root in discover_scan_roots(graph_path):
        try:
            target.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False


def _is_valid_property_key(key: str) -> bool:
    stripped = key.strip()
    if not stripped:
        return False
    return any(char.isalpha() for char in stripped)


def _parse_property_line(line: str) -> tuple[str, str] | None:
    match = PROPERTY_PATTERN.match(line)
    if not match:
        return None
    key = match.group(1).strip()
    value = match.group(2).strip()
    if not _is_valid_property_key(key):
        return None
    return key, value


def _extract_properties_from_line(line: str, properties: Dict[str, str]) -> bool:
    parsed = _parse_property_line(line)
    if not parsed:
        return False
    key, value = parsed
    properties[key] = value
    return True


def _create_page_properties_block(md_file: Path, page_name: str, line_number: int) -> Dict[str, Any]:
    return {
        "page": page_name,
        "file_path": str(md_file),
        "block_content": "",
        "line_start": line_number,
        "line_end": line_number,
        "block_path": page_name,
        "properties": {},
    }


def _append_block_line(block: Dict[str, Any], line: str, line_number: int) -> None:
    block["block_content"] = line if not block["block_content"] else f"{block['block_content']}\n{line}"
    block["line_end"] = line_number


def parse_file_for_properties(file_path: str) -> List[Dict[str, Any]]:
    md_file = Path(file_path)
    page_name = md_file.stem
    blocks: List[Dict[str, Any]] = []
    stack: List[Dict[str, Any]] = []
    page_properties_block: Dict[str, Any] | None = None
    allow_page_properties = True

    try:
        lines = md_file.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        lines = md_file.read_text(encoding="utf-8-sig").splitlines()

    for line_number, line in enumerate(lines, start=1):
        bullet_match = BLOCK_BULLET_PATTERN.match(line)
        if bullet_match:
            allow_page_properties = False
            indent = _indent_width(bullet_match.group("indent"))
            label = bullet_match.group("text").strip()

            while stack and indent <= stack[-1]["indent"]:
                stack.pop()

            parent_path = [item["label"] for item in stack if item["label"]]
            block = {
                "page": page_name,
                "file_path": str(md_file),
                "block_content": line,
                "line_start": line_number,
                "line_end": line_number,
                "block_path": " > ".join(parent_path + ([label] if label else [])),
                "properties": {},
                "label": label,
            }
            _extract_properties_from_line(label, block["properties"])
            blocks.append(block)
            stack.append({"indent": indent, "label": label, "block": block})
            continue

        if allow_page_properties:
            parsed_property = _parse_property_line(line)
            if parsed_property:
                if page_properties_block is None:
                    page_properties_block = _create_page_properties_block(md_file, page_name, line_number)
                    blocks.append(page_properties_block)
                key, value = parsed_property
                page_properties_block["properties"][key] = value
                _append_block_line(page_properties_block, line, line_number)
                continue
            if line.strip():
                allow_page_properties = False
            elif page_properties_block is not None and page_properties_block["block_content"]:
                _append_block_line(page_properties_block, "", line_number)
            if not stack:
                continue

        if not stack:
            continue

        current = stack[-1]["block"]
        _append_block_line(current, line, line_number)
        _extract_properties_from_line(line, current["properties"])

    for block in blocks:
        block.pop("label", None)

    return [block for block in blocks if block["properties"]]


def _process_single_file(md_file: Path) -> Dict[str, Any]:
    blocks = parse_file_for_properties(str(md_file))
    return {
        "blocks": blocks,
        "mtime": md_file.stat().st_mtime,
    }


def scan_and_parse_graph(graph_path: str) -> Dict[str, Any]:
    md_files = list(iter_markdown_files(graph_path))
    files: Dict[str, Any] = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_process_single_file, file): file for file in md_files}
        for future in concurrent.futures.as_completed(futures):
            md_file = futures[future]
            try:
                file_entry = future.result()
                files[str(md_file)] = file_entry
            except Exception:
                files[str(md_file)] = {"blocks": [], "mtime": md_file.stat().st_mtime}

    return files
