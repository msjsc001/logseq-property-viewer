import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  Divider,
  Input,
  Layout,
  message,
  Modal,
  Radio,
  Space,
  Switch,
  Typography,
} from 'antd';
import {
  ClearOutlined,
  DeleteOutlined,
  ExclamationCircleOutlined,
  FolderOpenOutlined,
  GlobalOutlined,
  ReloadOutlined,
  SyncOutlined,
} from '@ant-design/icons';

import { apiService, type ResetOptions } from '../api';
import { useI18n } from '../i18n';
import { toUserMessage } from '../utils/errors';


const { Content } = Layout;
const { Paragraph, Text, Title } = Typography;

const DEFAULT_RESET_OPTIONS: Required<ResetOptions> = {
  clear_cache: true,
  clear_logs: true,
  clear_graph_path: true,
  clear_preferences: true,
  clear_history: true,
};


const SettingsPage: React.FC = () => {
  const { locale, setLocale, t } = useI18n();
  const [graphPath, setGraphPath] = useState('');
  const [loading, setLoading] = useState(false);
  const [buildingCache, setBuildingCache] = useState(false);
  const [autoUpdateEnabled, setAutoUpdateEnabled] = useState(false);
  const [pendingUpdates, setPendingUpdates] = useState(0);
  const [dataDir, setDataDir] = useState('');
  const [logDir, setLogDir] = useState('');
  const [resetModalOpen, setResetModalOpen] = useState(false);
  const [resetCountdown, setResetCountdown] = useState(3);
  const [canConfirmReset, setCanConfirmReset] = useState(false);
  const [resetOptions, setResetOptions] = useState<Required<ResetOptions>>(DEFAULT_RESET_OPTIONS);

  const countdownRef = useRef<number | null>(null);
  const autoCheckRef = useRef<number | null>(null);

  useEffect(() => {
    const loadSettings = async () => {
      try {
        const [config, preferences] = await Promise.all([
          apiService.getConfig(),
          apiService.getPreferences(),
        ]);
        setGraphPath(config.graph_path || '');
        setAutoUpdateEnabled(preferences.auto_update_enabled || false);
        setDataDir(preferences.data_dir || '');
        setLogDir(preferences.log_dir || '');
      } catch {
        // Initial settings loading failure should not break the page shell.
      }
    };
    void loadSettings();

    return () => {
      if (autoCheckRef.current) {
        clearInterval(autoCheckRef.current);
      }
      if (countdownRef.current) {
        clearInterval(countdownRef.current);
      }
    };
  }, []);

  const checkForUpdates = useCallback(async () => {
    try {
      const result = await apiService.checkUpdates();
      setPendingUpdates(result.changed_count || 0);
    } catch {
      // Watcher polling is best-effort.
    }
  }, []);

  useEffect(() => {
    if (autoCheckRef.current) {
      clearInterval(autoCheckRef.current);
      autoCheckRef.current = null;
    }
    if (!autoUpdateEnabled) {
      return;
    }
    void checkForUpdates();
    autoCheckRef.current = window.setInterval(() => {
      void checkForUpdates();
    }, 5000);
    return () => {
      if (autoCheckRef.current) {
        clearInterval(autoCheckRef.current);
      }
    };
  }, [autoUpdateEnabled, checkForUpdates]);

  const handleLanguageChange = async (nextLocale: 'zh' | 'en') => {
    try {
      await setLocale(nextLocale);
    } catch (error) {
      message.error(toUserMessage(error, t('settings.operationFail')));
    }
  };

  const handleSavePath = async () => {
    setLoading(true);
    try {
      await apiService.updateConfig(graphPath.trim());
      message.success(t('settings.savePathSuccess'));
    } catch (error) {
      message.error(toUserMessage(error, t('settings.savePathError')));
    } finally {
      setLoading(false);
    }
  };

  const handleBuildCache = async () => {
    if (!graphPath.trim()) {
      message.error(t('settings.savePathError'));
      return;
    }

    setBuildingCache(true);
    message.loading({ content: t('common.loading'), key: 'build', duration: 0 });
    try {
      const result = await apiService.buildCache(graphPath.trim());
      message.success({
        content: t('settings.rebuildSuccess', { count: result.file_count || 0 }),
        key: 'build',
      });
      setPendingUpdates(0);
    } catch (error) {
      message.error({ content: toUserMessage(error, t('settings.rebuildError')), key: 'build' });
    } finally {
      setBuildingCache(false);
    }
  };

  const handleClearCache = async () => {
    try {
      await apiService.clearCache();
      message.success(t('settings.clearCacheSuccess'));
    } catch (error) {
      message.error(toUserMessage(error, t('settings.operationFail')));
    }
  };

  const handleClearSortMemory = async () => {
    try {
      await apiService.clearSortMemory();
      message.success(t('settings.clearSortSuccess'));
    } catch (error) {
      message.error(toUserMessage(error, t('settings.operationFail')));
    }
  };

  const handleOpenDir = async (kind: 'data' | 'log') => {
    try {
      if (kind === 'data') {
        await apiService.openDataDir();
      } else {
        await apiService.openLogDir();
      }
      message.success(t('settings.openDirSuccess'));
    } catch (error) {
      message.error(toUserMessage(error, t('settings.openDirFail')));
    }
  };

  const handleAutoUpdateToggle = async (checked: boolean) => {
    setAutoUpdateEnabled(checked);
    try {
      const result = await apiService.setAutoUpdate(checked);
      if (checked && result.watching) {
        message.success(t('settings.autoUpdateOn'));
      } else if (checked) {
        message.warning(t('settings.autoUpdateFail'));
      } else {
        message.success(t('settings.autoUpdateOff'));
      }
    } catch (error) {
      setAutoUpdateEnabled((previous) => !previous);
      message.error(toUserMessage(error, t('settings.operationFail')));
    }
  };

  const handleApplyUpdates = async () => {
    setBuildingCache(true);
    message.loading({ content: t('settings.applyUpdatesLoading'), key: 'applyUpdates', duration: 0 });
    try {
      const result = await apiService.applyUpdates();
      if (result.updated_count > 0) {
        message.success({
          content: t('settings.applyUpdatesDone', { count: result.updated_count }),
          key: 'applyUpdates',
        });
      } else {
        message.info({ content: t('settings.applyUpdatesNone'), key: 'applyUpdates' });
      }
      setPendingUpdates(0);
    } catch (error) {
      message.error({
        content: toUserMessage(error, t('settings.applyUpdatesFail')),
        key: 'applyUpdates',
      });
    } finally {
      setBuildingCache(false);
    }
  };

  const openResetModal = () => {
    setResetOptions(DEFAULT_RESET_OPTIONS);
    setResetModalOpen(true);
    setResetCountdown(3);
    setCanConfirmReset(false);
    countdownRef.current = window.setInterval(() => {
      setResetCountdown((previous) => {
        if (previous <= 1) {
          if (countdownRef.current) {
            clearInterval(countdownRef.current);
          }
          setCanConfirmReset(true);
          return 0;
        }
        return previous - 1;
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

  const toggleResetOption = (key: keyof ResetOptions, checked: boolean) => {
    setResetOptions((previous) => ({ ...previous, [key]: checked }));
  };

  const handleResetAll = async () => {
    closeResetModal();
    message.loading({ content: t('settings.resetLoading'), key: 'reset', duration: 0 });
    try {
      await apiService.resetAll(resetOptions);
      message.success({ content: t('settings.resetSuccess'), key: 'reset', duration: 2 });
      window.setTimeout(() => window.location.reload(), 1500);
    } catch (error) {
      message.error({ content: toUserMessage(error, t('settings.resetFail')), key: 'reset' });
    }
  };

  return (
    <Layout className="h-full bg-white">
      <Content style={{ padding: '24px', overflowY: 'auto' }}>
        <Title level={4}>{t('settings.title')}</Title>

        <Card title={<><GlobalOutlined /> {t('settings.language')}</>} style={{ marginBottom: 16 }}>
          <Radio.Group value={locale} onChange={(event) => void handleLanguageChange(event.target.value)}>
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
              onChange={(event) => setGraphPath(event.target.value)}
              prefix={<FolderOpenOutlined />}
              style={{ flex: 1 }}
            />
            <Button type="primary" onClick={() => void handleSavePath()} loading={loading}>
              {t('common.save')}
            </Button>
          </Space.Compact>
        </Card>

        <Card title={`🗄️ ${t('settings.cacheTitle')}`} style={{ marginBottom: 16 }}>
          <Alert message={t('settings.cacheHint')} type="info" showIcon style={{ marginBottom: 16 }} />

          <div
            style={{
              marginBottom: 16,
              padding: '12px 16px',
              background: '#f8fafc',
              borderRadius: 8,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div>
              <Text strong>{t('settings.autoUpdateTitle')}</Text>
              <br />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {t('settings.autoUpdateDesc')}
              </Text>
            </div>
            <Space>
              {pendingUpdates > 0 && (
                <Badge count={pendingUpdates} style={{ backgroundColor: '#52c41a' }}>
                  <Button
                    type="primary"
                    icon={<ReloadOutlined />}
                    size="small"
                    onClick={() => void handleApplyUpdates()}
                    loading={buildingCache}
                  >
                    {t('settings.applyUpdates')}
                  </Button>
                </Badge>
              )}
              <Switch
                checked={autoUpdateEnabled}
                onChange={(checked) => void handleAutoUpdateToggle(checked)}
                checkedChildren={t('common.on')}
                unCheckedChildren={t('common.off')}
              />
            </Space>
          </div>

          <Space wrap>
            <Button
              type="primary"
              icon={<SyncOutlined spin={buildingCache} />}
              onClick={() => void handleBuildCache()}
              loading={buildingCache}
            >
              {t('settings.rebuildCache')}
            </Button>
            <Button icon={<DeleteOutlined />} danger onClick={() => void handleClearCache()}>
              {t('settings.clearCache')}
            </Button>
          </Space>
        </Card>

        <Card title={`🧹 ${t('settings.cleanupTitle')}`} style={{ marginBottom: 16 }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Space wrap>
              <Button icon={<ClearOutlined />} onClick={() => void handleClearSortMemory()}>
                {t('settings.clearSortMemory')}
              </Button>
              <Button icon={<FolderOpenOutlined />} onClick={() => void handleOpenDir('data')}>
                {t('settings.openDataDir')}
              </Button>
              <Button icon={<FolderOpenOutlined />} onClick={() => void handleOpenDir('log')}>
                {t('settings.openLogDir')}
              </Button>
            </Space>
            <Divider style={{ margin: '8px 0' }} />
            <div>
              <Text strong>{t('settings.dataDir')}:</Text>
              <br />
              <Text type="secondary">{dataDir || t('common.none')}</Text>
            </div>
            <div>
              <Text strong>{t('settings.logDir')}:</Text>
              <br />
              <Text type="secondary">{logDir || t('common.none')}</Text>
            </div>
          </Space>
        </Card>

        <Card
          title={<><ExclamationCircleOutlined style={{ color: '#ff4d4f' }} /> {t('settings.resetTitle')}</>}
          style={{ marginBottom: 16, borderColor: '#ffccc7' }}
          headStyle={{ borderBottom: '1px solid #ffccc7' }}
        >
          <Alert
            message={t('settings.resetWarning')}
            description={t('settings.resetDesc')}
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />
          <Button danger type="primary" icon={<DeleteOutlined />} onClick={openResetModal}>
            {t('settings.resetAll')}
          </Button>
        </Card>

        <Card title={`ℹ️ ${t('settings.aboutTitle')}`}>
          <Text>{t('settings.aboutVersion')}</Text>
          <br />
          <Text type="secondary">{t('settings.techStack')}</Text>
          <Divider />
          <Space>
            <Button
              type="primary"
              icon={<SyncOutlined />}
              onClick={() => window.open('https://github.com/msjsc001/logseq-property-viewer', '_blank')}
            >
              {t('settings.checkUpdates')}
            </Button>
          </Space>
        </Card>

        <Modal
          title={<><ExclamationCircleOutlined style={{ color: '#ff4d4f', marginRight: 8 }} />{t('settings.resetConfirmTitle')}</>}
          open={resetModalOpen}
          onCancel={closeResetModal}
          footer={[
            <Button key="cancel" onClick={closeResetModal}>
              {t('common.cancel')}
            </Button>,
            <Button
              key="confirm"
              type="primary"
              danger
              disabled={!canConfirmReset}
              onClick={() => void handleResetAll()}
            >
              {canConfirmReset
                ? t('common.confirm')
                : t('settings.resetWait', { seconds: resetCountdown })}
            </Button>,
          ]}
          width={500}
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            <Checkbox
              checked={resetOptions.clear_cache}
              onChange={(event) => toggleResetOption('clear_cache', event.target.checked)}
            >
              {t('settings.resetCache')}
            </Checkbox>
            <Checkbox
              checked={resetOptions.clear_logs}
              onChange={(event) => toggleResetOption('clear_logs', event.target.checked)}
            >
              {t('settings.resetLogs')}
            </Checkbox>
            <Checkbox
              checked={resetOptions.clear_preferences}
              onChange={(event) => toggleResetOption('clear_preferences', event.target.checked)}
            >
              {t('settings.resetPreferences')}
            </Checkbox>
            <Checkbox
              checked={resetOptions.clear_history}
              onChange={(event) => toggleResetOption('clear_history', event.target.checked)}
            >
              {t('settings.resetHistory')}
            </Checkbox>
            <Checkbox
              checked={resetOptions.clear_graph_path}
              onChange={(event) => toggleResetOption('clear_graph_path', event.target.checked)}
            >
              {t('settings.resetGraphPath')}
            </Checkbox>
            <Divider style={{ margin: '8px 0' }} />
            {!canConfirmReset ? (
              <Text type="secondary">{t('settings.resetWait', { seconds: resetCountdown })}</Text>
            ) : (
              <Text type="success">{t('settings.resetReady')}</Text>
            )}
          </Space>
        </Modal>
      </Content>
    </Layout>
  );
};


export default SettingsPage;
