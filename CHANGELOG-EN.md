# Changelog

## v2.2.0 (2026-03)
- **Data Isolation**: Migrated all user-generated data, settings, and caching states to dedicated OS-level application data directories (e.g., `%APPDATA%\PropertyQuery` on Windows). Assured that the project directory is kept clean.
- **Data Collision Defense**: Resolved a severe dictionary collision vulnerability where Logseq notes bearing properties like `id` or `page` overwrite internal system states.
- **Dynamic URI Resolution**: Fixed an issue where the link referencing the Logseq graph was statically preset to `main` causing deep-link failure. The graph name is now dynamically extracted from the local source paths and shipped to frontend components.
- **Incremental Cache Fix**: Resurrected the API parsing logic mapping that caused the incremental build and watchdog auto-update subsystem to fail.

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
