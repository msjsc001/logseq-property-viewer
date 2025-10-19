# -*- coding: utf-8 -*-
import asyncio
from pathlib import Path
from collections import Counter
from typing import List, Dict, Any, Callable

from nicegui import ui, app

# 从项目中导入核心逻辑模块
from core import _process_single_file
from config import load_config, save_config, get_filters_for_path, save_filters_for_path, clear_filters
import cache

# --- 核心逻辑适配层 (保持不变) ---
async def run_in_executor(func, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, func, *args)

async def handle_clear_cache() -> bool:
    return await run_in_executor(cache.clear_all_cache)

def _build_cache_sync(path_str: str, log_handler: Callable[[str], None], silent: bool = False):
    graph_path = Path(path_str)
    if not silent: log_handler("正在智能检查文件变动，请稍候...")
    old_cache = cache.load_cache(path_str)
    current_files = {str(f.relative_to(graph_path)): f for f in graph_path.rglob("*.md")}
    if not silent:
        total_files_found = len(current_files)
        log_handler(f"知识库内共发现 {total_files_found} 个 .md 文件，开始比对...")
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
            deleted_files.add(file_key)
    files_to_process = new_files.union(modified_files)
    if not files_to_process and not deleted_files:
        if not silent: log_handler("缓存已是最新状态，无需更新。")
        return len(old_cache)
    if not silent:
        log_handler(f"检测到 {len(new_files)} 个新增, {len(modified_files)} 个修改, {len(deleted_files)} 个删除文件。")
    total_to_process = len(files_to_process)
    if total_to_process > 0 and not silent:
        log_handler(f"正在处理 {total_to_process} 个文件...")
    new_cache_data = old_cache.copy()
    for file_key in deleted_files:
        new_cache_data.pop(file_key, None)
    processed_count = 0
    for file_key in files_to_process:
        md_file_path = graph_path / file_key
        try:
            mtime = md_file_path.stat().st_mtime
            blocks = _process_single_file(md_file_path)
            new_cache_data[file_key] = {"mtime": mtime, "blocks": blocks}
        except FileNotFoundError:
            new_cache_data.pop(file_key, None)
        processed_count += 1
        if processed_count % 50 == 0 and not silent:
            log_handler(f"更新中... [ {processed_count} / {total_to_process} ]")
    cache.save_cache(path_str, new_cache_data)
    return len(new_cache_data)

async def handle_build_cache(path_str: str, log_handler: Callable[[str], None], silent: bool = False) -> int:
    return await run_in_executor(_build_cache_sync, path_str, log_handler, silent)

def _perform_search_on_cache(all_blocks: List[Dict], query: str) -> List[Dict]:
    def evaluate_condition(properties, condition):
        condition = condition.strip()
        if condition.startswith("has:"): return condition[4:] in properties
        if '~' in condition:
            key, value = condition.split('~', 1)
            return key in properties and value.lower() in str(properties[key]).lower()
        if ':' in condition:
            key, value = condition.split(':', 1)
            return key in properties and str(properties[key]).strip() == value.strip('"\'')
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

