# Property Query - Logseq 属性查询与统计工具 v2.1

[English](./README-EN.md) | 简体中文

<p align="center">
  <a href="https://github.com/msjsc001/logseq-property-viewer/releases/latest"><img src="https://img.shields.io/github/v/release/msjsc001/logseq-property-viewer"></a>
  <a href="https://github.com/msjsc001/logseq-property-viewer/commits/main"><img src="https://img.shields.io/github/last-commit/msjsc001/logseq-property-viewer"></a>
  <a href="https://github.com/msjsc001/logseq-property-viewer/releases"><img src="https://img.shields.io/github/downloads/msjsc001/logseq-property-viewer/total?label=Downloads&color=brightgreen"></a>
</p>

**这是一个独立于 Logseq 软件之外的高性能桌面工具，用于对 Logseq 知识库中的 Markdown 文件进行高级的属性查询和数据统计，** 并以现代化的图形用户界面（GUI）展示结果。它通用于所有使用 `key:: value` 格式属性的 Markdown 文件。

> **v2.1 新特性**：新增文件系统实时监听（零轮询）、增量更新、恢复出厂设置、全新配色方案等。

<img alt="image" src="https://github.com/user-attachments/assets/7c60b81e-ee34-495a-af44-d74fe5620515" />
<img alt="image" src="https://github.com/user-attachments/assets/21bfddf3-cadf-4ef4-bb7c-16cd93a8ffd3" />


---

## ✨ 核心功能

### 🔍 高级属性查询
- **多种匹配模式**：
  - `key:value` — 精确匹配
  - `key~value` — 模糊匹配
  - `has:key` — 存在性匹配
- **逻辑运算**：支持 `AND` / `OR` 进行复杂条件组合
- **动态表格**：
  - 列头拖拽调整顺序（拖拽 ⋮⋮ 图标）
  - 列边框拖拽调整宽度
  - 点击列头排序
  - 列配置按查询自动记忆
- **全局隐藏列**：设置全局隐藏的属性列，在所有查询中生效
- **查询历史**：自动保存最近 20 条查询记录，支持一键清空
- **数据导出**：支持 JSON 和 CSV（Excel 兼容）格式导出

### 📊 数据统计与分析
- 一键扫描知识库，统计所有属性键
- **刷新按钮**：手动刷新统计数据
- **百分比占比**：显示每个属性键的出现次数和占总数的百分比
- **属性键搜索**：实时筛选属性键列表
- **值分布分析**：
  - 图表可视化 Top 20 值分布
  - 表格显示所有值及其出现次数和占比
  - 支持值搜索快速定位

### ⚡ 智能增量缓存
- **首次加速**：全面扫描并建立缓存
- **实时监听**：使用 watchdog 文件系统监听，零轮询检测变动
- **增量更新**：仅更新有变化的文件，无需全量重建
- **手动管理**：支持手动重建和清理缓存

### 🔄 自动随数据源更新
- **文件系统监听**：基于操作系统事件，几乎不占用 CPU
- **防抖机制**：2秒内的连续变动自动合并处理
- **增量更新**：检测到变动后，只处理变化的文件
- **可视化提示**：有变动时显示绿色徽章，点击即可增量更新

### 🛡️ 数据安全
- **恢复出厂设置**：一键清除所有配置、缓存、搜索记录
- **3秒确认机制**：防止误操作的延迟确认
- **本地处理**：所有数据仅在本地处理，不上传任何数据

### 🌐 多语言支持
- 支持中文和英文界面切换

### 🎨 现代化设计
- **全新配色**：靛蓝紫主色调，简洁现代
- **侧边栏记忆**：折叠状态自动保存
- **响应式布局**：适应不同窗口大小

---

## 🚀 快速开始

### 方式一：直接使用（推荐）

下载 [Releases](../../releases) 页面的 `PropertyQuery.exe`，双击运行即可。

### 方式二：从源码运行

#### 1. 环境准备
- Python 3.8+
- Node.js 18+ (仅首次构建前端需要)

#### 2. 安装依赖

```bash
# 克隆项目
git clone https://github.com/your-username/logseq-property-viewer.git
cd logseq-property-viewer

# 创建虚拟环境（推荐）
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS

# 安装 Python 依赖
pip install -r requirements.txt

# 构建前端（首次运行或修改前端代码后）
cd frontend
npm install
npm run build
cd ..
```

#### 3. 运行程序

```bash
python run_app.py
```

程序启动后会自动打开桌面窗口。在"设置"页面中配置 Logseq 知识库路径，点击"重建缓存"后即可使用。

---

## 📦 构建 EXE 可执行文件

如需构建独立的 Windows 可执行文件：

```bash
# 安装构建工具
pip install pyinstaller pillow

# 构建 EXE（无终端窗口，带图标）
pyinstaller PropertyQuery.spec --clean

# 输出位置：dist/PropertyQuery.exe
```

