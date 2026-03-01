import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Input, Button, Layout, message, Space, Typography, Modal, Checkbox, Divider, Select, Tooltip, Table, List, Popover, Radio } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { SearchOutlined, SettingOutlined, HistoryOutlined, LinkOutlined, ExportOutlined, UpOutlined, DownOutlined, QuestionCircleOutlined, DeleteOutlined, HolderOutlined } from '@ant-design/icons';
import { apiService } from '../api';
import type { SearchResultItem } from '../api';

// DnD Kit
import { DndContext, closestCenter, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import type { DragEndEvent } from '@dnd-kit/core';
import { arrayMove, SortableContext, horizontalListSortingStrategy, useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

// Resizable
import { Resizable } from 'react-resizable';
import type { ResizeCallbackData } from 'react-resizable';
import 'react-resizable/css/styles.css';

const { Content } = Layout;
const { Title, Text, Paragraph } = Typography;

const MAX_HISTORY = 20;

interface ColumnConfig {
    visibleColumns: string[];
    columnOrder: string[];
    columnWidths: Record<string, number>;
}

// 帮助内容
const HelpContent = () => (
    <div style={{ maxWidth: 350 }}>
        <Paragraph strong>查询语法</Paragraph>
        <ul style={{ paddingLeft: 20, margin: 0 }}>
            <li><Text code>key:value</Text> — 精确匹配</li>
            <li><Text code>key~value</Text> — 模糊匹配</li>
            <li><Text code>has:key</Text> — 存在性匹配</li>
        </ul>
        <Divider style={{ margin: '8px 0' }} />
        <Paragraph strong>逻辑运算符</Paragraph>
        <ul style={{ paddingLeft: 20, margin: 0 }}>
            <li><Text code>AND</Text> — 且（同时满足）</li>
            <li><Text code>OR</Text> — 或（满足其一）</li>
        </ul>
        <Divider style={{ margin: '8px 0' }} />
        <Text type="secondary">示例: <Text code>has:date AND status:done</Text></Text>
    </div>
);

// 可拖拽的表头单元格
interface DragHandleProps {
    id: string;
    children: React.ReactNode;
}

const DragHandle: React.FC<DragHandleProps> = ({ id, children }) => {
    const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });

    const style: React.CSSProperties = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
    };

    return (
        <span ref={setNodeRef} style={style}>
            <span {...attributes} {...listeners} style={{ cursor: 'grab', marginRight: 4 }}>
                <HolderOutlined style={{ color: '#999' }} />
            </span>
            {children}
        </span>
    );
};

// 可调整宽度的表头
const ResizableTitle = (props: any) => {
    const { onResize, width, ...restProps } = props;

    if (!width) {
        return <th {...restProps} />;
    }

    return (
        <Resizable
            width={width}
            height={0}
            handle={
                <span
                    className="custom-resize-handle"
                    onClick={(e) => {
                        e.stopPropagation();
                        e.preventDefault();
                    }}
                    onMouseDown={(e) => e.stopPropagation()}
                />
            }
            onResize={onResize}
            draggableOpts={{ enableUserSelectHack: false }}
        >
            <th {...restProps} style={{ ...restProps.style, position: 'relative' }} />
        </Resizable>
    );
};

