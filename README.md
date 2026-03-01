# Property Query - Logseq 属性查询与统计工具 v2.2.0

[English](./README-EN.md) | 简体中文

<p align="center">
  <a href="https://github.com/msjsc001/logseq-property-viewer/releases/latest"><img src="https://img.shields.io/github/v/release/msjsc001/logseq-property-viewer"></a>
  <a href="https://github.com/msjsc001/logseq-property-viewer/commits/main"><img src="https://img.shields.io/github/last-commit/msjsc001/logseq-property-viewer"></a>
  <a href="https://github.com/msjsc001/logseq-property-viewer/releases"><img src="https://img.shields.io/github/downloads/msjsc001/logseq-property-viewer/total?label=Downloads&color=brightgreen"></a>
</p>

**这是一个独立于 Logseq 软件之外的高性能桌面工具，用于对 Logseq 知识库中的 Markdown 文件进行高级的属性查询和数据统计，** 并以现代化的图形用户界面（GUI）展示结果。它通用于所有使用 `key:: value` 格式属性的 Markdown 文件。

> **v2.2.0 新特性**：核心数据纯净隔离（支持持久存储至 APPDATA）、属性键防冲突重命名、Logseq 外部唤醒动态 URI、底层组件防宕机稳健修复等。

<img alt="image" src="https://github.com/user-attachments/assets/7c60b81e-ee34-495a-af44-d74fe5620515" />
<img alt="image" src="https://github.com/user-attachments/assets/52d54357-f851-4205-be6c-214017d51d71" />
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

## 🛠️ 开发者指南

### 1. 技术栈
- **后端**：FastAPI + Uvicorn + watchdog
- **前端**：React + TypeScript + Ant Design + ECharts + TailwindCSS
- **桌面应用**：PyWebView (无内嵌 Chromium 包袱，轻量级)
- **核心逻辑**：Python 多线程并行解析
- **打包工具**：PyInstaller (后端EXE构建)、Vite (前端构建)

### 2. 开发核心技术点
- **Markdown 属性解析**：基于正则表达式与多线程机制，能够高效并精确扫描 Logseq 知识库中符合 `key:: value` 语法的属性块。
- **智能增量缓存调度**：
  - 首屏启动时，全量扫描并构建 `cache.json` 本地缓存进行性能预热。
  - 基于 Watchdog 的操作系统底层事件监听（创建、修改、删除），实现对知识库的零轮询侦测和**增量缓存更新**，大幅节约 CPU 占用。
  - 内置防抖机制（Debounce）优雅处理密集型文件变更。
- **前后端解耦的架构设计**：
  - 本地启动 FastAPI 提供一套完整的 RESTful API 网关。
  - 使用 PyWebView 以现代无头浏览器承载基于 React 的单页应用（SPA）。
  - 支持前后端独立按需开发和热渲染。

### 3. 项目结构

```text
.
├── run_app.py          # 🚀 应用主入口 (初始化 PyWebView 和 FastAPI)
├── backend/
│   ├── main.py         # 🔧 FastAPI 后端核心服务 (路由与控制器)
│   └── file_watcher.py # 👁️ 文件系统监听器（watchdog 增量更新实现）
├── frontend/           # 🎨 React 前端代码库
│   ├── src/
│   │   ├── App.tsx     #    - 主应用与路由组件
│   │   ├── api.ts      #    - API 服务封装层
│   │   ├── i18n.tsx    #    - 国际化支持模块
│   │   └── components/ #    - 页面级业务组件 (查询、统计、设置等)
│   └── dist/           #    - npm run build 构建输出目录
├── core.py             # ⚙️ 核心数据解析与查询逻辑层
├── cache.py            # ⚡ 智能缓存管理机制
├── config.py           # 💾 本地用户配置与状态持久层
├── PropertyQuery.spec  # 📦 PyInstaller 独立程序打包配置
├── icon.ico            # 🎨 Windows 桌面应用图标
├── requirements.txt    # 📦 Python 运行依赖清单
└── README.md           # 📄 项目说明文档
```

### 4. 本地开发调试模式

确保在系统内拥有 Python 3.8+ 及 Node.js 18+ 环境。

```bash
# 激活后端并以热重载模式运行
cd backend
uvicorn main:app --reload --port 8000

# 激活前端并进行实时浏览器调试
cd frontend
npm run dev
```

### 5. API 核心功能端点

| 端点                 | 方法     | 核心功能说明                             |
| -------------------- | -------- | ---------------------------------------- |
| `/api/health`        | GET      | 探针检测应用后端存活状态                 |
| `/api/config`        | GET/POST | 系统运行参数与用户个性化配置存取         |
| `/api/build-cache`   | POST     | 销毁脏数据，触发知识库全景扫描           |
| `/api/search`        | POST     | 高级查询引擎（执行：精确/模糊/存在匹配） |
| `/api/stats`         | GET      | 全局维度下的分析统计模型下发             |
| `/api/check-updates` | GET      | 获取通过 watchdog 所捕获的本地变更文件池 |
| `/api/apply-updates` | POST     | 消费变更文件池，热更新当前内存缓存       |
| `/api/reset-all`     | POST     | 摧毁全部落盘数据与状态，执行出厂重置     |

### 6. 构建独立 EXE 可执行文件 (发布准备)

项目支持通过 PyInstaller 构建免安装的纯净版 Windows 可执行程序，该形式内部已包含运行期所有依赖环境，运行不带黑色命令行终端。

```bash
# 1. 确保已在环境中安装打包依赖工具
pip install pyinstaller pillow

# 2. 编译前端生产级代码（至关重要！否则程序将因缺失 UI 而阻断运行）
cd frontend
npm install
npm run build
cd ..

# 3. 发起产物重组构建
pyinstaller PropertyQuery.spec --clean

# 执行成功后，最终输出成果在 dist/PropertyQuery.exe，体积控制在 17-18 MB 左右
```

---

## 📝 更新日志

[👉 点击查看完整更新日志 / Click here for full changelog](./CHANGELOG.md)

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
