# -*- coding: utf-8 -*-
import webbrowser
import threading
from pathlib import Path
from collections import Counter
from typing import List, Dict, Any

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.widgets import (
    Header, Footer, Button, Input, DataTable, Label, Log, Select, Static, Tabs, Checkbox, SelectionList
)
from textual.widgets._selection_list import Selection
from textual.reactive import var
from textual.binding import Binding

# 从我们创建的模块中导入函数
from core import _process_single_file
from config import load_config, save_config
# 【新增】导入缓存模块
import cache

# --- 筛选对话框 ---
class SelectionDialog(Screen):
    # ... (代码未改变，保持折叠)
    """一个模态对话框，用于选择要显示的列。"""
    def __init__(self, columns: List[str], selected: List[str]) -> None:
        self.columns = columns
        self.selected = selected
        super().__init__()
    def compose(self) -> ComposeResult:
        with Vertical(id="selection-dialog"):
            yield Label("请选择要显示的列:")
            # 【UI优化】让复选框区域可滚动，并填充可用空间
            with VerticalScroll(id="column-checkboxes-container") as vs:
                vs.styles.height = "1fr" # 关键: 使其填充剩余空间
                for i, col in enumerate(self.columns):
                    yield Checkbox(col, value=(col in self.selected), id=f"cb-{i}")
            with Horizontal(id="selection-buttons"):
                yield Button("全选", id="select-all")
                yield Button("全不选", id="deselect-all")
                yield Button("应用", variant="primary", id="apply-selection")
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "apply-selection":
            selected_labels = [cb.label.plain for cb in self.query(Checkbox) if cb.value]
            self.dismiss(selected_labels)
        elif event.button.id == "select-all":
            for cb in self.query(Checkbox):
                cb.value = True
        elif event.button.id == "deselect-all":
            for cb in self.query(Checkbox):
                cb.value = False
# --- 主应用 ---

