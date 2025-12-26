# Property Query - Logseq Property Query & Statistics Tool v2.1

**A high-performance standalone desktop tool for advanced property queries and data analysis of Markdown files in Logseq knowledge bases,** presented through a modern graphical user interface (GUI). It works with any Markdown files using the `key:: value` property format.

> **v2.1 New Features**: Real-time file system monitoring (zero-polling), incremental updates, factory reset, new color scheme, and more.

![screenshot](https://github.com/user-attachments/assets/44dd628b-0520-4afa-8367-154613091f37)

---

## ✨ Core Features

### 🔍 Advanced Property Query
- **Multiple Match Modes**:
  - `key:value` — Exact match
  - `key~value` — Fuzzy match
  - `has:key` — Existence match
- **Logical Operators**: Support `AND` / `OR` for complex condition combinations
- **Dynamic Table**:
  - Drag column headers to reorder (drag the ⋮⋮ icon)
  - Drag column borders to resize
  - Click headers to sort
  - Column configuration auto-saved per query
- **Global Hidden Columns**: Set globally hidden columns that apply across all queries
- **Query History**: Auto-saves last 20 queries with one-click clear option
- **Data Export**: Export to JSON or CSV (Excel compatible) formats

### 📊 Data Statistics & Analysis
- One-click scan to analyze all property keys in your knowledge base
- **Refresh Button**: Manually refresh statistics data
- **Percentage Stats**: Display occurrence count and percentage of total for each key
- **Key Search**: Real-time filtering of property key list
- **Value Distribution**:
  - Chart visualization of Top 20 value distribution
  - Table showing all values with counts and percentages
  - Value search for quick lookup

### ⚡ Smart Incremental Cache
- **First-time Acceleration**: Full scan and cache building
- **Real-time Monitoring**: Uses watchdog for file system events, zero-polling
- **Incremental Updates**: Only update changed files, no full rebuild needed
- **Manual Control**: Rebuild or clear cache manually

### 🔄 Auto-Update with Data Source
- **File System Monitoring**: Based on OS-level events, minimal CPU usage
- **Debounce Mechanism**: Continuous changes within 2s are merged
- **Incremental Updates**: Only process changed files when updates detected
- **Visual Indicator**: Green badge shows pending changes, click to apply

### 🛡️ Data Security
- **Factory Reset**: One-click clear all config, cache, and search history
- **3-Second Confirmation**: Delayed confirmation to prevent accidents
- **Local Processing**: All data processed locally, nothing uploaded

### 🌐 Multi-language Support
- Switch between Chinese and English interfaces

### 🎨 Modern Design
- **New Color Scheme**: Indigo-purple primary color, clean and modern
- **Sidebar Memory**: Collapse state auto-saved
- **Responsive Layout**: Adapts to different window sizes

---

## 🚀 Quick Start

### Option 1: Direct Use (Recommended)

Download `PropertyQuery.exe` from the [Releases](../../releases) page and double-click to run.

### Option 2: Run from Source

#### 1. Prerequisites
- Python 3.8+
- Node.js 18+ (only needed for building frontend)

#### 2. Install Dependencies

```bash
# Clone the repository
git clone https://github.com/your-username/logseq-property-viewer.git
cd logseq-property-viewer

# Create virtual environment (recommended)
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS

# Install Python dependencies
pip install -r requirements.txt

# Build frontend (first run or after modifying frontend code)
cd frontend
npm install
npm run build
cd ..
```

#### 3. Run the Application

```bash
python run_app.py
```

The application will automatically open a desktop window. Configure your Logseq graph path in the "Settings" page, click "Rebuild Cache", and you're ready to go.

---

## 📦 Building EXE Executable

To build a standalone Windows executable:

```bash
# Install build tools
pip install pyinstaller pillow

# Build EXE (no console window, with icon)
pyinstaller PropertyQuery.spec --clean

# Output location: dist/PropertyQuery.exe
```

**Build Notes**:
- Ensure `frontend/dist/` directory exists (run `npm run build` first)
- Ensure `icon.ico` icon file exists
- Build output is approximately 17-18 MB
- EXE includes all dependencies and runs standalone

---

## 🛠️ Developer Guide

### Project Structure

```
.
├── run_app.py          # 🚀 Application entry point
├── backend/
│   ├── main.py         # 🔧 FastAPI backend service
│   └── file_watcher.py # 👁️ File system watcher (watchdog)
├── frontend/           # 🎨 React frontend
│   ├── src/
│   │   ├── App.tsx     #    - Main app component
│   │   ├── api.ts      #    - API service wrapper
│   │   ├── i18n.tsx    #    - Internationalization module
│   │   └── components/ #    - Page components
│   │       ├── QueryPage.tsx    # Advanced query page
│   │       ├── ChartsPage.tsx   # Statistics page
│   │       └── SettingsPage.tsx # Settings page
│   └── dist/           #    - Production build output
├── core.py             # ⚙️ Core parsing logic
├── cache.py            # ⚡ Smart cache management
├── config.py           # 💾 User configuration
├── PropertyQuery.spec  # 📦 PyInstaller build config
├── icon.ico            # 🎨 Application icon
├── requirements.txt    # 📦 Python dependencies
└── README.md           # 📄 Project documentation
```

### Tech Stack

- **Backend**: FastAPI + Uvicorn + watchdog
- **Frontend**: React + TypeScript + Ant Design + ECharts
- **Desktop Window**: PyWebView
- **Core Features**: Python multi-threaded parallel parsing

### Development Mode

```bash
# Backend development (hot reload)
cd backend
uvicorn main:app --reload --port 8000

# Frontend development (hot reload)
cd frontend
npm run dev
```

### API Endpoints

| Endpoint             | Method   | Description               |
| -------------------- | -------- | ------------------------- |
| `/api/health`        | GET      | Health check              |
| `/api/config`        | GET/POST | Configuration management  |
| `/api/build-cache`   | POST     | Rebuild cache             |
| `/api/search`        | POST     | Property query            |
| `/api/stats`         | GET      | Statistics data           |
| `/api/check-updates` | GET      | Check file changes        |
| `/api/apply-updates` | POST     | Apply incremental updates |
| `/api/reset-all`     | POST     | Factory reset             |

---

## 📝 Changelog

### v2.1 (2024-12)
- **File System Monitoring**: Zero-polling real-time monitoring with watchdog
- **Incremental Updates**: Only process changed files, no full rebuild
- **Factory Reset**: One-click clear all data with 3-second confirmation
- **New Color Scheme**: Indigo-purple primary color, modern and clean
- **Sidebar Memory**: Collapse state auto-saved
- **Statistics Refresh**: Added manual refresh button
- **Config Persistence**: Query history, column config stored in backend
- **EXE Build Support**: Added PyInstaller config and custom icon

### v2.0 (2024-12)
- **Architecture Overhaul**: Migrated from NiceGUI to FastAPI + React
- **New UI**: Modern interface with Ant Design component library
- **Column Drag**: Drag ⋮⋮ icon to reorder columns
- **Column Resize**: Drag column borders to adjust width
- **Percentage Stats**: Added percentage columns for keys and values
- **Multi-language**: Chinese/English interface switching
- **Enhanced Export**: JSON and CSV format support
- **History Persistence**: Query history saved across sessions

### v0.3
- **Architecture Upgrade**: UI modules split into `ui_components` package

### v0.2
- Fixed "page" column display issues
- Right-click copy popup functionality

### v0.1
- Initial release
- Version number in title bar
- Column selection with global memory for advanced queries

---

## ⚠️ Disclaimer

This software (hereinafter referred to as "the Tool") is provided "AS IS" without warranty of any kind, express or implied, including but not limited to warranties of merchantability, fitness for a particular purpose, non-infringement, reliability, or availability.

### Assumption of Risk

- **User Assumes All Risk**: You use this Tool at your own risk. The authors and contributors shall not be liable for any direct, indirect, incidental, special, punitive, or consequential damages arising from the use or inability to use this Tool.
- **No Guarantees**: The authors do not guarantee that the Tool will meet your requirements or that its operation will be uninterrupted or error-free.

### Data Processing Statement

- This Tool only reads and analyzes Markdown files in user-specified directories locally. It **does not** upload, transmit, or share any user data to external servers.
- Users are responsible for ensuring they have the right to access and process the specified directories and files.

### Third-Party Components

This Tool relies on third-party open-source components (such as FastAPI, React, Ant Design, watchdog, etc.), which are subject to their respective licenses.

### Limitation of Liability

To the maximum extent permitted by applicable law, the authors, copyright holders, or contributors shall not be liable for any claims, damages, or other liabilities arising from this software or its use.

**By continuing to use this Tool, you acknowledge that you have read, understood, and agreed to all terms of this disclaimer.**
