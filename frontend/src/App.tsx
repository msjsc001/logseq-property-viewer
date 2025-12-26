import React, { useState, useEffect } from 'react';
import { Layout, Menu, Typography, ConfigProvider, theme } from 'antd';
import { DatabaseOutlined, SettingOutlined, BarChartOutlined } from '@ant-design/icons';
import QueryPage from './components/QueryPage';
import SettingsPage from './components/SettingsPage';
import ChartsPage from './components/ChartsPage';
import { useI18n } from './i18n';
import { apiService } from './api';

const { Sider } = Layout;
const { Text } = Typography;

const App: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [currentPage, setCurrentPage] = useState<string>('query');
  const { t } = useI18n();

  // 从后端加载侧边栏折叠状态
  useEffect(() => {
    const loadSidebarState = async () => {
      try {
        const prefs = await apiService.getPreferences();
        if (typeof prefs.sidebar_collapsed === 'boolean') {
          setCollapsed(prefs.sidebar_collapsed);
        }
      } catch (e) {
        console.error('Failed to load sidebar state:', e);
      }
    };
    loadSidebarState();
  }, []);

  // 保存侧边栏折叠状态
  const handleCollapse = (value: boolean) => {
    setCollapsed(value);
    // 异步保存到后端
    fetch('http://127.0.0.1:8000/api/preferences/sidebar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ collapsed: value })
    }).catch(e => console.error('Failed to save sidebar state:', e));
  };

  const handleMenuClick = (key: string) => {
    setCurrentPage(key);
  };

  // 现代配色主题
  const customTheme = {
    token: {
      colorPrimary: '#6366f1',      // 靛蓝紫 - 主色
      colorBgContainer: '#ffffff',   // 纯白背景
      colorBgLayout: '#f8fafc',      // 浅灰布局背景
      borderRadius: 8,               // 圆角
      colorText: '#1e293b',          // 深灰文字
      colorTextSecondary: '#64748b', // 次要文字
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    },
    algorithm: theme.defaultAlgorithm,
  };

  return (
    <ConfigProvider theme={customTheme}>
      <Layout style={{ minHeight: '100vh', height: '100vh', background: '#f8fafc' }}>
        {/* 左侧固定侧边栏 - 现代深色设计 */}
        <Sider
          collapsible
          collapsed={collapsed}
          onCollapse={handleCollapse}
          style={{
            position: 'fixed',
            left: 0,
            top: 0,
            bottom: 0,
            height: '100vh',
            zIndex: 100,
            background: 'linear-gradient(180deg, #1e293b 0%, #0f172a 100%)',
            boxShadow: '2px 0 8px rgba(0, 0, 0, 0.15)',
          }}
          theme="dark"
        >
          {/* Logo 区域 */}
          <div style={{
            height: 56,
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            padding: collapsed ? 0 : '0 20px',
            borderBottom: '1px solid rgba(255,255,255,0.08)',
            marginBottom: 8
          }}>
            {!collapsed && (
              <Text style={{
                color: '#fff',
                fontSize: 15,
                fontWeight: 600,
                letterSpacing: '0.5px',
                whiteSpace: 'nowrap'
              }}>
                Property Query
              </Text>
            )}
            {collapsed && (
              <Text style={{ color: '#fff', fontSize: 18, fontWeight: 700 }}>PQ</Text>
            )}
          </div>

          <Menu
            theme="dark"
            selectedKeys={[currentPage]}
            mode="inline"
            onClick={(e) => handleMenuClick(e.key)}
            style={{
              background: 'transparent',
              borderRight: 'none',
            }}
            items={[
              {
                key: 'query',
                icon: <DatabaseOutlined style={{ fontSize: 16 }} />,
                label: t('nav.query'),
              },
              {
                key: 'charts',
                icon: <BarChartOutlined style={{ fontSize: 16 }} />,
                label: t('nav.charts'),
              },
              {
                key: 'settings',
                icon: <SettingOutlined style={{ fontSize: 16 }} />,
                label: t('nav.settings'),
              },
            ]}
          />
        </Sider>

        {/* 右侧内容区域 */}
        <Layout style={{
          marginLeft: collapsed ? 80 : 200,
          transition: 'margin-left 0.2s ease',
          height: '100vh',
          overflow: 'hidden',
          background: '#f8fafc'
        }}>
          {/* 使用 display 隐藏/显示保持组件实例状态 */}
          <div style={{ display: currentPage === 'query' ? 'flex' : 'none', height: '100%', flexDirection: 'column' }}>
            <QueryPage />
          </div>
          <div style={{ display: currentPage === 'charts' ? 'flex' : 'none', height: '100%', flexDirection: 'column' }}>
            <ChartsPage />
          </div>
          <div style={{ display: currentPage === 'settings' ? 'flex' : 'none', height: '100%', flexDirection: 'column' }}>
            <SettingsPage />
          </div>
        </Layout>
      </Layout>
    </ConfigProvider>
  );
};

export default App;
