import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Layout, Card, Table, Typography, message, Spin, Empty, Button, Space, Input } from 'antd';
import { BarChartOutlined, ArrowLeftOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { apiService } from '../api';

const { Content } = Layout;
const { Title, Text } = Typography;

interface KeyStats {
    key: string;
    count: number;
    uniqueValues: number;
}

interface ValueStats {
    value: string;
    count: number;
}

const ChartsPage: React.FC = () => {
    const [loading, setLoading] = useState<boolean>(false);
    const [keyStats, setKeyStats] = useState<KeyStats[]>([]);
    const [selectedKey, setSelectedKey] = useState<string | null>(null);
    const [valueStats, setValueStats] = useState<ValueStats[]>([]);
    const [searchText, setSearchText] = useState<string>('');
    const [valueSearchText, setValueSearchText] = useState<string>(''); // 值分布搜索
    const [lastLoadTime, setLastLoadTime] = useState<number>(0);

    // 加载属性键统计
    const loadKeyStats = useCallback(async () => {
        setLoading(true);
        try {
            const res = await apiService.getStats();
            setKeyStats(res.keys || []);
            setLastLoadTime(Date.now());
        } catch (err) {
            console.error(err);
            message.error('加载统计数据失败，请先在设置中配置路径并重建缓存');
        } finally {
            setLoading(false);
        }
    }, []);

    // 初始加载
    useEffect(() => {
        loadKeyStats();
    }, [loadKeyStats]);

    // 页面可见时检查是否需要刷新（超过30秒自动刷新）
    useEffect(() => {
        const handleVisibilityChange = () => {
            if (document.visibilityState === 'visible') {
                const elapsed = Date.now() - lastLoadTime;
                if (elapsed > 30000) { // 超过30秒自动刷新
                    loadKeyStats();
                }
            }
        };

        document.addEventListener('visibilitychange', handleVisibilityChange);
        return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
    }, [lastLoadTime, loadKeyStats]);

    // 点击某个属性键，查看值分布
    const handleKeyClick = async (key: string) => {
        setSelectedKey(key);
        setValueSearchText('');
        setLoading(true);
        try {
            const res = await apiService.getValueDistribution(key);
            setValueStats(res.values || []);
        } catch (err) {
            message.error('加载值分布失败');
        } finally {
            setLoading(false);
        }
    };

    // 返回属性键列表
    const handleBack = () => {
        setSelectedKey(null);
        setValueStats([]);
        setValueSearchText('');
    };

    // 计算总出现次数
    const totalKeyCount = useMemo(() =>
        keyStats.reduce((sum, item) => sum + item.count, 0),
        [keyStats]
    );

    // 计算值分布总次数
    const totalValueCount = useMemo(() =>
        valueStats.reduce((sum, item) => sum + item.count, 0),
        [valueStats]
    );

    // 过滤后的属性键列表
    const filteredKeyStats = useMemo(() =>
        keyStats.filter(item => item.key.toLowerCase().includes(searchText.toLowerCase())),
        [keyStats, searchText]
    );

    // 过滤后的值列表
    const filteredValueStats = useMemo(() =>
        valueStats.filter(item => item.value.toLowerCase().includes(valueSearchText.toLowerCase())),
        [valueStats, valueSearchText]
    );

    // 属性键表格列定义（带百分比）
    const keyColumns = [
        {
            title: '属性键',
            dataIndex: 'key',
            key: 'key',
            sorter: (a: KeyStats, b: KeyStats) => a.key.localeCompare(b.key)
        },
        {
            title: '出现次数',
            dataIndex: 'count',
            key: 'count',
            sorter: (a: KeyStats, b: KeyStats) => a.count - b.count
        },
        {
            title: '占比',
            key: 'percentage',
            render: (_: any, record: KeyStats) => {
                const pct = totalKeyCount > 0 ? (record.count / totalKeyCount * 100).toFixed(2) : '0.00';
                return <span>{pct}%</span>;
            },
            sorter: (a: KeyStats, b: KeyStats) => a.count - b.count
        },
        {
            title: '唯一值数',
            dataIndex: 'uniqueValues',
            key: 'uniqueValues',
            sorter: (a: KeyStats, b: KeyStats) => a.uniqueValues - b.uniqueValues
        },
        {
            title: '操作',
            key: 'action',
            render: (_: any, record: KeyStats) => (
                <Button type="link" onClick={() => handleKeyClick(record.key)}>
                    查看分布
                </Button>
            ),
        },
    ];

    // 值分布表格列定义（带百分比）
    const valueColumns = [
        { title: '值', dataIndex: 'value', key: 'value' },
        { title: '出现次数', dataIndex: 'count', key: 'count', sorter: (a: ValueStats, b: ValueStats) => a.count - b.count },
        {
            title: '占比',
            key: 'percentage',
            render: (_: any, record: ValueStats) => {
                const pct = totalValueCount > 0 ? (record.count / totalValueCount * 100).toFixed(2) : '0.00';
                return <span>{pct}%</span>;
            },
            sorter: (a: ValueStats, b: ValueStats) => a.count - b.count
        },
    ];

    // 值分布图表配置
    const getChartOption = () => {
        const top20 = filteredValueStats.slice(0, 20);
        return {
            title: { text: `${selectedKey} 值分布 (Top 20)`, left: 'center' },
            tooltip: {
                trigger: 'axis',
                formatter: (params: any) => {
                    const data = params[0];
                    const pct = totalValueCount > 0 ? (data.value / totalValueCount * 100).toFixed(2) : '0.00';
                    return `${data.name}<br/>次数: ${data.value}<br/>占比: ${pct}%`;
                }
            },
            xAxis: {
                type: 'category',
                data: top20.map(v => v.value.length > 15 ? v.value.substring(0, 15) + '...' : v.value),
                axisLabel: { rotate: 45, interval: 0 },
            },
            yAxis: { type: 'value' },
            series: [{
                type: 'bar',
                data: top20.map(v => v.count),
                itemStyle: { color: '#1890ff' },
            }],
            grid: { bottom: 100 },
        };
    };

    return (
        <Layout className="h-full bg-white">
            <Content style={{ padding: '24px', height: '100%', overflow: 'auto' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                    <Title level={4} style={{ margin: 0 }}>
                        <BarChartOutlined /> 数据统计
                    </Title>
                    <Button
                        icon={<ReloadOutlined />}
                        onClick={() => loadKeyStats()}
                        loading={loading}
                    >
                        刷新数据
                    </Button>
                </div>

                {loading ? (
                    <div style={{ textAlign: 'center', padding: 50 }}>
                        <Spin size="large" />
                    </div>
                ) : selectedKey ? (
                    <Card>
                        <Space style={{ marginBottom: 16 }}>
                            <Button icon={<ArrowLeftOutlined />} onClick={handleBack}>
                                返回属性列表
                            </Button>
                            <Text strong>当前属性: {selectedKey}</Text>
                            <Text type="secondary">共 {valueStats.length} 个不同值，总出现 {totalValueCount} 次</Text>
                        </Space>

                        {/* 值搜索框 */}
                        <div style={{ marginBottom: 16 }}>
                            <Input
                                placeholder="搜索值..."
                                prefix={<SearchOutlined />}
                                value={valueSearchText}
                                onChange={e => setValueSearchText(e.target.value)}
                                allowClear
                                style={{ width: 300 }}
                            />
                            <Text type="secondary" style={{ marginLeft: 16 }}>
                                显示 {filteredValueStats.length} / {valueStats.length} 个值
                            </Text>
                        </div>

                        {filteredValueStats.length > 0 ? (
                            <ReactECharts option={getChartOption()} style={{ height: 400 }} />
                        ) : (
                            <Empty description="暂无匹配数据" />
                        )}
                        <Table
                            dataSource={filteredValueStats}
                            columns={valueColumns}
                            rowKey="value"
                            size="small"
                            pagination={{
                                pageSize: 50,
                                showSizeChanger: true,
                                pageSizeOptions: ['20', '50', '100', '500'],
                                showTotal: (total, range) => `${range[0]}-${range[1]} / 共 ${total} 条`
                            }}
                            style={{ marginTop: 16 }}
                        />
                    </Card>
                ) : keyStats.length > 0 ? (
                    <Card title={`所有属性键 (共 ${keyStats.length} 个，总出现 ${totalKeyCount} 次)`}>
                        {/* 搜索框 */}
                        <div style={{ marginBottom: 16 }}>
                            <Input
                                placeholder="搜索属性键..."
                                prefix={<SearchOutlined />}
                                value={searchText}
                                onChange={e => setSearchText(e.target.value)}
                                allowClear
                                style={{ width: 300 }}
                            />
                            <Text type="secondary" style={{ marginLeft: 16 }}>
                                显示 {filteredKeyStats.length} / {keyStats.length} 个属性
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
                                showTotal: (total) => `共 ${total} 条`
                            }}
                        />
                    </Card>
                ) : (
                    <Empty description="暂无统计数据，请先在设置中配置路径并重建缓存" />
                )}
            </Content>
        </Layout>
    );
};

export default ChartsPage;