const QueryPage: React.FC = () => {
    const [query, setQuery] = useState<string>('');
    const [rowData, setRowData] = useState<SearchResultItem[]>([]);
    const [loading, setLoading] = useState<boolean>(false);
    const [allColumns, setAllColumns] = useState<string[]>([]);
    const [visibleColumns, setVisibleColumns] = useState<string[]>([]);
    const [columnOrder, setColumnOrder] = useState<string[]>([]);
    const [columnWidths, setColumnWidths] = useState<Record<string, number>>({});
    const [columnModalOpen, setColumnModalOpen] = useState<boolean>(false);
    const [queryHistory, setQueryHistory] = useState<string[]>([]);
    const [lastQuery, setLastQuery] = useState<string>('');
    const [globalHiddenCols, setGlobalHiddenCols] = useState<string[]>([]);
    const [graphName, setGraphName] = useState<string>('main');

    // 导出对话框
    const [exportModalOpen, setExportModalOpen] = useState<boolean>(false);
    const [exportFormat, setExportFormat] = useState<'json' | 'csv'>('json');

    // DnD sensors
    const sensors = useSensors(
        useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
    );

    // 列配置引用
    const columnConfigsRef = React.useRef<Record<string, ColumnConfig>>({});

    // 从后端加载用户偏好
    useEffect(() => {
        const loadPreferences = async () => {
            try {
                const prefs = await apiService.getPreferences();
                if (prefs.query_history && Array.isArray(prefs.query_history)) {
                    setQueryHistory(prefs.query_history);
                }
                if (prefs.global_hidden_columns && Array.isArray(prefs.global_hidden_columns)) {
                    setGlobalHiddenCols(prefs.global_hidden_columns);
                }
                if (prefs.column_configs) {
                    columnConfigsRef.current = prefs.column_configs;
                }
                if (prefs.graph_name) {
                    setGraphName(prefs.graph_name);
                }
            } catch (e) {
                console.error('Failed to load preferences:', e);
            }
        };
        loadPreferences();
    }, []);

    const saveToHistory = useCallback((q: string) => {
        const trimmed = q.trim();
        if (!trimmed) return;

        setQueryHistory(prev => {
            const newHistory = [trimmed, ...prev.filter(h => h !== trimmed)].slice(0, MAX_HISTORY);
            apiService.saveQueryHistory(newHistory).catch(e => console.error('Failed to save history:', e));
            return newHistory;
        });
    }, []);

    const clearHistory = () => {
        setQueryHistory([]);
        apiService.saveQueryHistory([]).then(() => {
            message.success('历史记录已清空');
        }).catch(e => console.error('Failed to clear history:', e));
    };

    const saveGlobalHiddenCols = (cols: string[]) => {
        setGlobalHiddenCols(cols);
        apiService.saveGlobalHiddenColumns(cols).catch(e => console.error('Failed to save global hidden cols:', e));
    };

    const saveColumnConfig = useCallback((queryKey: string, config: ColumnConfig) => {
        columnConfigsRef.current[queryKey] = config;
        apiService.saveColumnConfig(queryKey, config).catch(e => console.error('Failed to save column config:', e));
    }, []);

    const loadColumnConfig = (queryKey: string, defaultCols: string[]): ColumnConfig => {
        const saved = columnConfigsRef.current[queryKey];
        if (saved) {
            const validVisible = (saved.visibleColumns || []).filter(c => defaultCols.includes(c));
            const validOrder = (saved.columnOrder || []).filter(c => defaultCols.includes(c));
            const newCols = defaultCols.filter(c => !validOrder.includes(c));
            return {
                visibleColumns: validVisible.length > 0 ? validVisible : defaultCols,
                columnOrder: [...validOrder, ...newCols],
                columnWidths: saved.columnWidths || {}
            };
        }
        return { visibleColumns: defaultCols, columnOrder: defaultCols, columnWidths: {} };
    };

    const handleSearch = async () => {
        if (!query.trim()) { message.warning('请输入查询语句'); return; }
        setLoading(true);
        saveToHistory(query);
        try {
            const res = await apiService.search(query);

            if (res.results && res.results.length > 0) {
                const keys = new Set<string>();
                res.results.forEach(item => { Object.keys(item).forEach(k => keys.add(k)); });
                keys.delete('id'); keys.delete('_missing');
                const colList = Array.from(keys);

                const sortedCols = colList.includes('page')
                    ? ['page', ...colList.filter(c => c !== 'page')]
                    : colList;

                setAllColumns(sortedCols);
                const savedConfig = loadColumnConfig(query.trim(), sortedCols);
                setVisibleColumns(savedConfig.visibleColumns);
                setColumnOrder(savedConfig.columnOrder);
                setColumnWidths(savedConfig.columnWidths);
                setLastQuery(query.trim());
            }
            setRowData(res.results || []);
            message.success(`找到 ${res.count} 条结果`);
        } catch (err) {
            console.error(err);
            message.error('查询失败');
        } finally {
            setLoading(false);
        }
    };

    const handleHistorySelect = (value: string) => { setQuery(value); };

    const applyColumnConfig = () => {
        setColumnModalOpen(false);
        if (lastQuery) {
            saveColumnConfig(lastQuery, { visibleColumns, columnOrder, columnWidths });
        }
        message.success('列设置已保存');
    };

    const moveColumn = (index: number, direction: 'up' | 'down') => {
        const newOrder = [...columnOrder];
        const targetIndex = direction === 'up' ? index - 1 : index + 1;
        if (targetIndex < 0 || targetIndex >= newOrder.length) return;
        [newOrder[index], newOrder[targetIndex]] = [newOrder[targetIndex], newOrder[index]];
        setColumnOrder(newOrder);
    };

    const handleDragEnd = (event: DragEndEvent) => {
        const { active, over } = event;
        if (over && active.id !== over.id) {
            const orderedVisible = columnOrder.filter(c => visibleColumns.includes(c));
            const oldIndex = orderedVisible.indexOf(active.id as string);
            const newIndex = orderedVisible.indexOf(over.id as string);

            if (oldIndex !== -1 && newIndex !== -1) {
                const newOrderedVisible = arrayMove(orderedVisible, oldIndex, newIndex);
                const hiddenCols = columnOrder.filter(c => !visibleColumns.includes(c));
                const newColumnOrder = [...newOrderedVisible, ...hiddenCols];
                setColumnOrder(newColumnOrder);

                if (lastQuery) {
                    saveColumnConfig(lastQuery, { visibleColumns, columnOrder: newColumnOrder, columnWidths });
                }
            }
        }
    };

    const handleColumnResize = (col: string) => (_e: React.SyntheticEvent, data: ResizeCallbackData) => {
        const newWidths = { ...columnWidths, [col]: data.size.width };
        setColumnWidths(newWidths);
        if (lastQuery) {
            saveColumnConfig(lastQuery, { visibleColumns, columnOrder, columnWidths: newWidths });
        }
    };

    const handlePageClick = (pageName: string) => {
        const url = `logseq://graph/${encodeURIComponent(graphName)}?page=${encodeURIComponent(pageName)}`;
        window.open(url, '_blank');
        message.info(`正在打开 Logseq: ${pageName} (${graphName})`);
    };

    const handleCopy = (text: string) => {
        navigator.clipboard.writeText(text);
        message.success('已复制');
    };

    const handleExportClick = () => {
        if (rowData.length === 0) { message.warning('没有数据可导出'); return; }
        setExportModalOpen(true);
    };

    const doExport = () => {
        const cleanData = rowData.map((row: any) => {
            const { id, _missing, ...rest } = row;
            return rest;
        });

        let content: string;
        let mimeType: string;
        let ext: string;

        if (exportFormat === 'json') {
            content = JSON.stringify(cleanData, null, 2);
            mimeType = 'application/json';
            ext = 'json';
        } else {
            const headers = orderedVisibleColumns;
            const csvRows = [headers.join(',')];
            cleanData.forEach((row: any) => {
                const values = headers.map((h: string) => {
                    const val = String(row[h] || '').replace(/"/g, '""');
                    return `"${val}"`;
                });
                csvRows.push(values.join(','));
            });
            content = csvRows.join('\n');
            mimeType = 'text/csv';
            ext = 'csv';
        }

        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `logseq_export_${new Date().toISOString().slice(0, 10)}.${ext}`;
        a.click();
        URL.revokeObjectURL(url);

        setExportModalOpen(false);
        message.success(`已导出 ${cleanData.length} 条数据为 ${ext.toUpperCase()}`);
    };

    const orderedVisibleColumns = useMemo(() =>
        columnOrder.filter(c => visibleColumns.includes(c) && !globalHiddenCols.includes(c)),
        [columnOrder, visibleColumns, globalHiddenCols]
    );

    const tableColumns: ColumnsType<SearchResultItem> = useMemo(() => {
        return orderedVisibleColumns.map(col => ({
            title: <DragHandle id={col}>{col}</DragHandle>,
            dataIndex: col,
            key: col,
            width: columnWidths[col] || (col === 'page' ? 200 : 150),
            sorter: (a: any, b: any) => String(a[col] || '').localeCompare(String(b[col] || '')),
            render: (text: any) => {
                if (col === 'page') {
                    return (
                        <Tooltip title="点击在 Logseq 中打开">
                            <a onClick={() => handlePageClick(text)} style={{ cursor: 'pointer' }}>{text}</a>
                        </Tooltip>
                    );
                }
                return (
                    <Tooltip title="双击复制">
                        <span
                            onDoubleClick={() => handleCopy(String(text || ''))}
                            style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}
                        >
                            {String(text || '')}
                        </span>
                    </Tooltip>
                );
            },
            onHeaderCell: (column: any) => ({
                width: column.width,
                onResize: handleColumnResize(col),
            }),
        }));
    }, [orderedVisibleColumns, columnWidths, lastQuery]);

    const components = {
        header: {
            cell: ResizableTitle,
        },
    };

    return (
        <Layout className="h-full bg-white">
            <Content style={{ padding: '24px', display: 'flex', flexDirection: 'column', height: '100%' }}>
                <div style={{ marginBottom: 16, flexShrink: 0 }}>
                    <Space align="center">
                        <Title level={4} style={{ margin: 0 }}>高级属性查询</Title>
                        <Popover content={<HelpContent />} title="查询帮助" trigger="click" placement="bottomLeft">
                            <QuestionCircleOutlined style={{ fontSize: 18, color: '#1890ff', cursor: 'pointer' }} />
                        </Popover>
                    </Space>
                    <div style={{ marginTop: 12 }}>
                        <Space wrap>
                            <Input
                                placeholder="输入查询 (如: has:date)"
                                value={query}
                                onChange={e => setQuery(e.target.value)}
                                onPressEnter={handleSearch}
                                style={{ width: 350 }}
                                allowClear
                            />
                            <Space.Compact>
                                <Select
                                    placeholder="历史记录"
                                    style={{ width: 180 }}
                                    options={queryHistory.map(h => ({ value: h, label: h }))}
                                    onChange={handleHistorySelect}
                                    allowClear
                                    suffixIcon={<HistoryOutlined />}
                                    value={undefined}
                                />
                                <Tooltip title="清空历史记录">
                                    <Button
                                        icon={<DeleteOutlined />}
                                        onClick={clearHistory}
                                        disabled={queryHistory.length === 0}
                                    />
                                </Tooltip>
                            </Space.Compact>
                            <Button type="primary" icon={<SearchOutlined />} loading={loading} onClick={handleSearch}>搜索</Button>
                            <Button icon={<SettingOutlined />} onClick={() => setColumnModalOpen(true)} disabled={allColumns.length === 0}>列管理</Button>
                            <Button icon={<ExportOutlined />} onClick={handleExportClick} disabled={rowData.length === 0}>导出</Button>
                        </Space>
                    </div>
                </div>

                <div style={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
                    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                        <SortableContext items={orderedVisibleColumns} strategy={horizontalListSortingStrategy}>
                            <Table
                                dataSource={rowData}
                                columns={tableColumns}
                                components={components}
                                rowKey={(record, index) => `${record.page || ''}_${index}`}
                                loading={loading}
                                size="small"
                                scroll={{ x: 'max-content' }}
                                bordered
                                pagination={{
                                    defaultPageSize: 50,
                                    showSizeChanger: true,
                                    showTotal: (total) => `共 ${total} 条`,
                                    pageSizeOptions: ['20', '50', '100', '200']
                                }}
                                rowClassName={(record) => record._missing ? 'row-missing' : ''}
                            />
                        </SortableContext>
                    </DndContext>
                </div>

                <div style={{ marginTop: 8, color: '#999', fontSize: 12, flexShrink: 0 }}>
                    <LinkOutlined /> 拖拽列头图标 ⋮⋮ 调整顺序 | 拖拽列边框调整宽度 | 点击 Page 跳转 Logseq | 双击复制
                </div>

                <Modal
                    title="列管理（调整显示与顺序）"
                    open={columnModalOpen}
                    onOk={applyColumnConfig}
                    onCancel={() => setColumnModalOpen(false)}
                    okText="保存"
                    cancelText="取消"
                    width={550}
                >
                    <div style={{ marginBottom: 8 }}>
                        <Button size="small" onClick={() => setVisibleColumns([...allColumns])}>全选</Button>
                        <Button size="small" onClick={() => setVisibleColumns([])} style={{ marginLeft: 8 }}>全不选</Button>
                        <Button size="small" onClick={() => setColumnOrder([...allColumns])} style={{ marginLeft: 8 }}>重置顺序</Button>
                    </div>
                    <Divider style={{ margin: '8px 0' }} />
                    <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>
                        💡 勾选"全局"将在所有查询中隐藏该列
                    </Text>
                    <List
                        size="small"
                        bordered
                        dataSource={columnOrder}
                        style={{ maxHeight: 350, overflowY: 'auto' }}
                        renderItem={(col, index) => (
                            <List.Item
                                style={{ padding: '8px 12px', backgroundColor: visibleColumns.includes(col) && !globalHiddenCols.includes(col) ? '#fff' : '#f5f5f5' }}
                                actions={[
                                    <Tooltip title="全局隐藏">
                                        <Checkbox
                                            checked={globalHiddenCols.includes(col)}
                                            onChange={e => {
                                                if (e.target.checked) {
                                                    saveGlobalHiddenCols([...globalHiddenCols, col]);
                                                } else {
                                                    saveGlobalHiddenCols(globalHiddenCols.filter(c => c !== col));
                                                }
                                            }}
                                        >
                                            <Text type="secondary" style={{ fontSize: 12 }}>全局</Text>
                                        </Checkbox>
                                    </Tooltip>,
                                    <Button size="small" icon={<UpOutlined />} disabled={index === 0} onClick={() => moveColumn(index, 'up')} />,
                                    <Button size="small" icon={<DownOutlined />} disabled={index === columnOrder.length - 1} onClick={() => moveColumn(index, 'down')} />
                                ]}
                            >
                                <Checkbox
                                    checked={visibleColumns.includes(col)}
                                    onChange={e => {
                                        if (e.target.checked) setVisibleColumns([...visibleColumns, col]);
                                        else setVisibleColumns(visibleColumns.filter(c => c !== col));
                                    }}
                                >
                                    <span style={{ fontWeight: col === 'page' ? 'bold' : 'normal' }}>{col}</span>
                                </Checkbox>
                            </List.Item>
                        )}
                    />
                </Modal>

                <Modal
                    title="导出数据"
                    open={exportModalOpen}
                    onOk={doExport}
                    onCancel={() => setExportModalOpen(false)}
                    okText="导出"
                    cancelText="取消"
                    width={400}
                >
                    <div style={{ marginBottom: 16 }}>
                        <Text>共 {rowData.length} 条数据</Text>
                    </div>
                    <div>
                        <Text strong>选择导出格式：</Text>
                        <div style={{ marginTop: 8 }}>
                            <Radio.Group value={exportFormat} onChange={e => setExportFormat(e.target.value)}>
                                <Radio value="json">JSON 格式</Radio>
                                <Radio value="csv">CSV 格式 (Excel 兼容)</Radio>
                            </Radio.Group>
                        </div>
                    </div>
                </Modal>
            </Content>

            <style>{`
                .row-missing { background-color: #ffebee !important; color: #c62828 !important; }
                .row-missing:hover { background-color: #ffcdd2 !important; }
                .react-resizable {
                    position: relative;
                    background-clip: padding-box;
                }
                .custom-resize-handle {
                    position: absolute;
                    right: 0;
                    top: 0;
                    bottom: 0;
                    width: 8px;
                    cursor: col-resize;
                    z-index: 10;
                    background: transparent;
                }
                .custom-resize-handle:hover {
                    background: rgba(24, 144, 255, 0.3);
                }
                .custom-resize-handle:active {
                    background: rgba(24, 144, 255, 0.5);
                }
                .ant-table-cell {
                    vertical-align: top;
                }
            `}</style>
        </Layout>
    );
};

export default QueryPage;
