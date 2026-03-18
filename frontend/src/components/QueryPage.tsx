import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Button,
  Checkbox,
  Divider,
  Input,
  Layout,
  List,
  message,
  Modal,
  Popover,
  Radio,
  Select,
  Space,
  Table,
  Tooltip,
  Typography,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  DeleteOutlined,
  DownOutlined,
  ExportOutlined,
  HistoryOutlined,
  HolderOutlined,
  QuestionCircleOutlined,
  SearchOutlined,
  SettingOutlined,
  UpOutlined,
  AimOutlined,
} from '@ant-design/icons';
import { closestCenter, DndContext, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import type { DragEndEvent } from '@dnd-kit/core';
import { arrayMove, horizontalListSortingStrategy, SortableContext, useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Resizable } from 'react-resizable';
import type { ResizeCallbackData } from 'react-resizable';
import 'react-resizable/css/styles.css';

import { apiService, type SearchResultItem } from '../api';
import { useI18n } from '../i18n';
import { toUserMessage } from '../utils/errors';
import { buildCsvContent, stripInternalFields } from '../utils/export';


const { Content } = Layout;
const { Paragraph, Text, Title } = Typography;
const MAX_HISTORY = 20;

interface ColumnConfig {
  visibleColumns: string[];
  columnOrder: string[];
  columnWidths: Record<string, number>;
}

interface DragHandleProps {
  id: string;
  children: React.ReactNode;
}

interface ResizableTitleProps extends React.ThHTMLAttributes<HTMLTableCellElement> {
  onResize?: (event: React.SyntheticEvent<Element>, data: ResizeCallbackData) => void;
  width?: number;
}

const DEFAULT_COLUMN_PRIORITY = ['page', 'block_path', 'line_start', 'line_end', 'block_content', 'file_path'];

const DragHandle: React.FC<DragHandleProps> = ({ id, children }) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });

  return (
    <span
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
      }}
    >
      <span {...attributes} {...listeners} style={{ cursor: 'grab', marginRight: 4 }}>
        <HolderOutlined style={{ color: '#999' }} />
      </span>
      {children}
    </span>
  );
};

const ResizableTitle: React.FC<ResizableTitleProps> = ({ onResize, width, ...restProps }) => {
  if (!width || !onResize) {
    return <th {...restProps} />;
  }

  return (
    <Resizable
      width={width}
      height={0}
      handle={
        <span
          className="custom-resize-handle"
          onClick={(event) => {
            event.stopPropagation();
            event.preventDefault();
          }}
          onMouseDown={(event) => event.stopPropagation()}
        />
      }
      onResize={onResize}
      draggableOpts={{ enableUserSelectHack: false }}
    >
      <th {...restProps} style={{ ...restProps.style, position: 'relative' }} />
    </Resizable>
  );
};

function orderColumns(columns: string[]): string[] {
  const base = DEFAULT_COLUMN_PRIORITY.filter((item) => columns.includes(item));
  const remaining = columns
    .filter((item) => !base.includes(item))
    .sort((left, right) => left.localeCompare(right));
  return [...base, ...remaining];
}


