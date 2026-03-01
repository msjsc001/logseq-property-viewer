import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Layout, Card, Input, Button, Space, Typography, message, Alert, Divider, Radio, Modal, Switch, Badge } from 'antd';
import { FolderOpenOutlined, SyncOutlined, ClearOutlined, DeleteOutlined, GlobalOutlined, ExclamationCircleOutlined, ReloadOutlined } from '@ant-design/icons';
import { apiService } from '../api';
import { useI18n } from '../i18n';
import type { Locale } from '../i18n';

const { Content } = Layout;
const { Title, Text, Paragraph } = Typography;

const SettingsPage: React.FC = () => {
    const { t, locale, setLocale } = useI18n();
    const [graphPath, setGraphPath] = useState<string>('');
    const [loading, setLoading] = useState<boolean>(false);
    const [buildingCache, setBuildingCache] = useState<boolean>(false);
    const [autoUpdateEnabled, setAutoUpdateEnabled] = useState<boolean>(false);
    const [pendingUpdates, setPendingUpdates] = useState<number>(0);

    // 清除所有数据对话框状态
    const [resetModalOpen, setResetModalOpen] = useState<boolean>(false);
    const [resetCountdown, setResetCountdown] = useState<number>(3);
    const [canConfirmReset, setCanConfirmReset] = useState<boolean>(false);
    const countdownRef = useRef<number | null>(null);

    // 自动检查更新定时器
    const autoCheckRef = useRef<number | null>(null);

    useEffect(() => {
        const loadConfig = async () => {
            try {
                const config = await apiService.getConfig();
                setGraphPath(config.graph_path || '');

                const prefs = await apiService.getPreferences();
                setAutoUpdateEnabled(prefs.auto_update_enabled || false);
            } catch (err) {
                console.error('Failed to load config:', err);
            }
        };
        loadConfig();

        return () => {
            if (autoCheckRef.current) clearInterval(autoCheckRef.current);
        };
    }, []);

    // 自动检查更新逻辑 - 轮询后端监听器状态
    const checkForUpdates = useCallback(async () => {
        try {
            const result = await apiService.checkUpdates();
            setPendingUpdates(result.changed_count || 0);
        } catch (err) {
            console.error('Check updates failed:', err);
        }
    }, []);

    // 启用/禁用自动更新 - 使用文件系统监听
    useEffect(() => {
        if (autoCheckRef.current) {
            clearInterval(autoCheckRef.current);
            autoCheckRef.current = null;
        }

        if (autoUpdateEnabled) {
            // 首次检查
            checkForUpdates();
            // 每5秒轮询后端监听器状态（后端使用 watchdog 真正监听文件变动）
            autoCheckRef.current = setInterval(checkForUpdates, 5000) as unknown as number;
        }

        return () => {
            if (autoCheckRef.current) clearInterval(autoCheckRef.current);
        };
    }, [autoUpdateEnabled, checkForUpdates]);

    const handleAutoUpdateToggle = async (checked: boolean) => {
        setAutoUpdateEnabled(checked);
        try {
            const result = await apiService.setAutoUpdate(checked);
            if (checked && result.watching) {
                message.success('已开启文件监听，变动将自动检测');
            } else if (checked) {
                message.warning('文件监听启动失败，请检查数据源路径');
            } else {
                message.success('已关闭自动更新');
            }
        } catch (err) {
            message.error('设置失败');
        }
    };

    // 应用增量更新
    const handleApplyUpdates = async () => {
        setBuildingCache(true);
        message.loading({ content: '正在增量更新...', key: 'applyUpdates', duration: 0 });
        try {
            const result = await apiService.applyUpdates();
            if (result.updated_count > 0) {
                message.success({ content: `已更新 ${result.updated_count} 个文件`, key: 'applyUpdates' });
            } else {
                message.info({ content: '没有需要更新的内容', key: 'applyUpdates' });
            }
            setPendingUpdates(0);
        } catch (err) {
            message.error({ content: '更新失败', key: 'applyUpdates' });
        } finally {
            setBuildingCache(false);
        }
    };


    const handleSavePath = async () => {
        if (!graphPath.trim()) {
            message.warning(t('common.error'));
            return;
        }
        setLoading(true);
        try {
            await apiService.updateConfig(graphPath);
            message.success(t('common.success'));
        } catch (err) {
            message.error(t('common.error'));
        } finally {
            setLoading(false);
        }
    };

    const handleBuildCache = async () => {
        if (!graphPath.trim()) return;
        setBuildingCache(true);
        message.loading({ content: t('common.loading'), key: 'build', duration: 0 });
        try {
            const result = await apiService.buildCache(graphPath);
            message.success({ content: `${t('common.success')} (${result.file_count || '?'} files)`, key: 'build' });
            setPendingUpdates(0);
        } catch (err: any) {
            message.error({ content: t('common.error'), key: 'build' });
        } finally {
            setBuildingCache(false);
        }
    };

    const handleClearCache = async () => {
        try {
            await apiService.clearCache();
            message.success(t('common.success'));
        } catch (err) {
            message.error(t('common.error'));
        }
    };

    const handleClearSortMemory = async () => {
        try {
            await apiService.clearSortMemory();
            message.success(t('common.success'));
        } catch (err) {
            message.error(t('common.error'));
        }
    };

    const handleOpenDataDir = async () => {
        try {
            await apiService.openDataDir();
            message.success('已打开数据目录');
        } catch (err) {
            message.error('打开数据目录失败');
        }
    };

    // 打开清除所有数据对话框
    const openResetModal = () => {
        setResetModalOpen(true);
        setResetCountdown(3);
        setCanConfirmReset(false);

        // 开始倒计时
        countdownRef.current = setInterval(() => {
            setResetCountdown(prev => {
                if (prev <= 1) {
                    if (countdownRef.current) clearInterval(countdownRef.current);
                    setCanConfirmReset(true);
                    return 0;
                }
                return prev - 1;
            });
        }, 1000);
    };

    const closeResetModal = () => {
        setResetModalOpen(false);
        if (countdownRef.current) {
            clearInterval(countdownRef.current);
            countdownRef.current = null;
        }
    };

    // 执行恢复出厂设置
    const handleResetAll = async () => {
        closeResetModal();
        message.loading({ content: '正在清除所有数据...', key: 'reset', duration: 0 });
        try {
            await apiService.resetAll();
            message.success({ content: '所有数据已清除，即将刷新页面...', key: 'reset', duration: 2 });
            // 延迟刷新页面，确保消息显示
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } catch (err) {
            message.error({ content: '清除失败', key: 'reset' });
        }
    };

    return (
        <Layout className="h-full bg-white">
            <Content style={{ padding: '24px', overflowY: 'auto' }}>
                <Title level={4}>{t('settings.title')}</Title>

                {/* 语言设置 */}
                <Card title={<><GlobalOutlined /> {t('settings.language')}</>} style={{ marginBottom: 16 }}>
                    <Radio.Group value={locale} onChange={(e) => setLocale(e.target.value as Locale)}>
                        <Radio.Button value="zh">{t('settings.langChinese')}</Radio.Button>
                        <Radio.Button value="en">{t('settings.langEnglish')}</Radio.Button>
                    </Radio.Group>
                </Card>

                <Card title={`📂 ${t('settings.pathTitle')}`} style={{ marginBottom: 16 }}>
                    <Paragraph type="secondary">{t('settings.pathDesc')}</Paragraph>
                    <Space.Compact style={{ width: '100%' }}>
                        <Input
                            placeholder={t('settings.pathPlaceholder')}
                            value={graphPath}
                            onChange={e => setGraphPath(e.target.value)}
                            prefix={<FolderOpenOutlined />}
                            style={{ flex: 1 }}
                        />
                        <Button type="primary" onClick={handleSavePath} loading={loading}>
                            {t('common.save')}
                        </Button>
                    </Space.Compact>
                </Card>

                <Card title={`🗄️ ${t('settings.cacheTitle')}`} style={{ marginBottom: 16 }}>
                    <Alert message={t('settings.cacheHint')} type="info" showIcon style={{ marginBottom: 16 }} />

                    {/* 自动更新开关 */}
                    <div style={{ marginBottom: 16, padding: '12px 16px', background: '#f8fafc', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div>
                            <Text strong>自动随数据源更新</Text>
                            <br />
                            <Text type="secondary" style={{ fontSize: 12 }}>开启后实时监听文件变动，只更新有变化的文件（零轮询）</Text>
                        </div>
                        <Space>
                            {pendingUpdates > 0 && (
                                <Badge count={`${pendingUpdates}个文件变动`} style={{ backgroundColor: '#52c41a' }}>
                                    <Button
                                        type="primary"
                                        icon={<ReloadOutlined />}
                                        size="small"
                                        onClick={handleApplyUpdates}
                                        loading={buildingCache}
                                    >
                                        增量更新
                                    </Button>
                                </Badge>
                            )}
                            <Switch
                                checked={autoUpdateEnabled}
                                onChange={handleAutoUpdateToggle}
                                checkedChildren="开"
                                unCheckedChildren="关"
                            />
                        </Space>
                    </div>

                    <Space wrap>
                        <Button type="primary" icon={<SyncOutlined spin={buildingCache} />} onClick={handleBuildCache} loading={buildingCache}>
                            {t('settings.rebuildCache')}
                        </Button>
                        <Button icon={<DeleteOutlined />} danger onClick={handleClearCache}>
                            {t('settings.clearCache')}
                        </Button>
                    </Space>
                </Card>

                <Card title={`🧹 ${t('settings.cleanupTitle')}`} style={{ marginBottom: 16 }}>
                    <Space wrap>
                        <Button icon={<ClearOutlined />} onClick={handleClearSortMemory}>
                            {t('settings.clearSortMemory')}
                        </Button>
                        <Button icon={<FolderOpenOutlined />} onClick={handleOpenDataDir}>
                            打开数据存储目录
                        </Button>
                    </Space>
                </Card>

                {/* 危险操作区 */}
                <Card
                    title={<><ExclamationCircleOutlined style={{ color: '#ff4d4f' }} /> 危险操作</>}
                    style={{ marginBottom: 16, borderColor: '#ffccc7' }}
                    headStyle={{ borderBottom: '1px solid #ffccc7' }}
                >
                    <Alert
                        message="以下操作不可恢复"
                        description="清除所有数据将删除软件的所有配置、缓存、搜索记录等，相当于恢复出厂设置。此操作无法撤销。"
                        type="warning"
                        showIcon
                        style={{ marginBottom: 16 }}
                    />
                    <Button
                        danger
                        type="primary"
                        icon={<DeleteOutlined />}
                        onClick={openResetModal}
                    >
                        清除所有数据
                    </Button>
                </Card>

                <Card title={`ℹ️ ${t('settings.aboutTitle')}`}>
                    <Text>Property Query v2.1</Text>
                    <br />
                    <Text type="secondary">{t('settings.techStack')}</Text>
                    <Divider />
                    <Text type="secondary">FastAPI | React | Ant Design | ECharts</Text>
                    <Divider />
                    <Space>
                        <Button
                            type="primary"
                            icon={<SyncOutlined />}
                            onClick={() => window.open('https://github.com/msjsc001/logseq-property-viewer', '_blank')}
                        >
                            检查更新
                        </Button>
                        <Text type="secondary">访问 GitHub 获取最新版本</Text>
                    </Space>
                </Card>

                {/* 清除所有数据确认对话框 */}
                <Modal
                    title={<><ExclamationCircleOutlined style={{ color: '#ff4d4f', marginRight: 8 }} />确认清除所有数据</>}
                    open={resetModalOpen}
                    onCancel={closeResetModal}
                    footer={[
                        <Button key="cancel" onClick={closeResetModal}>取消</Button>,
                        <Button
                            key="confirm"
                            type="primary"
                            danger
                            disabled={!canConfirmReset}
                            onClick={handleResetAll}
                        >
                            {canConfirmReset ? '确认清除' : `请等待 ${resetCountdown} 秒`}
                        </Button>
                    ]}
                    width={450}
                >
                    <Alert
                        message="是否清除所有数据和配置，恢复软件初始状态？"
                        description={
                            <ul style={{ margin: '8px 0', paddingLeft: 20 }}>
                                <li>所有缓存数据将被删除</li>
                                <li>所有配置将被重置</li>
                                <li>所有搜索记录将被清除</li>
                                <li>所有列配置和偏好将被清除</li>
                            </ul>
                        }
                        type="error"
                        showIcon
                    />
                    <div style={{ marginTop: 16, textAlign: 'center' }}>
                        {!canConfirmReset && (
                            <Text type="secondary">
                                为防止误操作，请等待 <Text strong style={{ color: '#ff4d4f', fontSize: 18 }}>{resetCountdown}</Text> 秒后确认
                            </Text>
                        )}
                        {canConfirmReset && (
                            <Text type="success">现在可以确认清除</Text>
                        )}
                    </div>
                </Modal>
            </Content>
        </Layout>
    );
};

export default SettingsPage;