class LogseqTUI(App):
    TITLE = "Logseq 键值查询工具 v0.3"

    DEFAULT_CSS = """
    Screen { overflow: hidden; }
    #main-container { height: 1fr; }
    #status_log { height: 6; border-top: wide $primary; }

    /* 【UI大师级重构】使用 Grid 布局彻底解决顶部拥挤问题 */
    #path-container {
        layout: grid;
        grid-size: 1 4; /* 1 行 4 列 */
        /* 列定义: 标签(auto) 输入框(弹性) 按钮1(auto) 按钮2(auto) */
        grid-columns: auto 1fr auto auto;
        height: auto;
        padding: 0 1;
        margin-bottom: 1;
    }
    #path_label {
        column-span: 1;
        width: auto;
        margin-right: 1;
        /* 垂直居中对齐 */
        height: 100%;
        align: center middle;
    }
    #path_input {
        column-span: 1;
        width: 1fr;
    }
    #build_cache_button {
        column-span: 1;
        width: auto;
        margin-left: 1;
    }
    #clear_cache_button {
        column-span: 1;
        width: auto;
        margin-left: 1;
    }

    #query-container, #stats-container, #settings-container { padding: 1; height: 100%; width: 100%; }
    /* 【UI优化】让统计页面的组件可滚动 */
    #stats-display {
        layout: grid;
        grid-size: 1 2;
        grid-columns: 2fr 1fr; /* 表格宽度是图表的两倍 */
        height: 100%; /* 让grid填满它的wrapper */
    }
    /* 这是终极方案的关键：一个固定高度的wrapper */
    #stats-display-wrapper {
        height: 1fr;
        margin-top: 1;
    }
    #results_table, #stats-table { margin-top: 1; height: 100%; }
    #stats-display, #selection-buttons { height: auto; margin-top: 1; }
    #text-chart { height: 100%; padding: 0 1; }
    Tabs { height: auto; }
    #selection-dialog { padding: 1; width: 60%; height: 80%; border: thick $primary; background: $surface; align: center middle; }
    
    #query-buttons { height: auto; margin-top: 1; }
    #query-buttons > Button { width: auto; margin-right: 1; }

    #prop-key-selection-list {
        height: 10;
        border: round $primary;
        margin-top: 1;
    }
    /* 这是确保查询表格水平滚动条正常工作的关键 */
    .table-wrapper {
        height: 1fr;
    }
    HorizontalScroll {
        scrollbar-color: $primary;
        scrollbar-color-active: $secondary;
        scrollbar-color-hover: $warning;
    }

    """

    BINDINGS = [
        Binding("q", "quit", "退出应用"),
        Binding("d", "toggle_dark", "切换主题")
    ]

    all_blocks_data = var([])
    current_search_results = var([])
    current_table_columns = var([])
    selected_table_columns = var([])
    all_prop_keys = var([]) # 【新增】存储所有属性键

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="main-container"):
            yield Tabs("高级属性查询", "数据统计与分析", "基础设置", id="main_tabs")
            
            with Vertical(id="query-container"):
                yield Label("查询语句:")
                yield Input(placeholder="例如: type:book AND has:due", id="query_input")
                with Horizontal(id="query-buttons"):
                    yield Button("开始查询", variant="primary", id="search_button")
                    yield Button("筛选显示列", id="filter_columns_button", disabled=True)
                # 【UI优化】将 DataTable 放入 HorizontalScroll 以便左右滚动
                from textual.containers import HorizontalScroll
                # 【UI终极修复】为水平滚动条创建一个弹性高度的视口
                with Vertical(classes="table-wrapper"):
                    with HorizontalScroll():
                        query_table = DataTable(id="results_table", zebra_stripes=True)
                        query_table.add_columns("所属页面", "属性")
                        yield query_table

            with Vertical(id="stats-container"):
                yield Button("扫描并分析知识库", variant="default", id="analyze_button")
                # 【修改】替换为 Input 和 SelectionList
                yield Input(placeholder="输入属性键进行联想筛选...", id="prop_key_input")
                yield SelectionList(id="prop_key_selection_list")
                
                # --- 终极三层布局方案 ---
                # 1. Wrapper: 固定高度(1fr)，提供有界视口
                with Vertical(id="stats-display-wrapper"):
                    # 2. Grid容器: 继承Wrapper的100%高度
                    with Horizontal(id="stats-display"):
                        # 3. 滚动容器，内部组件溢出时可滚动
                        with VerticalScroll():
                            stats_table = DataTable(id="stats_table")
                            stats_table.add_columns("属性值", "数量")
                            yield stats_table
                        with VerticalScroll():
                            yield Static(id="text-chart")

            with Vertical(id="settings-container"):
                yield Label("Logseq Graph 路径:", classes="setting-label")
                yield Input(placeholder="在此输入您的 Logseq Graph 绝对路径...", id="path_input")
                yield Static() # 增加一些垂直间距
                yield Label("缓存管理:", classes="setting-label")
                with Horizontal(classes="buttons-container"):
                    yield Button("建立/更新缓存", id="build_cache_button")
                    yield Button("清理所有缓存", id="clear_cache_button", variant="error")

        yield Log(id="status_log", max_lines=100)
        yield Footer()
        
    # on_tabs_tab_activated, on_mount, log_status, on_button_pressed... 等方法保持不变
    # ... 此处省略大量未改变的函数代码 ...
    
    def on_tabs_tab_activated(self, event: Tabs.TabActivated):
        # 【UI终极重构】更新 Tab 切换逻辑
        active_tab_label = event.tab.label.plain
        self.query_one("#query-container").display = (active_tab_label == "高级属性查询")
        self.query_one("#stats-container").display = (active_tab_label == "数据统计与分析")
        self.query_one("#settings-container").display = (active_tab_label == "基础设置")

    def on_mount(self) -> None:
        self.dark = False
        # 【UI终极重构】确保启动时只显示查询页面
        self.query_one("#query-container").display = True
        self.query_one("#stats-container").display = False
        self.query_one("#settings-container").display = False
        self.sort_column_key = None
        self.sort_reverse = False
        config = load_config()
        path = config.get("graph_path", "")
        self.query_one("#path_input", Input).value = path
        self.log_status("欢迎使用 Logseq 键值查询工具。")
        if Path(path).is_dir():
            self.log_status(f"检测到配置路径 '{path}', 正在后台自动分析...")
            thread = threading.Thread(target=self.run_analysis, args=(path,))
            thread.start()
        else:
            self.log_status("请先输入有效的 Logseq Graph 路径。")

    def log_status(self, message: str):
        self.query_one(Log).write_line(message)
    
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "filter_columns_button":
            dialog = SelectionDialog(self.current_table_columns, self.selected_table_columns)
            self.push_screen(dialog, self.update_filtered_columns)
            return
        
        # 【新增】处理清理缓存按钮
        if event.button.id == "clear_cache_button":
            if cache.clear_all_cache():
                self.log_status("[bold green]所有缓存已成功清理。[/]")
            else:
                self.log_status("[bold red]清理缓存失败！请检查文件权限。[/]")
            return

        path = self.query_one("#path_input", Input).value.strip()
        if not Path(path).is_dir():
            self.log_status("[bold red]错误: Logseq 路径无效或不存在！[/]")
            return
        
        for btn in self.query(Button).filter("#search_button, #analyze_button, #build_cache_button"):
            btn.disabled = True

        if event.button.id == "build_cache_button":
            self.log_status("正在启动缓存建立线程...")
            thread = threading.Thread(target=self.run_build_cache, args=(path,))
            thread.start()
        elif event.button.id == "search_button":
            query = self.query_one("#query_input", Input).value.strip()
            if not query:
                self.log_status("[bold red]错误: 查询语句不能为空！[/]")
                for btn in self.query(Button): btn.disabled = False
                return
            self.log_status(f"正在查询 '{query}'...")
            thread = threading.Thread(target=self.run_search, args=(path, query))
            thread.start()
        elif event.button.id == "analyze_button":
            self.log_status("正在手动扫描和分析知识库，请稍候...")
            thread = threading.Thread(target=self.run_analysis, args=(path,))
            thread.start()

    def update_filtered_columns(self, selected_columns: List[str]):
        if selected_columns is None: return
        self.selected_table_columns = selected_columns
        table = self.query_one("#results_table", DataTable)
        table.clear(columns=True)
        table.add_column("所属页面", key="page")
        for key in self.selected_table_columns:
            table.add_column(key, key=key)
        for item in self.current_search_results:
            row_data = [item['page']]
            for key in self.selected_table_columns:
                row_data.append(item['properties'].get(key, ""))
            table.add_row(*row_data)
        self.log_status(f"表格已更新，显示 {len(self.selected_table_columns)} 个属性列。")
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        if event.data_table.id == "results_table":
            if event.cursor_row < len(self.current_search_results):
                row_data = self.current_search_results[event.cursor_row]
                page_name = row_data['page']
                graph_name = Path(self.query_one("#path_input", Input).value).name
                uri = f"logseq://graph/{graph_name}?page={page_name}"
                try: webbrowser.open(uri); self.log_status(f"已尝试打开链接: {uri}")
                except Exception as e: self.log_status(f"[bold red]打开链接失败: {e}[/]")

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected):
        if event.data_table.id != "results_table": return
        table = event.data_table; column_key = event.column_key.value
        if self.sort_column_key == column_key: self.sort_reverse = not self.sort_reverse
        else: self.sort_column_key = column_key; self.sort_reverse = False
        def sort_key(item):
            if column_key == "page": return item.get("page", "")
            return item["properties"].get(column_key, "")
        sorted_results = sorted(self.current_search_results, key=sort_key, reverse=self.sort_reverse)
        self.current_search_results = sorted_results
        column_keys = [col.value for col in table.columns]
        table.clear()
        for item in sorted_results:
            row_data = []
            for key in column_keys:
                if key == "page": row_data.append(item.get("page", ""))
                else: row_data.append(item["properties"].get(key, ""))
            table.add_row(*row_data)
        self.log_status(f"已按 '{column_key}' 列进行 {'降序' if self.sort_reverse else '升序'} 排序。")

    def on_select_changed(self, event: Select.Changed):
        # 这个函数很快将被新的 SelectionList 逻辑取代
        selected_key = event.value
        if not selected_key: return
        self.generate_stats_for_key(selected_key)

    def on_selection_list_selected_changed(self, event: SelectionList.SelectedChanged) -> None:
        """当用户在联想列表中选择一个项目时触发。"""
        # 注意: SelectionList 允许多选, 但我们这里只处理第一个选择
        highlighted_index = event.selection_list.highlighted
        if highlighted_index is not None:
            # 【修复】通过索引安全地获取 Selection 对象，而不是直接访问 highlighted
            try:
                selected_item = event.selection_list.options[highlighted_index]
                selected_key = selected_item.value
            except IndexError:
                return # 索引越界，忽略
            # 将选中的值填回输入框，提供清晰的反馈
            self.query_one("#prop_key_input", Input).value = selected_key
            # 生成统计数据
            self.generate_stats_for_key(selected_key)
            # 可以选择清除列表的焦点
            self.query_one("#prop_key_selection_list").blur()


    def generate_stats_for_key(self, key: str):
        """为指定的属性键生成统计数据和图表。"""
        values = [block['properties'][key] for block in self.all_blocks_data if key in block['properties']]
        value_counts = Counter(values); df = sorted(value_counts.items(), key=lambda item: item[1], reverse=True)
        stats_table = self.query_one("#stats_table", DataTable); stats_table.clear()
        for value, count in df: stats_table.add_row(str(value), str(count))
        self.update_text_chart(df); self.log_status(f"已生成属性 '{key}' 的统计。")

    def update_text_chart(self, data: List, max_width=30):
        chart_text = ""
        max_val = max(item[1] for item in data) if data else 0
        for value, count in data[:15]:
            bar_len = int((count / max_val) * max_width) if max_val > 0 else 0
            bar = "█" * bar_len; chart_text += f"{str(value):<20.20} | {bar} ({count})\n"
        self.query_one("#text-chart", Static).update(chart_text)

    def _perform_search_on_cache(self, all_blocks: List[Dict], query: str) -> List[Dict]:
        """在已加载的缓存数据上执行查询逻辑。"""
        # (此处的查询逻辑是从 core.py 的 scan_and_process_files 搬移过来的)
        def evaluate_condition(properties, condition):
            condition = condition.strip()
            if condition.startswith("has:"): return condition[4:] in properties
            if '~' in condition:
                key, value = condition.split('~', 1)
                return key in properties and value.lower() in properties[key].lower()
            if ':' in condition:
                key, value = condition.split(':', 1)
                return key in properties and properties[key].strip() == value.strip('"\'')
            return False

        or_groups = [q.strip() for q in query.split(' OR ')]
        results = []
        for block_data in all_blocks:
            properties = block_data['properties']
            for group in or_groups:
                and_parts = [p.strip() for p in group.split(' AND ')]
                if all(evaluate_condition(properties, part) for part in and_parts):
                    results.append(block_data)
                    break
        return results

    def run_search(self, path: str, query: str):
        """【重构】从缓存运行搜索。"""
        try:
            # 1. 确保缓存是最新的
            self.run_build_cache(path, silent=True) # 静默更新
            
            # 2. 从缓存加载数据
            cache_data = cache.load_cache(path)
            all_blocks = cache.get_all_blocks_from_cache(cache_data)
            
            # 3. 在缓存数据上执行搜索
            results = self._perform_search_on_cache(all_blocks, query)

            # 4. 更新UI - 【状态同步修复】在这里同时更新两个页面的数据
            self.call_from_thread(self.update_analysis_results, all_blocks, path) # 先更新统计页面的总数据
            self.call_from_thread(self.update_search_results, results, path)      # 再更新查询页的筛选结果
        except Exception as e:
            self.call_from_thread(self.on_worker_error, f"查询时出错: {e}")

    def run_analysis(self, path: str):
        """【重构】从缓存运行分析。"""
        try:
            # 1. 确保缓存是最新的
            self.run_build_cache(path, silent=True) # 静默更新
            
            # 2. 从缓存加载数据
            cache_data = cache.load_cache(path)
            all_blocks = cache.get_all_blocks_from_cache(cache_data)
            
            # 3. 更新UI
            self.call_from_thread(self.update_analysis_results, all_blocks, path)
        except Exception as e:
            self.call_from_thread(self.on_worker_error, f"分析时出错: {e}")

    def update_search_results(self, results: List[Dict], path: str):
        self.log_status(f"[bold green]查询完成！找到 {len(results)} 条结果。[/]")
        table = self.query_one("#results_table", DataTable); table.clear(columns=True)
        self.current_search_results = results
        filter_button = self.query_one("#filter_columns_button", Button)
        if not results:
            filter_button.disabled = True; table.add_column("信息"); table.add_row("未找到匹配的结果。")
        else:
            filter_button.disabled = False
            all_keys = sorted(list(set(key for item in results for key in item['properties'].keys())))
            self.current_table_columns = all_keys; self.selected_table_columns = all_keys
            table.add_column("所属页面", key="page")
            for key in all_keys: table.add_column(key, key=key)
            for item in results:
                row_data = [item['page']]
                for key in all_keys: row_data.append(item['properties'].get(key, ""))
                table.add_row(*row_data)
        save_config({"graph_path": path})
        for btn in self.query(Button).filter("#search_button, #analyze_button, #build_cache_button"): btn.disabled = False

    def update_analysis_results(self, all_blocks: List[Dict], path: str):
        if self.all_blocks_data != all_blocks:
            self.all_blocks_data = all_blocks
            self.log_status(f"[bold green]分析完成！共扫描 {len(all_blocks)} 个带属性的块。[/]")
            
            # 【修改】更新新的联想输入系统
            self.all_prop_keys = sorted(Counter(key for block in all_blocks for key in block['properties'].keys()).keys())
            selection_list = self.query_one("#prop_key_selection_list", SelectionList)
            selection_list.clear_options()
            # 【修复】增加非空判断
            if self.all_prop_keys:
                selection_list.add_options([Selection(prop, prop) for prop in self.all_prop_keys])
            
            save_config({"graph_path": path})
        
        # 【状态同步修复】分析和查询都可能调用此方法，所以解锁按钮的操作移到 on_worker_done
        for btn in self.query(Button).filter("#search_button, #analyze_button, #build_cache_button"): btn.disabled = False

    def run_build_cache(self, path: str, silent=False):
        """
        后台工作线程：智能增量更新缓存。
        
        Args:
            path (str): Logseq graph 路径。
            silent (bool): 如果为 True，则只在日志中记录关键信息，避免打扰用户。
        """
        try:
            graph_path = Path(path)
            if not silent:
                self.call_from_thread(self.log_status, "正在智能检查文件变动，请稍候...")
            
            # --- 1. 加载旧缓存和扫描当前文件状态 ---
            old_cache = cache.load_cache(path)
            current_files = {str(f.relative_to(graph_path)): f for f in graph_path.rglob("*.md")}
            
            # 【功能优化】在最开始就报告文件总数
            total_files_found = len(current_files)
            if not silent:
                self.call_from_thread(self.log_status, f"知识库内共发现 {total_files_found} 个 .md 文件，开始比对...")
            
            # --- 2. 计算文件差异 ---
            old_files_set = set(old_cache.keys())
            current_files_set = set(current_files.keys())
            
            new_files = current_files_set - old_files_set
            deleted_files = old_files_set - current_files_set
            
            modified_files = set()
            potentially_modified = old_files_set.intersection(current_files_set)
            for file_key in potentially_modified:
                try:
                    cached_mtime = old_cache[file_key].get("mtime", 0)
                    current_mtime = current_files[file_key].stat().st_mtime
                    if current_mtime > cached_mtime:
                        modified_files.add(file_key)
                except FileNotFoundError:
                    # 如果在检查期间文件被删除，当作已删除文件处理
                    deleted_files.add(file_key)

            files_to_process = new_files.union(modified_files)
            
            if not files_to_process and not deleted_files:
                if not silent:
                    self.call_from_thread(self.log_status, "[bold green]缓存已是最新状态，无需更新。[/]")
                self.call_from_thread(self.on_worker_done) # 确保按钮被解锁
                return

            # --- 3. 执行增量更新 ---
            total_to_process = len(files_to_process)
            if not silent:
                self.call_from_thread(self.log_status,
                    f"检测到 {len(new_files)} 个新增, "
                    f"{len(modified_files)} 个修改, "
                    f"{len(deleted_files)} 个删除文件。"
                )
                if total_to_process > 0:
                    self.call_from_thread(self.log_status, f"正在处理 {total_to_process} 个文件...")

            new_cache_data = old_cache.copy() # 从旧缓存开始
            # 移除已删除的文件
            for file_key in deleted_files:
                new_cache_data.pop(file_key, None)

            # 处理新增和修改的文件
            processed_count = 0
            for file_key in files_to_process:
                md_file_path = graph_path / file_key
                try:
                    mtime = md_file_path.stat().st_mtime
                    blocks = _process_single_file(md_file_path)
                    new_cache_data[file_key] = {"mtime": mtime, "blocks": blocks}
                except FileNotFoundError:
                    # 文件在处理过程中被删除，忽略即可
                    new_cache_data.pop(file_key, None)
                
                processed_count += 1
                if processed_count % 20 == 0 and not silent:
                    self.call_from_thread(self.log_status, f"更新中... [ {processed_count} / {total_to_process} ]")

            # --- 4. 保存新缓存 ---
            cache.save_cache(path, new_cache_data)
            
            total_files_in_cache = len(new_cache_data)
            self.call_from_thread(self.update_cache_build_results, total_files_in_cache, silent)

        except Exception as e:
            self.call_from_thread(self.on_worker_error, f"建立缓存时出错: {e}")

    def update_cache_build_results(self, file_count: int, silent: bool):
        """
        缓存建立完成后的回调函数，在主线程中执行。
        """
        if not silent:
            self.log_status(f"[bold green]缓存更新完成！当前缓存中共有 {file_count} 个文件。[/]")
        self.on_worker_done()

    def on_worker_done(self):
        """ 一个统一的函数，用于在任何后台任务完成后解锁按钮。 """
        for btn in self.query(Button):
            btn.disabled = False
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """当联想输入框内容改变时，筛选下面的列表。"""
        if event.input.id == "prop_key_input":
            search_term = event.value.lower()
            selection_list = self.query_one("#prop_key_selection_list", SelectionList)
            
            if not search_term:
                # 如果输入框为空，显示全部
                filtered_keys = self.all_prop_keys
            else:
                # 否则，显示匹配项
                filtered_keys = [key for key in self.all_prop_keys if search_term in key.lower()]
            
            selection_list.clear_options()
            # 使用 add_option (单数) 来逐个添加
            for key in filtered_keys:
                selection_list.add_option(Selection(key, key))

    def on_worker_error(self, error: str):
        self.log_status(f"[bold red]错误: {error}[/]")
        self.on_worker_done() # 【修复】确保出错了也调用统一的方法解锁按钮