**构建注意事项**：
- 确保 `frontend/dist/` 目录存在（需先执行 `npm run build`）
- 确保 `icon.ico` 图标文件存在
- 构建产物约 17-18 MB
- EXE 文件包含所有依赖，可独立运行

---

## 🛠️ 开发指南

### 项目结构

```
.
├── run_app.py          # 🚀 应用主入口
├── backend/
│   ├── main.py         # 🔧 FastAPI 后端服务
│   └── file_watcher.py # 👁️ 文件系统监听器（watchdog）
├── frontend/           # 🎨 React 前端
│   ├── src/
│   │   ├── App.tsx     #    - 主应用组件
│   │   ├── api.ts      #    - API 服务封装
│   │   ├── i18n.tsx    #    - 国际化模块
│   │   └── components/ #    - 页面组件
│   │       ├── QueryPage.tsx    # 高级查询页
│   │       ├── ChartsPage.tsx   # 数据统计页
│   │       └── SettingsPage.tsx # 设置页
│   └── dist/           #    - 生产构建输出
├── core.py             # ⚙️ 核心解析逻辑
├── cache.py            # ⚡ 智能缓存管理
├── config.py           # 💾 用户配置管理
├── PropertyQuery.spec  # 📦 PyInstaller 构建配置
├── icon.ico            # 🎨 应用图标
├── requirements.txt    # 📦 Python 依赖
└── README.md           # 📄 项目说明
```

### 技术栈

- **后端**：FastAPI + Uvicorn + watchdog
- **前端**：React + TypeScript + Ant Design + ECharts
- **桌面窗口**：PyWebView
- **核心功能**：Python 多线程并行解析

### 开发模式

```bash
# 后端开发（热重载）
cd backend
uvicorn main:app --reload --port 8000

# 前端开发（热重载）
cd frontend
npm run dev
```

### API 端点

| 端点                 | 方法     | 说明         |
| -------------------- | -------- | ------------ |
| `/api/health`        | GET      | 健康检查     |
| `/api/config`        | GET/POST | 配置管理     |
| `/api/build-cache`   | POST     | 重建缓存     |
| `/api/search`        | POST     | 属性查询     |
| `/api/stats`         | GET      | 统计数据     |
| `/api/check-updates` | GET      | 检查文件变动 |
| `/api/apply-updates` | POST     | 应用增量更新 |
| `/api/reset-all`     | POST     | 恢复出厂设置 |

---

## 📝 更新日志

### v2.1 (2024-12)
- **文件系统监听**：使用 watchdog 实现零轮询的实时监听
- **增量更新**：仅处理变动文件，无需全量重建
- **恢复出厂设置**：一键清除所有数据和配置，带3秒确认
- **全新配色**：靛蓝紫主色调，现代简洁设计
- **侧边栏记忆**：折叠状态自动保存
- **数据统计刷新**：添加手动刷新按钮
- **配置持久化**：查询历史、列配置等存储到后端配置文件
- **EXE 构建支持**：添加 PyInstaller 构建配置和自定义图标

### v2.0 (2024-12)
- **架构重构**：从 NiceGUI 迁移至 FastAPI + React 架构
- **全新 UI**：采用 Ant Design 组件库，界面更加现代美观
- **列头拖拽**：支持拖拽 ⋮⋮ 图标调整列顺序
- **列宽调整**：支持拖拽列边框调整宽度
- **百分比统计**：属性键和值分布新增占比列
- **多语言支持**：支持中文/英文切换
- **导出增强**：支持 JSON 和 CSV 格式导出
- **历史记录**：查询历史持久化保存

### v0.3
- **架构升级**：UI 模块拆分为 `ui_components` 组件包

### v0.2
- 修复"所属页面"列显示问题
- 右键复制弹窗功能

### v0.1
- 初始版本发布
- 标题栏显示版本号
- 高级属性查询列选择支持全局记忆

---

## ⚠️ 免责声明

本软件（以下简称"本工具"）以"现状"（AS IS）方式提供，不提供任何形式的明示或暗示担保，包括但不限于对适销性、特定用途适用性、不侵权、可靠性或可用性的担保。

### 使用风险

- **用户自担风险**：使用本工具的全部风险由用户自行承担。作者和贡献者不对因使用或无法使用本工具而导致的任何直接、间接、附带、特殊、惩罚性或后果性损害承担责任。
- **无保证**：作者不保证本工具的功能将满足用户的需求，不保证本工具的操作不会中断或无错误。

### 数据处理声明

- 本工具仅在本地读取和分析用户指定目录下的 Markdown 文件，**不会**上传、传输或共享任何用户数据至外部服务器。
- 用户有责任确保其有权访问和处理所指定的目录及文件。

### 第三方组件

本工具依赖第三方开源组件（如 FastAPI、React、Ant Design、watchdog 等），这些组件受其各自的许可协议约束。

### 责任豁免

在适用法律允许的最大范围内，作者、版权持有人或贡献者不对因本软件或使用本软件而产生的任何索赔、损害或其他责任承担责任。

**继续使用本工具即表示您已阅读、理解并同意本免责声明的全部条款。**