const QueryPage: React.FC = () => {
  const { t } = useI18n();
  const [query, setQuery] = useState('');
  const [caseSensitive, setCaseSensitive] = useState(false);
  const [rowData, setRowData] = useState<SearchResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [allColumns, setAllColumns] = useState<string[]>([]);
  const [visibleColumns, setVisibleColumns] = useState<string[]>([]);
  const [columnOrder, setColumnOrder] = useState<string[]>([]);
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>({});
  const [columnModalOpen, setColumnModalOpen] = useState(false);
  const [queryHistory, setQueryHistory] = useState<string[]>([]);
  const [lastQuery, setLastQuery] = useState('');
  const [globalHiddenCols, setGlobalHiddenCols] = useState<string[]>([]);
  const [graphName, setGraphName] = useState('main');
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [exportFormat, setExportFormat] = useState<'json' | 'csv'>('json');

  const columnConfigsRef = useRef<Record<string, ColumnConfig>>({});
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  useEffect(() => {
    apiService
      .getPreferences()
      .then((preferences) => {
        setQueryHistory(Array.isArray(preferences.query_history) ? preferences.query_history : []);
        setGlobalHiddenCols(
          Array.isArray(preferences.global_hidden_columns) ? preferences.global_hidden_columns : [],
        );
        setCaseSensitive(Boolean(preferences.query_case_sensitive));
        if (preferences.column_configs && typeof preferences.column_configs === 'object') {
          columnConfigsRef.current = preferences.column_configs as Record<string, ColumnConfig>;
        }
        if (preferences.graph_name) {
          setGraphName(preferences.graph_name);
        }
      })
      .catch(() => {
        // Preference hydration should not block query usage.
      });
  }, []);

  const saveToHistory = useCallback((nextQuery: string) => {
    const trimmed = nextQuery.trim();
    if (!trimmed) {
      return;
    }
    setQueryHistory((previous) => {
      const history = [trimmed, ...previous.filter((item) => item !== trimmed)].slice(0, MAX_HISTORY);
      apiService.saveQueryHistory(history).catch(() => {
        // History persistence is best-effort.
      });
      return history;
    });
  }, []);

  const clearHistory = () => {
    setQueryHistory([]);
    apiService
      .saveQueryHistory([])
      .then(() => {
        message.success(t('query.clearHistorySuccess'));
      })
      .catch((error) => {
        message.error(toUserMessage(error, t('common.error')));
      });
  };

  const saveGlobalHiddenCols = (columns: string[]) => {
    setGlobalHiddenCols(columns);
    apiService.saveGlobalHiddenColumns(columns).catch(() => {
      // Global column visibility is best-effort persistence.
    });
  };

  const saveColumnConfig = useCallback((queryKey: string, config: ColumnConfig) => {
    columnConfigsRef.current[queryKey] = config;
    apiService.saveColumnConfig(queryKey, config).catch(() => {
      // Column layout persistence should not interrupt the table workflow.
    });
  }, []);

  const loadColumnConfig = useCallback((queryKey: string, defaultColumns: string[]): ColumnConfig => {
    const saved = columnConfigsRef.current[queryKey];
    if (!saved) {
      return {
        visibleColumns: defaultColumns,
        columnOrder: defaultColumns,
        columnWidths: {},
      };
    }

    const validVisible = (saved.visibleColumns || []).filter((column) => defaultColumns.includes(column));
    const validOrder = (saved.columnOrder || []).filter((column) => defaultColumns.includes(column));
    const missingColumns = defaultColumns.filter((column) => !validOrder.includes(column));

    return {
      visibleColumns: validVisible.length > 0 ? validVisible : defaultColumns,
      columnOrder: [...validOrder, ...missingColumns],
      columnWidths: saved.columnWidths || {},
    };
  }, []);

  const getColumnLabel = useCallback(
    (column: string) => {
      const columnLabels: Record<string, string> = {
        page: t('query.page'),
        block_path: t('query.blockPath'),
        line_start: t('query.lineStart'),
        line_end: t('query.lineEnd'),
        block_content: t('query.blockContent'),
        file_path: t('query.filePath'),
      };
      return columnLabels[column] || column;
    },
    [t],
  );

  const handlePageClick = useCallback(
    (pageName: string) => {
      const url = `logseq://graph/${encodeURIComponent(graphName)}?page=${encodeURIComponent(pageName)}`;
      window.open(url, '_blank');
    },
    [graphName],
  );

  const handleLocateBlock = useCallback(
    (record: SearchResultItem) => {
      handlePageClick(record.page);
      message.info(
        t('query.locateFallback', {
          line: record.line_start ?? '-',
        }),
      );
    },
    [handlePageClick, t],
  );

  const handleCopy = useCallback(
    async (value: unknown) => {
      await navigator.clipboard.writeText(String(value ?? ''));
      message.success(t('query.copySuccess'));
    },
    [t],
  );

  const handleSearch = async () => {
    const trimmed = query.trim();
    if (!trimmed) {
      message.warning(t('query.empty'));
      return;
    }

    setLoading(true);
    saveToHistory(trimmed);
    setLastQuery(trimmed);

    try {
      const response = await apiService.search(trimmed, undefined, caseSensitive);
      const results = response.results || [];
      setRowData(results);

      if (results.length === 0) {
        setAllColumns([]);
        setVisibleColumns([]);
        setColumnOrder([]);
        message.success(t('query.searchSuccess', { count: response.count }));
        return;
      }

      const keys = new Set<string>();
      results.forEach((item) => {
        Object.keys(item).forEach((key) => {
          if (!['id', 'content', 'properties'].includes(key)) {
            keys.add(key);
          }
        });
      });

      const sortedColumns = orderColumns(Array.from(keys));
      const savedConfig = loadColumnConfig(trimmed, sortedColumns);
      setAllColumns(sortedColumns);
      setVisibleColumns(savedConfig.visibleColumns);
      setColumnOrder(savedConfig.columnOrder);
      setColumnWidths(savedConfig.columnWidths);
      message.success(t('query.searchSuccess', { count: response.count }));
    } catch (error) {
      message.error(toUserMessage(error, t('query.searchError')));
    } finally {
      setLoading(false);
    }
  };

  const toggleCaseSensitive = useCallback(() => {
    setCaseSensitive((previous) => {
      const next = !previous;
      apiService.saveQueryCaseSensitive(next).catch(() => {
        // Search preference persistence is best-effort.
      });
      return next;
    });
  }, []);

  const handleCaseSensitiveKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLSpanElement>) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        toggleCaseSensitive();
      }
    },
    [toggleCaseSensitive],
  );

  const applyColumnConfig = () => {
    setColumnModalOpen(false);
    if (lastQuery) {
      saveColumnConfig(lastQuery, { visibleColumns, columnOrder, columnWidths });
    }
    message.success(t('query.columnsSaved'));
  };

  const moveColumn = (index: number, direction: 'up' | 'down') => {
    const nextOrder = [...columnOrder];
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= nextOrder.length) {
      return;
    }
    [nextOrder[index], nextOrder[targetIndex]] = [nextOrder[targetIndex], nextOrder[index]];
    setColumnOrder(nextOrder);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) {
      return;
    }
    const orderedVisible = columnOrder.filter((column) => visibleColumns.includes(column));
    const oldIndex = orderedVisible.indexOf(String(active.id));
    const newIndex = orderedVisible.indexOf(String(over.id));
    if (oldIndex === -1 || newIndex === -1) {
      return;
    }
    const nextVisibleOrder = arrayMove(orderedVisible, oldIndex, newIndex);
    const hiddenColumns = columnOrder.filter((column) => !visibleColumns.includes(column));
    const nextOrder = [...nextVisibleOrder, ...hiddenColumns];
    setColumnOrder(nextOrder);
    if (lastQuery) {
      saveColumnConfig(lastQuery, { visibleColumns, columnOrder: nextOrder, columnWidths });
    }
  };

  const handleColumnResize = useCallback(
    (column: string) => (_event: React.SyntheticEvent<Element>, data: ResizeCallbackData) => {
      const nextWidths = { ...columnWidths, [column]: data.size.width };
      setColumnWidths(nextWidths);
      if (lastQuery) {
        saveColumnConfig(lastQuery, { visibleColumns, columnOrder, columnWidths: nextWidths });
      }
    },
    [columnOrder, columnWidths, lastQuery, saveColumnConfig, visibleColumns],
  );

  const handleExport = () => {
    const cleanRows = stripInternalFields(rowData);
    const headers = orderedVisibleColumns;

    let blob: Blob;
    let extension: 'json' | 'csv';
    if (exportFormat === 'json') {
      blob = new Blob([JSON.stringify(cleanRows, null, 2)], { type: 'application/json' });
      extension = 'json';
    } else {
      blob = new Blob([buildCsvContent(cleanRows, headers)], {
        type: 'text/csv;charset=utf-8;',
      });
      extension = 'csv';
    }

    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `property-query-${new Date().toISOString().slice(0, 10)}.${extension}`;
    link.click();
    URL.revokeObjectURL(url);
    setExportModalOpen(false);
    message.success(
      t('query.exportDone', {
        count: cleanRows.length,
        format: extension.toUpperCase(),
      }),
    );
  };

  const orderedVisibleColumns = useMemo(
    () => columnOrder.filter((column) => visibleColumns.includes(column) && !globalHiddenCols.includes(column)),
    [columnOrder, visibleColumns, globalHiddenCols],
  );

  const tableColumns: ColumnsType<SearchResultItem> = useMemo(() => {
    return orderedVisibleColumns.map((column) => ({
      title: <DragHandle id={column}>{getColumnLabel(column)}</DragHandle>,
      dataIndex: column,
      key: column,
      width: columnWidths[column] || (column === 'page' ? 240 : column === 'block_content' ? 320 : 170),
      sorter: (left, right) => String(left[column] ?? '').localeCompare(String(right[column] ?? '')),
      render: (value: unknown, record) => {
        if (column === 'page') {
          return (
            <Space size="small">
              <Tooltip title={t('query.pageHint')}>
                <a onClick={() => handlePageClick(record.page)} style={{ cursor: 'pointer' }}>
                  {record.page}
                </a>
              </Tooltip>
              <Tooltip title={t('query.locateHint')}>
                <Button
                  size="small"
                  icon={<AimOutlined />}
                  onClick={() => handleLocateBlock(record)}
                />
              </Tooltip>
            </Space>
          );
        }
        return (
          <Tooltip title={t('query.doubleCopy')}>
            <span
              onDoubleClick={() => {
                void handleCopy(value);
              }}
              style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}
            >
              {String(value ?? '')}
            </span>
          </Tooltip>
        );
      },
      onHeaderCell: () => ({
        width: columnWidths[column] || 150,
        onResize: handleColumnResize(column),
      }),
    }));
  }, [
    columnWidths,
    getColumnLabel,
    handleColumnResize,
    handleCopy,
    handleLocateBlock,
    handlePageClick,
    orderedVisibleColumns,
    t,
  ]);

  const helpContent = (
    <div style={{ maxWidth: 360 }}>
      <Paragraph strong>{t('query.helpSyntax')}</Paragraph>
      <ul style={{ paddingLeft: 20, margin: 0 }}>
        <li>
          <Text code>key:value</Text> - <Text strong>{t('query.helpExactMode')}</Text>：{t('query.helpExact')}
        </li>
        <li>
          <Text code>key~value</Text> - <Text strong>{t('query.helpFuzzyMode')}</Text>：{t('query.helpFuzzy')}
        </li>
        <li>
          <Text code>has:key</Text> - <Text strong>{t('query.helpHasMode')}</Text>：{t('query.helpHas')}
        </li>
        <li>
          <Text code>text</Text> - <Text strong>{t('query.helpTextMode')}</Text>：{t('query.helpText')}
        </li>
      </ul>
      <Divider style={{ margin: '8px 0' }} />
      <Paragraph strong>{t('query.helpLogic')}</Paragraph>
      <ul style={{ paddingLeft: 20, margin: 0 }}>
        <li>
          <Text code>AND</Text> - {t('query.helpAnd')}
        </li>
        <li>
          <Text code>OR</Text> - {t('query.helpOr')}
        </li>
      </ul>
      <Divider style={{ margin: '8px 0' }} />
      <Paragraph strong style={{ marginBottom: 8 }}>
        {t('query.helpExample')}
      </Paragraph>
      <ul style={{ paddingLeft: 20, margin: 0 }}>
        <li>
          <Text code>has:ai-提示词</Text>
        </li>
        <li>
          <Text code>ai-提示词~提示词-书籍总结</Text>
        </li>
        <li>
          <Text code>has:时间戳 AND 案例-观察~观察-开盘</Text>
        </li>
      </ul>
    </div>
  );

  const caseSensitiveSuffix = (
    <Tooltip
      title={t('query.caseSensitiveTooltip', {
        state: caseSensitive ? t('common.on') : t('common.off'),
      })}
    >
      <span
        role="button"
        aria-label={t('query.caseSensitive')}
        aria-pressed={caseSensitive}
        tabIndex={0}
        onClick={toggleCaseSensitive}
        onKeyDown={handleCaseSensitiveKeyDown}
        style={{
          cursor: 'pointer',
          userSelect: 'none',
          fontSize: 12,
          fontWeight: 700,
          lineHeight: '18px',
          padding: '1px 6px',
          borderRadius: 4,
          color: caseSensitive ? '#1677ff' : 'rgba(0, 0, 0, 0.45)',
          backgroundColor: caseSensitive ? 'rgba(22, 119, 255, 0.12)' : 'transparent',
          border: caseSensitive ? '1px solid rgba(22, 119, 255, 0.25)' : '1px solid transparent',
        }}
      >
        Aa
      </span>
    </Tooltip>
  );

  return (
    <Layout className="h-full bg-white">
      <Content style={{ padding: '24px', display: 'flex', flexDirection: 'column', height: '100%' }}>
        <div style={{ marginBottom: 16, flexShrink: 0 }}>
          <Space align="center">
            <Title level={4} style={{ margin: 0 }}>
              {t('query.title')}
            </Title>
            <Popover content={helpContent} title={t('query.helpTitle')} trigger="click" placement="bottomLeft">
              <span role="button" aria-label={t('query.helpTitle')} style={{ display: 'inline-flex' }}>
                <QuestionCircleOutlined style={{ fontSize: 18, color: '#1890ff', cursor: 'pointer' }} />
              </span>
            </Popover>
          </Space>
          <div style={{ marginTop: 12 }}>
            <Space wrap>
              <Input
                placeholder={t('query.placeholder')}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onPressEnter={handleSearch}
                style={{ width: 430 }}
                allowClear
                suffix={caseSensitiveSuffix}
              />
              <Space.Compact>
                <Select
                  placeholder={t('query.history')}
                  style={{ width: 210 }}
                  options={queryHistory.map((item) => ({ value: item, label: item }))}
                  onChange={(value) => setQuery(value ?? '')}
                  allowClear
                  suffixIcon={<HistoryOutlined />}
                  value={undefined}
                />
                <Tooltip title={t('query.clearHistory')}>
                  <Button
                    icon={<DeleteOutlined />}
                    onClick={clearHistory}
                    disabled={queryHistory.length === 0}
                  />
                </Tooltip>
              </Space.Compact>
              <Button type="primary" icon={<SearchOutlined />} loading={loading} onClick={handleSearch}>
                {t('common.search')}
              </Button>
              <Button
                icon={<SettingOutlined />}
                onClick={() => setColumnModalOpen(true)}
                disabled={allColumns.length === 0}
              >
                {t('query.columnManage')}
              </Button>
              <Button
                icon={<ExportOutlined />}
                onClick={() => setExportModalOpen(true)}
                disabled={rowData.length === 0}
              >
                {t('query.exportData')}
              </Button>
            </Space>
          </div>
        </div>

        <div style={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={orderedVisibleColumns} strategy={horizontalListSortingStrategy}>
              <Table
                dataSource={rowData}
                columns={tableColumns}
                components={{ header: { cell: ResizableTitle } }}
                rowKey="id"
                loading={loading}
                size="small"
                scroll={{ x: 'max-content' }}
                bordered
                locale={{ emptyText: t('query.noResults') }}
                pagination={{
                  defaultPageSize: 50,
                  showSizeChanger: true,
                  showTotal: (total) => `${t('common.results')}: ${total}`,
                  pageSizeOptions: ['20', '50', '100', '200'],
                }}
              />
            </SortableContext>
          </DndContext>
        </div>

        <div style={{ marginTop: 8, color: '#999', fontSize: 12, flexShrink: 0 }}>
          {t('query.queryHelpText')} {t('query.caseSensitiveHint')}
        </div>

        <Modal
          title={t('query.columnManage')}
          open={columnModalOpen}
          onOk={applyColumnConfig}
          onCancel={() => setColumnModalOpen(false)}
          okText={t('common.save')}
          cancelText={t('common.cancel')}
          width={560}
        >
          <div style={{ marginBottom: 8 }}>
            <Button size="small" onClick={() => setVisibleColumns([...allColumns])}>
              {t('query.selectAll')}
            </Button>
            <Button size="small" onClick={() => setVisibleColumns([])} style={{ marginLeft: 8 }}>
              {t('query.selectNone')}
            </Button>
            <Button size="small" onClick={() => setColumnOrder([...allColumns])} style={{ marginLeft: 8 }}>
              {t('query.resetOrder')}
            </Button>
          </div>
          <Divider style={{ margin: '8px 0' }} />
          <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>
            {t('query.globalHideHint')}
          </Text>
          <List
            size="small"
            bordered
            dataSource={columnOrder}
            style={{ maxHeight: 350, overflowY: 'auto' }}
            renderItem={(column, index) => (
              <List.Item
                style={{
                  padding: '8px 12px',
                  backgroundColor:
                    visibleColumns.includes(column) && !globalHiddenCols.includes(column) ? '#fff' : '#f5f5f5',
                }}
                actions={[
                  <Tooltip key={`${column}-global`} title={t('query.globalHide')}>
                    <Checkbox
                      checked={globalHiddenCols.includes(column)}
                      onChange={(event) => {
                        if (event.target.checked) {
                          saveGlobalHiddenCols([...globalHiddenCols, column]);
                        } else {
                          saveGlobalHiddenCols(globalHiddenCols.filter((item) => item !== column));
                        }
                      }}
                    >
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {t('query.globalHide')}
                      </Text>
                    </Checkbox>
                  </Tooltip>,
                  <Button
                    key={`${column}-up`}
                    size="small"
                    icon={<UpOutlined />}
                    disabled={index === 0}
                    onClick={() => moveColumn(index, 'up')}
                  />,
                  <Button
                    key={`${column}-down`}
                    size="small"
                    icon={<DownOutlined />}
                    disabled={index === columnOrder.length - 1}
                    onClick={() => moveColumn(index, 'down')}
                  />,
                ]}
              >
                <Checkbox
                  checked={visibleColumns.includes(column)}
                  onChange={(event) => {
                    if (event.target.checked) {
                      setVisibleColumns([...visibleColumns, column]);
                    } else {
                      setVisibleColumns(visibleColumns.filter((item) => item !== column));
                    }
                  }}
                >
                  <span style={{ fontWeight: column === 'page' ? 'bold' : 'normal' }}>
                    {getColumnLabel(column)}
                  </span>
                </Checkbox>
              </List.Item>
            )}
          />
        </Modal>

        <Modal
          title={t('query.exportData')}
          open={exportModalOpen}
          onOk={handleExport}
          onCancel={() => setExportModalOpen(false)}
          okText={t('common.export')}
          cancelText={t('common.cancel')}
          width={420}
        >
          <div style={{ marginBottom: 16 }}>
            <Text>
              {t('common.results')}: {rowData.length}
            </Text>
          </div>
          <Text strong>{t('query.exportFormat')}</Text>
          <div style={{ marginTop: 8 }}>
            <Radio.Group value={exportFormat} onChange={(event) => setExportFormat(event.target.value)}>
              <Radio value="json">{t('query.exportJson')}</Radio>
              <Radio value="csv">{t('query.exportCsv')}</Radio>
            </Radio.Group>
          </div>
        </Modal>

        <style>{`
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
      </Content>
    </Layout>
  );
};


export default QueryPage;
