import React, { Suspense, lazy, useEffect, useState } from 'react';
import { ConfigProvider, Layout, Menu, Spin, Typography, theme } from 'antd';
import { BarChartOutlined, DatabaseOutlined, SettingOutlined } from '@ant-design/icons';

import { apiService } from './api';
import { useI18n } from './i18n';


const { Sider } = Layout;
const { Text } = Typography;

const QueryPage = lazy(() => import('./components/QueryPage'));
const ChartsPage = lazy(() => import('./components/ChartsPage'));
const SettingsPage = lazy(() => import('./components/SettingsPage'));

type PageKey = 'query' | 'charts' | 'settings';

const PAGE_COMPONENTS: Record<PageKey, React.LazyExoticComponent<React.FC>> = {
  query: QueryPage,
  charts: ChartsPage,
  settings: SettingsPage,
};


const App: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [currentPage, setCurrentPage] = useState<PageKey>('query');
  const [loadedPages, setLoadedPages] = useState<PageKey[]>(['query']);
  const { t } = useI18n();

  useEffect(() => {
    apiService
      .getPreferences()
      .then((preferences) => {
        if (typeof preferences.sidebar_collapsed === 'boolean') {
          setCollapsed(preferences.sidebar_collapsed);
        }
      })
      .catch(() => {
        // Sidebar state restoration should not block the app shell.
      });
  }, []);

  const handleCollapse = (value: boolean) => {
    setCollapsed(value);
    apiService.saveSidebarState(value).catch(() => {
      // The UI should stay responsive even if persistence fails.
    });
  };

  const handleMenuClick = (key: string) => {
    const pageKey = key as PageKey;
    setCurrentPage(pageKey);
    setLoadedPages((prev) => (prev.includes(pageKey) ? prev : [...prev, pageKey]));
  };

  const customTheme = {
    token: {
      colorPrimary: '#6366f1',
      colorBgContainer: '#ffffff',
      colorBgLayout: '#f8fafc',
      borderRadius: 8,
      colorText: '#1e293b',
      colorTextSecondary: '#64748b',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    },
    algorithm: theme.defaultAlgorithm,
  };

  return (
    <ConfigProvider theme={customTheme}>
      <Layout style={{ minHeight: '100vh', height: '100vh', background: '#f8fafc' }}>
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
          <div
            style={{
              height: 56,
              display: 'flex',
              alignItems: 'center',
              justifyContent: collapsed ? 'center' : 'flex-start',
              padding: collapsed ? 0 : '0 20px',
              borderBottom: '1px solid rgba(255,255,255,0.08)',
              marginBottom: 8,
            }}
          >
            {!collapsed && (
              <Text
                style={{
                  color: '#fff',
                  fontSize: 15,
                  fontWeight: 600,
                  letterSpacing: '0.5px',
                  whiteSpace: 'nowrap',
                }}
              >
                Property Query
              </Text>
            )}
            {collapsed && <Text style={{ color: '#fff', fontSize: 18, fontWeight: 700 }}>PQ</Text>}
          </div>

          <Menu
            theme="dark"
            selectedKeys={[currentPage]}
            mode="inline"
            onClick={(event) => handleMenuClick(event.key)}
            style={{ background: 'transparent', borderRight: 'none' }}
            items={[
              { key: 'query', icon: <DatabaseOutlined style={{ fontSize: 16 }} />, label: t('nav.query') },
              { key: 'charts', icon: <BarChartOutlined style={{ fontSize: 16 }} />, label: t('nav.charts') },
              { key: 'settings', icon: <SettingOutlined style={{ fontSize: 16 }} />, label: t('nav.settings') },
            ]}
          />
        </Sider>

        <Layout
          style={{
            marginLeft: collapsed ? 80 : 200,
            transition: 'margin-left 0.2s ease',
            height: '100vh',
            overflow: 'hidden',
            background: '#f8fafc',
          }}
        >
          {loadedPages.map((page) => {
            const Component = PAGE_COMPONENTS[page];
            return (
              <div
                key={page}
                style={{
                  display: currentPage === page ? 'flex' : 'none',
                  height: '100%',
                  flexDirection: 'column',
                  width: '100%',
                }}
              >
                <Suspense
                  fallback={
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        height: '100%',
                      }}
                    >
                      <Spin tip={t('app.loadingPage')} />
                    </div>
                  }
                >
                  <Component />
                </Suspense>
              </div>
            );
          })}
        </Layout>
      </Layout>
    </ConfigProvider>
  );
};


export default App;
