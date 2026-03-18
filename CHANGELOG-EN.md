# Changelog

## v2.4.0 (2026-03-18)
- **Page-Level Property Fix**: Added support for Logseq page properties placed before the first `- block`, fixing missing queries for keys such as `ai-提示词` and `提示词-经典程度`.
- **Query UX Upgrade**: Added a case-sensitive toggle, rewrote the help popover into “syntax mode + meaning + examples”, and updated examples to better match real Logseq usage.
- **Statistics Enhancement**: Added the new “Value Statistics” view so users can drill from global values into the property keys that use them.
- **Cleaner Indexing**: Filters pseudo-properties such as `--:: --` and `--2:: --` so separators no longer pollute search and statistics.
- **Release Quality**: Added regression coverage for parser, query, frontend interaction, build, and release readiness.

## v2.2.1 (2026-03)
- **Fix**: Disabled PyWebview `private_mode` default, fixing the issue where application lost persistent `localStorage` and graph path settings upon restart.

## v2.2.0 (2026-03)
- **Data Isolation**: Migrated all user-generated data, settings, and caching states to dedicated OS-level application data directories (e.g., `%APPDATA%\PropertyQuery` on Windows). Assured that the project directory is kept clean.
- **Data Collision Defense**: Resolved a severe dictionary collision vulnerability where Logseq notes bearing properties like `id` or `page` overwrite internal system states.
- **Dynamic URI Resolution**: Fixed an issue where the link referencing the Logseq graph was statically preset to `main` causing deep-link failure. The graph name is now dynamically extracted from the local source paths and shipped to frontend components.
- **Incremental Cache Fix**: Resurrected the API parsing logic mapping that caused the incremental build and watchdog auto-update subsystem to fail.
- **Data Directory Access**: Added a one-click button in the Settings page to open the OS-level application data directory for easy inspection.

## v2.1 (2024-12)
- **File System Monitoring**: Zero-polling real-time monitoring with watchdog
- **Incremental Updates**: Only process changed files, no full rebuild
- **Factory Reset**: One-click clear all data with 3-second confirmation
- **New Color Scheme**: Indigo-purple primary color, modern and clean
- **Sidebar Memory**: Collapse state auto-saved
- **Statistics Refresh**: Added manual refresh button
- **Config Persistence**: Query history, column config stored in backend
- **EXE Build Support**: Added PyInstaller config and custom icon

## v2.0 (2024-12)
- **Architecture Overhaul**: Migrated from NiceGUI to FastAPI + React
- **New UI**: Modern interface with Ant Design component library
- **Column Drag**: Drag ⋮⋮ icon to reorder columns
- **Column Resize**: Drag column borders to adjust width
- **Percentage Stats**: Added percentage columns for keys and values
- **Multi-language**: Chinese/English interface switching
- **Enhanced Export**: JSON and CSV format support
- **History Persistence**: Query history saved across sessions

## v0.3
- **Architecture Upgrade**: UI modules split into `ui_components` package

## v0.2
- Fixed "page" column display issues
- Right-click copy popup functionality

## v0.1
- Initial release
- Version number in title bar
- Column selection with global memory for advanced queries
