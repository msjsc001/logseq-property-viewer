# -*- coding: utf-8 -*-
from nicegui import ui
import nicegui_ui

def main():
    """应用主入口"""
    # 调用新UI模块中的函数来创建界面
    nicegui_ui.create_ui()
    
    # 启动NiceGUI应用
    ui.run(
        title="Logseq 属性查询工具",  # 设置窗口标题
        window_size=(1200, 800),   # 设置初始窗口大小
        native=True,               # 以独立的桌面应用模式运行
        reload=False               # 在最终版本中关闭自动重载
    )

# 这种写法是NiceGUI官方推荐的，以确保在打包成可执行文件时能正确运行
if __name__ in {"__main__", "__mp_main__"}:
    main()