# --- UI 类封装 ---
class AppUI:
    def __init__(self):
        self.app_state = {
            "all_blocks_data": [], "current_search_results": [], "all_table_columns": [],
            "selected_table_columns": [], "all_prop_keys": [], "filter_seen": [], "filter_search_term": "",
        }
        self.checkboxes = []
        self.right_panel_expanded = True
        self.build_ui()

    def get_all_buttons(self):
        return [
            self.search_button, self.filter_columns_button, self.analyze_button,
            self.build_cache_button, self.clear_cache_button
        ]

    def _unique(self, seq):
        """保持顺序的去重"""
        seen = set()
        out = []
        for x in seq:
            if x not in seen:
                out.append(x)
                seen.add(x)
        return out

    def _get_current_graph_path(self) -> str:
        try:
            return self.path_input.value.strip()
        except Exception:
            return ""

    def _persist_filters(self):
        """将当前列选择持久化到配置文件"""
        path = self._get_current_graph_path()
        if not path or not Path(path).is_dir():
            return
        selected = self.app_state.get("selected_table_columns", [])
        # 优先使用缓存的 seen；若无则用当前列全集
        seen = self.app_state.get("filter_seen", self.app_state.get("all_table_columns", []))
        try:
            save_filters_for_path(path, selected, seen)
        except Exception as e:
            self.status_log.push(f"保存列过滤偏好失败: {e}")

    def on_filter_checkbox_change(self, checked: bool, col_name: str):
        """复选框变更时更新选择并持久化，并即时刷新表格"""
        selected = list(self.app_state.get("selected_table_columns", []))
        if checked:
            if col_name not in selected:
                selected.append(col_name)
        else:
            try:
                selected.remove(col_name)
            except ValueError:
                pass
        self.app_state["selected_table_columns"] = self._unique(selected)
        self._persist_filters()
        # 立即刷新结果表以反映勾选变更
        self.update_table_columns()

    def on_filter_search_change(self, e):
        """筛选对话框顶部搜索输入变更时，更新过滤关键字并重绘复选项。"""
        term = (e.value or "").strip().lower()
        self.app_state["filter_search_term"] = term
        self.update_filter_dialog()

    def open_filter_dialog(self):
        """打开筛选对话框（重置搜索关键字并重绘内容）。"""
        self.app_state["filter_search_term"] = ""
        if hasattr(self, "filter_search_input"):
            self.filter_search_input.value = ""
        self.update_filter_dialog()
        self.filter_dialog.open()

    def set_loading(self, is_loading: bool, button: ui.button = None):
        """控制所有异步操作按钮的加载状态，避免并发冲突。"""
        for btn in self.get_all_buttons():
            if is_loading:
                if btn != button:
                    btn.props('disable')
            else:
                btn.props(remove='disable')
        if button:
            if is_loading:
                button.props('loading')
            else:
                button.props(remove='loading')

    async def handle_long_operation(self, coro, button: ui.button):
        self.set_loading(True, button)
        try:
            await coro
        except Exception as e:
            self.status_log.push(f"操作失败: {e}")
            ui.notify(f'操作失败: {e}', color='negative', icon='report_problem')
        finally:
            self.set_loading(False, button)

    async def on_search_click(self, button: ui.button):
        async def search_task():
            path = self.path_input.value.strip()
            query = self.query_input.value.strip()
            if not path or not Path(path).is_dir():
                ui.notify('错误: 请先在“基础设置”中指定有效的 Logseq 路径！', color='negative', icon='warning')
                return
            if not query:
                ui.notify('错误: 查询语句不能为空！', color='negative', icon='warning')
                return
            self.status_log.push("正在静默更新缓存...")
            await handle_build_cache(path, self.status_log.push, silent=True)
            self.status_log.push(f"正在查询 '{query}'...")
            cache_data = await run_in_executor(cache.load_cache, path)
            all_blocks = await run_in_executor(cache.get_all_blocks_from_cache, cache_data)
            self.update_analysis_data(all_blocks)
            results = await run_in_executor(_perform_search_on_cache, all_blocks, query)
            
            flat_results = []
            if results:
                for i, item in enumerate(results):
                    flat_item = {'id': i, 'page': item['page'], 'content': item['content']}
                    flat_item.update(item['properties'])
                    flat_results.append(flat_item)

            self.app_state["current_search_results"] = flat_results
            self.status_log.push(f"查询完成！找到 {len(flat_results)} 条结果。")

            if not flat_results:
                self.app_state["all_table_columns"] = []
                self.app_state["selected_table_columns"] = []
                self.app_state["filter_seen"] = []
                ui.notify('未找到匹配的结果。', icon='info')
            else:
                # 计算列集合：包含 'page' 与属性列（排除 id/content）
                property_keys = sorted(list(set([key for item in flat_results for key in item.keys() if key not in ['id', 'page', 'content']])))
                all_cols = self._unique(['page'] + property_keys)
                
                # 读取历史过滤偏好并合并：新列（含 'page'）默认勾选
                filters = await run_in_executor(get_filters_for_path, path)
                selected_prev = filters.get("selected", [])
                seen_prev = filters.get("seen", [])
                
                seen_new = self._unique(list(seen_prev) + list(all_cols))
                selected_existing = [k for k in selected_prev if k in all_cols]
                new_keys_to_select = [k for k in all_cols if k not in seen_prev]
                selected_new = self._unique(selected_existing + new_keys_to_select)
                # 保证 'page' 默认选中（如果它是第一次出现）
                if 'page' in all_cols and 'page' not in seen_prev:
                    if 'page' not in selected_new:
                      selected_new.insert(0, 'page')
                elif not selected_prev and 'page' in all_cols: # 首次加载且无任何配置
                    selected_new.insert(0, 'page')
                
                self.app_state["all_table_columns"] = all_cols
                self.app_state["selected_table_columns"] = selected_new
                self.app_state["filter_seen"] = seen_new
                
                # 初次查询即写回（确保“已知道的列”被记住）
                await run_in_executor(save_filters_for_path, path, selected_new, seen_new)
                
                self.update_filter_dialog()

            self.update_table_columns()
        await self.handle_long_operation(search_task(), button)

    def update_table_columns(self):
        """动态构建 Ag-Grid 的列定义并刷新表格。"""
        column_defs = []
        selected_columns = self.app_state.get("selected_table_columns", [])
        
        for key in selected_columns:
            col_def = {
                'headerName': '所属页面' if key == 'page' else key,
                'field': key,
                'sortable': True,
                'filter': True,
                'suppressMovable': False
            }
            if key == 'page':
                col_def['headerClass'] = 'font-bold'
            column_defs.append(col_def)
        
        new_options = dict(self.results_table.options)
        new_options['columnDefs'] = column_defs
        new_options['rowData'] = self.app_state.get("current_search_results", [])
        self.results_table.options = new_options
        self.filter_columns_button.set_enabled(bool(self.app_state.get("current_search_results")))
        self.results_table.update()

    def update_filter_dialog(self):
        """重绘筛选器对话框的内容（支持顶部搜索过滤）。"""
        self.checkboxes_container.clear()
        with self.checkboxes_container:
            with ui.grid(columns=2).classes('w-full items-center'):
                ui.label('显示').classes('font-bold')
                ui.label('列名').classes('font-bold')

                all_cols = self.app_state.get("all_table_columns", [])
                selected_cols = self.app_state.get("selected_table_columns", [])
                search_term = (self.app_state.get("filter_search_term","") or "").strip().lower()

                # 确保“所属页面”列在存在结果时始终可供选择
                if self.app_state.get("current_search_results"):
                    if 'page' not in all_cols:
                        all_cols = ['page'] + [c for c in all_cols if c != 'page']
                        self.app_state["all_table_columns"] = all_cols
                    if 'page' not in selected_cols:
                        selected_cols = ['page'] + [c for c in selected_cols if c != 'page']
                        self.app_state["selected_table_columns"] = selected_cols

                def get_label(column: str) -> str:
                    return '所属页面' if column == 'page' else column

                # 保持对话框内顺序稳定，并根据搜索关键字（字段名或显示名）进行过滤
                display_cols = []
                for c in all_cols:
                    label = get_label(c)
                    if not search_term or search_term in c.lower() or search_term in label.lower():
                        display_cols.append((c, label))

                sorted_list = sorted(display_cols, key=lambda item: item[0])

                for key, label in sorted_list:
                    ui.checkbox(text="", value=(key in selected_cols)).on(
                        'update:model-value',
                        lambda e, k=key: self.on_filter_checkbox_change(bool(e.args[0]), k)
                    )
                    ui.label(label)

    async def on_build_cache_click(self, button: ui.button):
        async def build_cache_task():
            path = self.path_input.value.strip()
            if not path or not Path(path).is_dir():
                ui.notify('错误: Logseq 路径无效或不存在！', color='negative', icon='warning')
                return
            file_count = await handle_build_cache(path, self.status_log.push)
            self.status_log.push(f"缓存操作完成！当前缓存中共有 {file_count} 个文件。")
            ui.notify('缓存更新成功！', color='positive', icon='done')
            # 合并写入配置，避免覆盖 column_filters 等已存在的配置项
            existing_config = await run_in_executor(load_config)
            if not isinstance(existing_config, dict):
                existing_config = {}
            existing_config["graph_path"] = path
            await run_in_executor(save_config, existing_config)
        await self.handle_long_operation(build_cache_task(), button)

    async def on_clear_cache_click(self, button: ui.button):
        async def clear_cache_task():
            success = await handle_clear_cache()
            if success:
                # 同步清除所有列过滤偏好
                try:
                    await run_in_executor(clear_filters)
                except Exception as e:
                    self.status_log.push(f"清理列过滤偏好失败: {e}")
                self.status_log.push("所有缓存与过滤偏好已成功清理。")
                ui.notify('所有缓存与过滤偏好已成功清理。', color='positive', icon='done')
            else:
                self.status_log.push("清理缓存失败！请检查文件权限。")
                ui.notify('清理缓存失败！请检查文件权限。', color='negative', icon='report_problem')
        await self.handle_long_operation(clear_cache_task(), button)

    async def on_clear_filters_click(self, button: ui.button):
        async def clear_filters_task():
            path = self._get_current_graph_path()
            target = path if (path and Path(path).is_dir()) else None
            try:
                await run_in_executor(clear_filters, target) if target else await run_in_executor(clear_filters)
                msg = f"已清除{'当前路径' if target else '全部路径'}的高级属性查询过滤偏好。"
                self.status_log.push(msg)
                ui.notify(msg, color='warning', icon='filter_alt_off')
            except Exception as e:
                self.status_log.push(f'清理过滤偏好失败: {e}')
                ui.notify(f'清理过滤偏好失败: {e}', color='negative', icon='report_problem')
        await self.handle_long_operation(clear_filters_task(), button)

    async def on_analyze_click(self, button: ui.button):
        async def analyze_task():
            path = self.path_input.value.strip()
            if not path or not Path(path).is_dir():
                ui.notify('错误: 请先在“基础设置”中指定有效的 Logseq 路径！', color='negative', icon='warning')
                return
            self.status_log.push("正在扫描和分析知识库...")
            await handle_build_cache(path, self.status_log.push, silent=True)
            cache_data = await run_in_executor(cache.load_cache, path)
            all_blocks = await run_in_executor(cache.get_all_blocks_from_cache, cache_data)
            self.update_analysis_data(all_blocks)
            self.status_log.push(f"分析完成！共扫描 {len(all_blocks)} 个带属性的块。")
            ui.notify('知识库分析完成！', color='positive', icon='done')
        await self.handle_long_operation(analyze_task(), button)

    def update_analysis_data(self, all_blocks: List[Dict]):
        self.app_state["all_blocks_data"] = all_blocks
        all_keys = sorted(Counter(key for block in all_blocks for key in block['properties'].keys()).keys()) if all_blocks else []
        self.app_state["all_prop_keys"] = all_keys
        self.prop_key_select.options = all_keys
        self.prop_key_select.update()

    def on_prop_key_select(self, e):
        selected_key = e.value
        if not selected_key:
            self.stats_table.rows = []
            self.text_chart.set_content('')
            return
        values = [block['properties'][selected_key] for block in self.app_state["all_blocks_data"] if selected_key in block['properties']]
        value_counts = Counter(values)
        df = sorted(value_counts.items(), key=lambda item: item[1], reverse=True)
        self.stats_table.rows = [{'id': i, 'value': str(v), 'count': c} for i, (v, c) in enumerate(df)]
        self.update_text_chart(df)
        self.status_log.push(f"已生成属性 '{selected_key}' 的统计。")

    def update_text_chart(self, data: List, max_width=30):
        chart_text = ""
        max_val = max(item[1] for item in data) if data else 0
        for value, count in data[:15]:
            bar_len = int((count / max_val) * max_width) if max_val > 0 else 0
            bar = "█" * bar_len
            chart_text += f"{str(value):<20.20} | {bar} ({count})\n"
        self.text_chart.set_content(f"```\n{chart_text}\n```")

    async def on_startup(self):
        initial_config = load_config()
        initial_path = initial_config.get("graph_path", "")
        self.path_input.value = initial_path
        if Path(initial_path).is_dir():
            self.status_log.push(f"检测到配置路径 '{initial_path}', 正在后台自动分析...")
            await self.on_analyze_click(self.analyze_button)
        else:
            self.status_log.push('欢迎使用 Logseq 查询工具。请先前往“基础设置”页面配置您的知识库路径。')

    def toggle_right_panel(self):
        if self.splitter.value < 100:
            self.splitter.value = 100
            self.right_panel_expanded = False
        else:
            self.splitter.value = 70
            self.right_panel_expanded = True
        self.toggle_button.props(f'icon={"chevron_right" if self.right_panel_expanded else "chevron_left"}')

    def build_ui(self):
        ui.add_head_html("""
<style>
html, body { margin: 0; padding: 0; height: 100%; overflow: hidden; }
/* 统一开启文本选择能力 */
.enable-text-select, .enable-text-select * {
    user-select: text !important;
    -webkit-user-select: text !important;
}
/* Ag-Grid 文本选择 */
.ag-root, .ag-root-wrapper, .ag-center-cols-container, .ag-cell, .ag-header-cell {
    user-select: text !重要;
}
/* Quasar Table 文本选择 */
.q-table, .q-table__container, .q-table__grid-content, .q-table__middle, .q-table__bottom {
    user-select: text !important;
}
/* 复制提示 Toast */
#copy-toast {
  position: fixed;
  bottom: 16px;
  right: 16px;
  background: rgba(0,0,0,0.75);
  color: #fff;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  z-index: 99999;
  opacity: 0;
  transition: opacity .15s ease;
  pointer-events: none;
}
#copy-toast.show { opacity: 1; }
/* 自定义右键菜单 */
#copy-menu {
  position: fixed;
  display: none;
  flex-direction: column;
  min-width: 120px;
  background: #fff;
  border: 1px solid rgba(0,0,0,0.1);
  border-radius: 6px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.18);
  z-index: 99998;
  overflow: hidden;
}
#copy-menu button {
  padding: 8px 16px;
  background: none;
  border: none;
  text-align: left;
  font-size: 13px;
  cursor: pointer;
}
#copy-menu button:hover {
  background: rgba(33,150,243,0.08);
}
</style>
<script>
function ensureCopyToast(){
  let toast = document.getElementById('copy-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'copy-toast';
    toast.textContent = '';
    document.body.appendChild(toast);
  }
  return toast;
}
function showCopyToast(msg){
  const toast = ensureCopyToast();
  toast.textContent = msg || '已复制到剪贴板';
  toast.classList.add('show');
  setTimeout(()=> toast.classList.remove('show'), 1500);
}
function ensureCopyMenu(){
  let menu = document.getElementById('copy-menu');
  if (!menu) {
    menu = document.createElement('div');
    menu.id = 'copy-menu';
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.textContent = '复制';
    menu.appendChild(btn);
    document.body.appendChild(menu);
  }
  return menu;
}
function hideCopyMenu(){
  const menu = document.getElementById('copy-menu');
  if (menu) {
    menu.style.display = 'none';
    menu.dataset.text = '';
  }
}
/* 在指定区域启用“右键复制选中文本”的功能，弹出菜单 */
document.addEventListener('contextmenu', function(e) {
  const el = e.target.closest('.copy-on-rightclick');
  if (!el) {
    hideCopyMenu();
    return;
  }
  const selection = window.getSelection();
  const text = selection ? selection.toString().trim() : '';
  if (!text) {
    hideCopyMenu();
    return;
  }
  e.preventDefault();
  const menu = ensureCopyMenu();
  menu.dataset.text = text;
  menu.style.left = `${e.clientX}px`;
  menu.style.top = `${e.clientY}px`;
  menu.style.display = 'flex';
}, true);

document.addEventListener('click', function(e) {
  const menu = document.getElementById('copy-menu');
  if (!menu) return;
  const button = e.target.closest('#copy-menu button');
  if (button) {
    const text = menu.dataset.text || '';
    if (text) {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(()=> showCopyToast('已复制到剪贴板')).catch(()=>{});
      } else {
        try {
          const textarea = document.createElement('textarea');
          textarea.value = text;
          document.body.appendChild(textarea);
          textarea.select();
          document.execCommand('copy');
          document.body.removeChild(textarea);
          showCopyToast('已复制到剪贴板');
        } catch (_) {}
      }
    }
    hideCopyMenu();
  } else if (!e.target.closest('#copy-menu')) {
    hideCopyMenu();
  }
}, true);

document.addEventListener('scroll', hideCopyMenu, true);
window.addEventListener('resize', hideCopyMenu);
</script>
""")
        app.native.window_args['resizable'] = True
        ui.colors(primary='#1e88e5', secondary='#212121', accent='#ffab40', positive='#43a047', negative='#d32f2f')

        with ui.element('div').style('position: absolute; top: 0; left: 0; right: 0; bottom: 0;'):
            self.splitter = ui.splitter(value=70).classes('w-full h-full')
            with self.splitter:
                with self.splitter.before:
                    with ui.column().classes('w-full h-full p-4 gap-4 bg-gray-100'):
                        with ui.tabs().classes('w-full').props('align="left"') as tabs:
                            query_tab = ui.tab('高级属性查询', icon='search')
                            stats_tab = ui.tab('数据统计与分析', icon='analytics')
                            settings_tab = ui.tab('基础设置', icon='settings')
                        
                        initial_config = load_config()
                        initial_path = initial_config.get("graph_path", "")
                        initial_tab = query_tab if Path(initial_path).is_dir() else settings_tab

                        with ui.tab_panels(tabs, value=initial_tab, animated=False).classes('w-full flex-grow rounded-lg bg-white'):
                            with ui.tab_panel(query_tab).classes('h-full'):
                                with ui.column().classes('w-full p-4 gap-2 h-full'):
                                    with ui.row().classes('w-full items-center gap-2'):
                                        self.query_input = ui.input(placeholder="例如: type:book AND has:due").classes('flex-grow').props('outlined dense')
                                        self.search_button = ui.button(icon='search', on_click=lambda e: self.on_search_click(e.sender)).props('unelevated')
                                        self.filter_columns_button = ui.button(icon='filter_list', on_click=lambda: self.open_filter_dialog()).props('unelevated')
                                    
                                    aggrid_options = {
                                        'columnDefs': [],
                                        'rowData': [],
                                        'rowSelection': 'multiple',
                                        'suppressRowClickSelection': True,
                                        'domLayout': 'autoHeight',
                                        'animateRows': True,
                                    }
                                    self.results_table = ui.aggrid(aggrid_options).classes('w-full copy-on-rightclick enable-text-select').props('flat bordered')

                            with ui.tab_panel(stats_tab).classes('h-full'):
                                with ui.column().classes('w-full p-4 gap-2 h-full'):
                                    with ui.row().classes('w-full items-center gap-2'):
                                        self.analyze_button = ui.button('扫描并分析知识库', icon='update', on_click=lambda e: self.on_analyze_click(e.sender)).props('unelevated')
                                        self.prop_key_select = ui.select(options=[], label='选择属性键进行分析', with_input=True, on_change=self.on_prop_key_select).classes('flex-grow').props('outlined dense')
                                    with ui.grid(columns=2).classes('w-full mt-2 gap-4 flex-grow'):
                                        self.stats_table = ui.table(columns=[{'name': 'value', 'label': '属性值', 'field': 'value', 'sortable': True, 'align': 'left'}, {'name': 'count', 'label': '数量', 'field': 'count', 'sortable': True, 'align': 'right'}], rows=[], row_key='id').classes('w-full h-full copy-on-rightclick enable-text-select').props('flat bordered')
                                        self.text_chart = ui.markdown("").classes('p-2 border rounded-md h-full bg-gray-50 copy-on-rightclick enable-text-select').style('font-family: monospace; white-space: pre-wrap; overflow-wrap: break-word; user-select: text;')

                            with ui.tab_panel(settings_tab):
                                with ui.column().classes('w-full p-4 gap-4'):
                                    with ui.card().classes('w-full'):
                                        ui.label('Logseq Graph 路径').classes('text-lg font-semibold')
                                        self.path_input = ui.input(placeholder='在此输入您的 Logseq Graph 绝对路径...').props('outlined dense w-full').classes('w-full')
                                    with ui.card().classes('w-full'):
                                        ui.label('缓存管理').classes('text-lg font-semibold')
                                        with ui.row().classes('items-center gap-2'):
                                            self.build_cache_button = ui.button('只本路径库-建立/更新缓存', icon='save', on_click=lambda e: self.on_build_cache_click(e.sender)).props('unelevated')
                                            self.clear_filters_button = ui.button('只清理-高级属性查询-过滤', icon='filter_alt_off', on_click=lambda e: self.on_clear_filters_click(e.sender)).props('unelevated color=warning')
                                            self.clear_cache_button = ui.button('清理所有缓存', icon='delete_sweep', on_click=lambda e: self.on_clear_cache_click(e.sender)).props('unelevated color=negative')
                with self.splitter.after:
                    self.status_log = ui.log(max_lines=100).classes('w-full h-full text-sm copy-on-rightclick enable-text-select').style('user-select: text; white-space: pre-wrap; overflow-wrap: break-word;')
            
            self.toggle_button = ui.button(icon='chevron_right', on_click=self.toggle_right_panel) \
                .props('flat round dense color=primary') \
                .classes('absolute top-2 right-2 z-10 bg-white')

        with ui.dialog() as self.filter_dialog, ui.card().style('min-width: 400px;'):
            ui.label('选择要显示的列').classes('text-lg font-bold')
            with ui.row().classes('w-full items-center mt-2'):
                ui.label('搜索列').classes('text-sm')
                self.filter_search_input = ui.input(placeholder='输入关键字以过滤列名...', on_change=self.on_filter_search_change).props('outlined dense clearable').classes('flex-grow')
            
            self.checkboxes_container = ui.column().classes('w-full mt-3')
            
            with ui.row().classes('w-full justify-end mt-6'):
                ui.button('关闭', on_click=lambda: (self.filter_dialog.close(), self._persist_filters(), self.update_table_columns())).props('flat')

        self.filter_columns_button.disable()
        ui.timer(0.1, self.on_startup, once=True)

def create_ui():
    AppUI()
