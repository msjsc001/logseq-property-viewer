import React, { Suspense, lazy, useCallback, useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Empty,
  Input,
  Layout,
  message,
  Segmented,
  Space,
  Spin,
  Table,
  Tooltip,
  Typography,
} from 'antd';
import { ArrowLeftOutlined, BarChartOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

import {
  apiService,
  type DiagnosticsResponse,
  type GlobalValueStat,
  type KeyStatsItem,
  type ValueDistributionItem,
  type ValueKeyDistributionItem,
} from '../api';
import { useI18n } from '../i18n';
import { toUserMessage } from '../utils/errors';


const ReactECharts = lazy(() =>
  import('echarts-for-react').then((module) => ({ default: module.default })),
);

const { Content } = Layout;
const { Text, Title } = Typography;

type ViewMode = 'keys' | 'values' | 'diagnostics';

interface DiagnosticRow {
  [key: string]: unknown;
}

interface DiagnosticSection {
  title: string;
  data: DiagnosticRow[];
  columns: ColumnsType<DiagnosticRow>;
  rowKey: string;
}

const VALUE_CELL_STYLE = {
  display: 'inline-block',
  maxWidth: 320,
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
  verticalAlign: 'bottom',
} as const;

function formatStatValue(value: string, emptyLabel: string): string {
  return value === '' ? emptyLabel : value;
}

function toSingleLineText(value: string, emptyLabel: string): string {
  if (value === '') {
    return emptyLabel;
  }
  const singleLine = value.replace(/\s+/g, ' ').trim();
  return singleLine || emptyLabel;
}

function truncateChartLabel(label: string): string {
  return label.length > 18 ? `${label.slice(0, 18)}...` : label;
}


const ChartsPage: React.FC = () => {
  const { t } = useI18n();
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('keys');
  const [lastLoadTime, setLastLoadTime] = useState(0);

  const [keyStats, setKeyStats] = useState<KeyStatsItem[]>([]);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [keyValueStats, setKeyValueStats] = useState<ValueDistributionItem[]>([]);
  const [keySearchText, setKeySearchText] = useState('');
  const [keyValueSearchText, setKeyValueSearchText] = useState('');

  const [globalValueStats, setGlobalValueStats] = useState<GlobalValueStat[]>([]);
  const [selectedValue, setSelectedValue] = useState<string | null>(null);
  const [valueKeyStats, setValueKeyStats] = useState<ValueKeyDistributionItem[]>([]);
  const [globalValueSearchText, setGlobalValueSearchText] = useState('');
  const [valueKeySearchText, setValueKeySearchText] = useState('');

  const [diagnostics, setDiagnostics] = useState<DiagnosticsResponse | null>(null);

  const emptyValueLabel = t('charts.emptyValue');

  const renderValueCell = useCallback(
    (value: string) => {
      const fullText = formatStatValue(value, emptyValueLabel);
      const singleLine = toSingleLineText(value, emptyValueLabel);
      return (
        <Tooltip title={<span style={{ whiteSpace: 'pre-wrap' }}>{fullText}</span>}>
          <span style={VALUE_CELL_STYLE}>{singleLine}</span>
        </Tooltip>
      );
    },
    [emptyValueLabel],
  );

  const renderTopKeysCell = useCallback(
    (topKeys: Array<{ key: string; count: number }>) => {
      const fullText = topKeys.map((item) => `${item.key}(${item.count})`).join(', ');
      return (
        <Tooltip title={fullText || t('common.none')}>
          <span style={VALUE_CELL_STYLE}>{fullText || t('common.none')}</span>
        </Tooltip>
      );
    },
    [t],
  );

  const loadInitialData = useCallback(async () => {
    setLoading(true);
    try {
      const [statsResult, diagnosticsResult] = await Promise.all([
        apiService.getStats(),
        apiService.getDiagnostics(),
      ]);
      setKeyStats(statsResult.keys || []);
      setDiagnostics(diagnosticsResult);
      setLastLoadTime(Date.now());
    } catch (error) {
      message.error(toUserMessage(error, t('charts.loadError')));
    } finally {
      setLoading(false);
    }
  }, [t]);

  const loadKeyStats = useCallback(async () => {
    setLoading(true);
    try {
      const result = await apiService.getStats();
      setKeyStats(result.keys || []);
      setLastLoadTime(Date.now());
    } catch (error) {
      message.error(toUserMessage(error, t('charts.loadError')));
    } finally {
      setLoading(false);
    }
  }, [t]);

  const loadDiagnostics = useCallback(async () => {
    setLoading(true);
    try {
      const result = await apiService.getDiagnostics();
      setDiagnostics(result);
      setLastLoadTime(Date.now());
    } catch (error) {
      message.error(toUserMessage(error, t('charts.loadError')));
    } finally {
      setLoading(false);
    }
  }, [t]);

  const loadGlobalValueStats = useCallback(async () => {
    setLoading(true);
    try {
      const result = await apiService.getGlobalValueStats();
      setGlobalValueStats(result.values || []);
      setLastLoadTime(Date.now());
    } catch (error) {
      message.error(toUserMessage(error, t('charts.loadError')));
    } finally {
      setLoading(false);
    }
  }, [t]);

  const loadKeyValueDistribution = useCallback(
    async (key: string, resetSearch = false) => {
      setLoading(true);
      try {
        const result = await apiService.getValueDistribution(key);
        setSelectedKey(key);
        setSelectedValue(null);
        setKeyValueStats(result.values || []);
        if (resetSearch) {
          setKeyValueSearchText('');
        }
        setLastLoadTime(Date.now());
      } catch (error) {
        message.error(toUserMessage(error, t('charts.valueError')));
      } finally {
        setLoading(false);
      }
    },
    [t],
  );

  const loadValueKeyDistribution = useCallback(
    async (value: string, resetSearch = false) => {
      setLoading(true);
      try {
        const result = await apiService.getValueKeyDistribution(value);
        setSelectedValue(value);
        setSelectedKey(null);
        setValueKeyStats(result.keys || []);
        if (resetSearch) {
          setValueKeySearchText('');
        }
        setLastLoadTime(Date.now());
      } catch (error) {
        message.error(toUserMessage(error, t('charts.keyDistributionError')));
      } finally {
        setLoading(false);
      }
    },
    [t],
  );

  useEffect(() => {
    void loadInitialData();
  }, [loadInitialData]);

  useEffect(() => {
    if (viewMode === 'values' && globalValueStats.length === 0) {
      void loadGlobalValueStats();
    }
  }, [globalValueStats.length, loadGlobalValueStats, viewMode]);

  const handleRefresh = useCallback(async () => {
    if (viewMode === 'keys') {
      if (selectedKey !== null) {
        await loadKeyValueDistribution(selectedKey);
        return;
      }
      await loadKeyStats();
      return;
    }

    if (viewMode === 'values') {
      if (selectedValue !== null) {
        await loadValueKeyDistribution(selectedValue);
        return;
      }
      await loadGlobalValueStats();
      return;
    }

    await loadDiagnostics();
  }, [
    loadDiagnostics,
    loadGlobalValueStats,
    loadKeyStats,
    loadKeyValueDistribution,
    loadValueKeyDistribution,
    selectedKey,
    selectedValue,
    viewMode,
  ]);

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && Date.now() - lastLoadTime > 30000) {
        void handleRefresh();
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [handleRefresh, lastLoadTime]);

  const handleModeChange = (value: string) => {
    const nextMode = value as ViewMode;
    setViewMode(nextMode);
    setSelectedKey(null);
    setSelectedValue(null);
    setKeyValueStats([]);
    setValueKeyStats([]);
    setKeyValueSearchText('');
    setValueKeySearchText('');
  };

  const totalKeyCount = useMemo(
    () => keyStats.reduce((sum, item) => sum + item.count, 0),
    [keyStats],
  );
  const totalKeyValueCount = useMemo(
    () => keyValueStats.reduce((sum, item) => sum + item.count, 0),
    [keyValueStats],
  );
  const totalGlobalValueCount = useMemo(
    () => globalValueStats.reduce((sum, item) => sum + item.count, 0),
    [globalValueStats],
  );
  const totalValueKeyCount = useMemo(
    () => valueKeyStats.reduce((sum, item) => sum + item.count, 0),
    [valueKeyStats],
  );

  const filteredKeyStats = useMemo(
    () => keyStats.filter((item) => item.key.toLowerCase().includes(keySearchText.toLowerCase())),
    [keySearchText, keyStats],
  );
  const filteredKeyValueStats = useMemo(
    () =>
      keyValueStats.filter((item) =>
        formatStatValue(item.value, emptyValueLabel).toLowerCase().includes(keyValueSearchText.toLowerCase()),
      ),
    [emptyValueLabel, keyValueSearchText, keyValueStats],
  );
  const filteredGlobalValueStats = useMemo(
    () =>
      globalValueStats.filter((item) =>
        formatStatValue(item.value, emptyValueLabel)
          .toLowerCase()
          .includes(globalValueSearchText.toLowerCase()),
      ),
    [emptyValueLabel, globalValueSearchText, globalValueStats],
  );
  const filteredValueKeyStats = useMemo(
    () =>
      valueKeyStats.filter((item) =>
        item.key.toLowerCase().includes(valueKeySearchText.toLowerCase()),
      ),
    [valueKeySearchText, valueKeyStats],
  );

  const keyColumns: ColumnsType<KeyStatsItem> = [
    {
      title: t('charts.key'),
      dataIndex: 'key',
      key: 'key',
      sorter: (left, right) => left.key.localeCompare(right.key),
    },
    {
      title: t('charts.count'),
      dataIndex: 'count',
      key: 'count',
      sorter: (left, right) => left.count - right.count,
    },
    {
      title: t('charts.percentage'),
      key: 'percentage',
      render: (_value, record) => {
        const percentage = totalKeyCount > 0 ? ((record.count / totalKeyCount) * 100).toFixed(2) : '0.00';
        return <span>{percentage}%</span>;
      },
      sorter: (left, right) => left.count - right.count,
    },
    {
      title: t('charts.uniqueValues'),
      dataIndex: 'uniqueValues',
      key: 'uniqueValues',
      sorter: (left, right) => left.uniqueValues - right.uniqueValues,
    },
    {
      title: t('charts.action'),
      key: 'action',
      render: (_value, record) => (
        <Button type="link" onClick={() => void loadKeyValueDistribution(record.key, true)}>
          {t('charts.viewDistribution')}
        </Button>
      ),
    },
  ];

  const keyValueColumns: ColumnsType<ValueDistributionItem> = [
    {
      title: t('charts.value'),
      dataIndex: 'value',
      key: 'value',
      render: (value: string) => renderValueCell(value),
    },
    {
      title: t('charts.count'),
      dataIndex: 'count',
      key: 'count',
      sorter: (left, right) => left.count - right.count,
    },
    {
      title: t('charts.percentage'),
      key: 'percentage',
      render: (_value, record) => {
        const percentage = totalKeyValueCount > 0 ? ((record.count / totalKeyValueCount) * 100).toFixed(2) : '0.00';
        return <span>{percentage}%</span>;
      },
      sorter: (left, right) => left.count - right.count,
    },
  ];

  const globalValueColumns: ColumnsType<GlobalValueStat> = [
    {
      title: t('charts.value'),
      dataIndex: 'value',
      key: 'value',
      render: (value: string) => renderValueCell(value),
    },
    {
      title: t('charts.count'),
      dataIndex: 'count',
      key: 'count',
      sorter: (left, right) => left.count - right.count,
    },
    {
      title: t('charts.percentage'),
      key: 'percentage',
      render: (_value, record) => {
        const percentage =
          totalGlobalValueCount > 0 ? ((record.count / totalGlobalValueCount) * 100).toFixed(2) : '0.00';
        return <span>{percentage}%</span>;
      },
      sorter: (left, right) => left.count - right.count,
    },
    {
      title: t('charts.keyCountForValue'),
      dataIndex: 'keyCount',
      key: 'keyCount',
      sorter: (left, right) => left.keyCount - right.keyCount,
    },
    {
      title: t('charts.topKeys'),
      dataIndex: 'topKeys',
      key: 'topKeys',
      render: (value: Array<{ key: string; count: number }>) => renderTopKeysCell(value),
    },
    {
      title: t('charts.action'),
      key: 'action',
      render: (_value, record) => (
        <Button type="link" onClick={() => void loadValueKeyDistribution(record.value, true)}>
          {t('charts.viewKeyDistribution')}
        </Button>
      ),
    },
  ];

  const valueKeyColumns: ColumnsType<ValueKeyDistributionItem> = [
    {
      title: t('charts.key'),
      dataIndex: 'key',
      key: 'key',
      sorter: (left, right) => left.key.localeCompare(right.key),
    },
    {
      title: t('charts.count'),
      dataIndex: 'count',
      key: 'count',
      sorter: (left, right) => left.count - right.count,
    },
    {
      title: t('charts.percentage'),
      key: 'percentage',
      render: (_value, record) => {
        const percentage =
          totalValueKeyCount > 0 ? ((record.count / totalValueKeyCount) * 100).toFixed(2) : '0.00';
        return <span>{percentage}%</span>;
      },
      sorter: (left, right) => left.count - right.count,
    },
  ];

  const keyChartOption = useMemo(() => {
    const topTwenty = filteredKeyValueStats.slice(0, 20);
    return {
      title: { text: t('charts.chartTitle', { key: selectedKey || '' }), left: 'center' },
      tooltip: {
        trigger: 'axis',
        formatter: (params: Array<{ name: string; value: number }>) => {
          const data = params[0];
          const percentage =
            totalKeyValueCount > 0 ? ((data.value / totalKeyValueCount) * 100).toFixed(2) : '0.00';
          return `${data.name}<br/>${t('charts.count')}: ${data.value}<br/>${t('charts.percentage')}: ${percentage}%`;
        },
      },
      xAxis: {
        type: 'category',
        data: topTwenty.map((item) => truncateChartLabel(formatStatValue(item.value, emptyValueLabel))),
        axisLabel: { rotate: 45, interval: 0 },
      },
      yAxis: { type: 'value' },
      series: [{ type: 'bar', data: topTwenty.map((item) => item.count), itemStyle: { color: '#1890ff' } }],
      grid: { bottom: 100 },
    };
  }, [emptyValueLabel, filteredKeyValueStats, selectedKey, t, totalKeyValueCount]);

  const valueKeyChartOption = useMemo(() => {
    const topTwenty = filteredValueKeyStats.slice(0, 20);
    return {
      title: {
        text: t('charts.valueKeyChartTitle', {
          value: formatStatValue(selectedValue ?? '', emptyValueLabel),
        }),
        left: 'center',
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params: Array<{ name: string; value: number }>) => {
          const data = params[0];
          const percentage =
            totalValueKeyCount > 0 ? ((data.value / totalValueKeyCount) * 100).toFixed(2) : '0.00';
          return `${data.name}<br/>${t('charts.count')}: ${data.value}<br/>${t('charts.percentage')}: ${percentage}%`;
        },
      },
      xAxis: {
        type: 'category',
        data: topTwenty.map((item) => truncateChartLabel(item.key)),
        axisLabel: { rotate: 45, interval: 0 },
      },
      yAxis: { type: 'value' },
      series: [{ type: 'bar', data: topTwenty.map((item) => item.count), itemStyle: { color: '#52c41a' } }],
      grid: { bottom: 100 },
    };
  }, [emptyValueLabel, filteredValueKeyStats, selectedValue, t, totalValueKeyCount]);

  const diagnosticsTables: DiagnosticSection[] | null = diagnostics
    ? [
        {
          title: t('charts.emptyValues'),
          data: diagnostics.emptyValues as DiagnosticRow[],
          columns: [
            { title: t('charts.key'), dataIndex: 'key', key: 'key' },
            { title: t('charts.count'), dataIndex: 'count', key: 'count' },
          ],
          rowKey: 'key',
        },
        {
          title: t('charts.caseConflicts'),
          data: diagnostics.caseConflicts as DiagnosticRow[],
          columns: [
            { title: t('charts.normalizedKey'), dataIndex: 'normalizedKey', key: 'normalizedKey' },
            {
              title: t('charts.variants'),
              dataIndex: 'variants',
              key: 'variants',
              render: (value: unknown) => (Array.isArray(value) ? value.join(', ') : ''),
            },
            { title: t('charts.count'), dataIndex: 'count', key: 'count' },
          ],
          rowKey: 'normalizedKey',
        },
        {
          title: t('charts.synonyms'),
          data: diagnostics.suspectedSynonyms as DiagnosticRow[],
          columns: [
            { title: t('charts.normalizedKey'), dataIndex: 'normalizedKey', key: 'normalizedKey' },
            {
              title: t('charts.variants'),
              dataIndex: 'variants',
              key: 'variants',
              render: (value: unknown) => (Array.isArray(value) ? value.join(', ') : ''),
            },
            {
              title: t('charts.variantCount'),
              key: 'variantCount',
              render: (_value: unknown, record: DiagnosticRow) =>
                Array.isArray(record.variants) ? record.variants.length : 0,
            },
          ],
          rowKey: 'normalizedKey',
        },
        {
          title: t('charts.lowSignal'),
          data: diagnostics.lowSignalKeys as DiagnosticRow[],
          columns: [
            { title: t('charts.key'), dataIndex: 'key', key: 'key' },
            { title: t('charts.count'), dataIndex: 'count', key: 'count' },
            { title: t('charts.uniqueValues'), dataIndex: 'uniqueValues', key: 'uniqueValues' },
          ],
          rowKey: 'key',
        },
        {
          title: t('charts.singleton'),
          data: diagnostics.singletonKeys as DiagnosticRow[],
          columns: [
            { title: t('charts.key'), dataIndex: 'key', key: 'key' },
            { title: t('charts.count'), dataIndex: 'count', key: 'count' },
          ],
          rowKey: 'key',
        },
      ]
    : null;

  return (
    <Layout className="h-full bg-white">
      <Content style={{ padding: '24px', height: '100%', overflow: 'auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <Title level={4} style={{ margin: 0 }}>
            <BarChartOutlined /> {t('charts.title')}
          </Title>
          <Space>
            <Segmented<ViewMode>
              value={viewMode}
              options={[
                { label: t('charts.statsTab'), value: 'keys' },
                { label: t('charts.valueStatsTab'), value: 'values' },
                { label: t('charts.diagnosticsTab'), value: 'diagnostics' },
              ]}
              onChange={(value) => handleModeChange(value)}
            />
            <Button icon={<ReloadOutlined />} onClick={() => void handleRefresh()} loading={loading}>
              {t('common.refresh')}
            </Button>
          </Space>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: 50 }}>
            <Spin size="large" />
          </div>
        ) : viewMode === 'keys' && selectedKey !== null ? (
          <Card>
            <Space style={{ marginBottom: 16 }}>
              <Button icon={<ArrowLeftOutlined />} onClick={() => setSelectedKey(null)}>
                {t('charts.backToList')}
              </Button>
              <Text strong>
                {t('charts.currentKey')}: {selectedKey}
              </Text>
              <Text type="secondary">
                {t('charts.totalValues', { count: keyValueStats.length, total: totalKeyValueCount })}
              </Text>
            </Space>

            <div style={{ marginBottom: 16 }}>
              <Input
                placeholder={t('charts.searchValues')}
                prefix={<SearchOutlined />}
                value={keyValueSearchText}
                onChange={(event) => setKeyValueSearchText(event.target.value)}
                allowClear
                style={{ width: 320 }}
              />
              <Text type="secondary" style={{ marginLeft: 16 }}>
                {t('charts.showing', {
                  current: filteredKeyValueStats.length,
                  total: keyValueStats.length,
                })}
              </Text>
            </div>

            {filteredKeyValueStats.length > 0 ? (
              <Suspense
                fallback={
                  <div style={{ textAlign: 'center', padding: 40 }}>
                    <Spin />
                  </div>
                }
              >
                <ReactECharts option={keyChartOption} style={{ height: 400 }} />
              </Suspense>
            ) : (
              <Empty description={t('charts.emptyMatch')} />
            )}

            <Table
              dataSource={filteredKeyValueStats}
              columns={keyValueColumns}
              rowKey="value"
              size="small"
              pagination={{
                pageSize: 50,
                showSizeChanger: true,
                pageSizeOptions: ['20', '50', '100', '500'],
                showTotal: (total, range) => `${range[0]}-${range[1]} / ${total}`,
              }}
              style={{ marginTop: 16 }}
            />
          </Card>
        ) : viewMode === 'values' && selectedValue !== null ? (
          <Card>
            <Space style={{ marginBottom: 16 }}>
              <Button icon={<ArrowLeftOutlined />} onClick={() => setSelectedValue(null)}>
                {t('charts.backToList')}
              </Button>
              <Text strong>
                {t('charts.currentValue')}: {renderValueCell(selectedValue)}
              </Text>
              <Text type="secondary">
                {t('charts.totalKeys', { count: valueKeyStats.length, total: totalValueKeyCount })}
              </Text>
            </Space>

            <div style={{ marginBottom: 16 }}>
              <Input
                placeholder={t('charts.searchKeys')}
                prefix={<SearchOutlined />}
                value={valueKeySearchText}
                onChange={(event) => setValueKeySearchText(event.target.value)}
                allowClear
                style={{ width: 320 }}
              />
              <Text type="secondary" style={{ marginLeft: 16 }}>
                {t('charts.showing', {
                  current: filteredValueKeyStats.length,
                  total: valueKeyStats.length,
                })}
              </Text>
            </div>

            {filteredValueKeyStats.length > 0 ? (
              <Suspense
                fallback={
                  <div style={{ textAlign: 'center', padding: 40 }}>
                    <Spin />
                  </div>
                }
              >
                <ReactECharts option={valueKeyChartOption} style={{ height: 400 }} />
              </Suspense>
            ) : (
              <Empty description={t('charts.emptyMatch')} />
            )}

            <Table
              dataSource={filteredValueKeyStats}
              columns={valueKeyColumns}
              rowKey="key"
              size="small"
              pagination={{
                pageSize: 50,
                showSizeChanger: true,
                pageSizeOptions: ['20', '50', '100', '500'],
                showTotal: (total, range) => `${range[0]}-${range[1]} / ${total}`,
              }}
              style={{ marginTop: 16 }}
            />
          </Card>
        ) : viewMode === 'diagnostics' ? (
          diagnosticsTables && diagnosticsTables.length > 0 ? (
            <Space direction="vertical" style={{ width: '100%' }}>
              {diagnosticsTables.map((section) => (
                <Card key={section.title} title={section.title}>
                  <Table
                    dataSource={section.data}
                    columns={section.columns}
                    rowKey={section.rowKey}
                    pagination={{ defaultPageSize: 10, showSizeChanger: true }}
                    locale={{ emptyText: t('query.noResults') }}
                    size="small"
                  />
                </Card>
              ))}
            </Space>
          ) : (
            <Empty description={t('charts.noData')} />
          )
        ) : viewMode === 'values' ? (
          globalValueStats.length > 0 ? (
            <Card title={t('charts.valueCount', { values: globalValueStats.length, count: totalGlobalValueCount })}>
              <div style={{ marginBottom: 16 }}>
                <Input
                  placeholder={t('charts.searchValues')}
                  prefix={<SearchOutlined />}
                  value={globalValueSearchText}
                  onChange={(event) => setGlobalValueSearchText(event.target.value)}
                  allowClear
                  style={{ width: 320 }}
                />
                <Text type="secondary" style={{ marginLeft: 16 }}>
                  {t('charts.showing', {
                    current: filteredGlobalValueStats.length,
                    total: globalValueStats.length,
                  })}
                </Text>
              </div>
              <Table
                dataSource={filteredGlobalValueStats}
                columns={globalValueColumns}
                rowKey="value"
                pagination={{
                  defaultPageSize: 20,
                  showSizeChanger: true,
                  pageSizeOptions: ['20', '50', '100'],
                }}
                locale={{ emptyText: t('query.noResults') }}
              />
            </Card>
          ) : (
            <Empty description={t('charts.noData')} />
          )
        ) : keyStats.length > 0 ? (
          <Card title={t('charts.keyCount', { keys: keyStats.length, count: totalKeyCount })}>
            <div style={{ marginBottom: 16 }}>
              <Input
                placeholder={t('charts.searchKeys')}
                prefix={<SearchOutlined />}
                value={keySearchText}
                onChange={(event) => setKeySearchText(event.target.value)}
                allowClear
                style={{ width: 320 }}
              />
              <Text type="secondary" style={{ marginLeft: 16 }}>
                {t('charts.showing', {
                  current: filteredKeyStats.length,
                  total: keyStats.length,
                })}
              </Text>
            </div>
            <Table
              dataSource={filteredKeyStats}
              columns={keyColumns}
              rowKey="key"
              pagination={{
                defaultPageSize: 20,
                showSizeChanger: true,
                pageSizeOptions: ['20', '50', '100'],
              }}
            />
          </Card>
        ) : (
          <Empty description={t('charts.noData')} />
        )}
      </Content>
    </Layout>
  );
};


export default ChartsPage;
