import React, { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';

// 支持的语言
export type Locale = 'zh' | 'en';

// 翻译字典
const translations: Record<Locale, Record<string, string>> = {
    zh: {
        // 通用
        'app.title': 'Logseq 属性查询工具',
        'common.search': '搜索',
        'common.save': '保存',
        'common.cancel': '取消',
        'common.apply': '应用',
        'common.confirm': '确认',
        'common.loading': '加载中...',
        'common.success': '成功',
        'common.error': '错误',

        // 导航
        'nav.query': '高级查询',
        'nav.charts': '数据统计',
        'nav.settings': '设置',

        // 查询页面
        'query.title': '高级属性查询',
        'query.placeholder': '输入查询 (如: has:date)',
        'query.history': '历史记录',
        'query.columnManage': '列管理',
        'query.saveView': '保存视图',
        'query.resultCount': '找到 {count} 条结果',
        'query.noResults': '无结果',
        'query.tip': '点击 Page 可跳转 Logseq | 右键显示更多操作 | 缺失文件以红色标注',

        // 列管理
        'column.selectAll': '全选',
        'column.onlyPage': '仅 page',

        // 右键菜单
        'menu.copyCell': '复制单元格',
        'menu.copyRow': '复制整行 (JSON)',
        'menu.openLogseq': '在 Logseq 中打开',
        'menu.exportSelected': '导出选中行为 JSON',

        // 图表页面
        'charts.title': '数据统计',
        'charts.allKeys': '所有属性键',
        'charts.viewDistribution': '查看分布',
        'charts.backToList': '返回属性列表',
        'charts.currentKey': '当前属性',
        'charts.noData': '暂无统计数据，请先在设置中配置路径并重建缓存',

        // 设置页面
        'settings.title': '设置',
        'settings.pathTitle': 'Logseq 图谱路径',
        'settings.pathDesc': '请输入您的 Logseq 图谱根目录路径（包含 pages 和 journals 文件夹的目录）',
        'settings.pathPlaceholder': '例如: D:\\Logseq\\MyGraph',
        'settings.cacheTitle': '缓存管理',
        'settings.cacheHint': '首次使用或 Logseq 内容更新后，请点击「重建缓存」以获取最新数据',
        'settings.rebuildCache': '重建缓存',
        'settings.clearCache': '清除缓存',
        'settings.clearCacheConfirm': '确认清除缓存?',
        'settings.clearCacheDesc': '将删除本地缓存文件，下次使用需重新构建',
        'settings.cleanupTitle': '清理设置',
        'settings.clearSortMemory': '清除排序记忆',
        'settings.clearColumnConfig': '清除列配置',
        'settings.aboutTitle': '关于',
        'settings.version': 'Logseq 属性查询工具 v2.0',
        'settings.techStack': '基于 FastAPI + React + AG Grid 构建',

        // 语言
        'settings.language': '语言',
        'settings.langChinese': '中文',
        'settings.langEnglish': 'English',
    },
    en: {
        // Common
        'app.title': 'Logseq Property Query Tool',
        'common.search': 'Search',
        'common.save': 'Save',
        'common.cancel': 'Cancel',
        'common.apply': 'Apply',
        'common.confirm': 'Confirm',
        'common.loading': 'Loading...',
        'common.success': 'Success',
        'common.error': 'Error',

        // Navigation
        'nav.query': 'Advanced Query',
        'nav.charts': 'Statistics',
        'nav.settings': 'Settings',

        // Query Page
        'query.title': 'Advanced Property Query',
        'query.placeholder': 'Enter query (e.g., has:date)',
        'query.history': 'History',
        'query.columnManage': 'Columns',
        'query.saveView': 'Save View',
        'query.resultCount': 'Found {count} results',
        'query.noResults': 'No results',
        'query.tip': 'Click Page to open in Logseq | Right-click for more options | Missing files in red',

        // Column Management
        'column.selectAll': 'Select All',
        'column.onlyPage': 'Only page',

        // Context Menu
        'menu.copyCell': 'Copy Cell',
        'menu.copyRow': 'Copy Row (JSON)',
        'menu.openLogseq': 'Open in Logseq',
        'menu.exportSelected': 'Export Selected as JSON',

        // Charts Page
        'charts.title': 'Statistics',
        'charts.allKeys': 'All Property Keys',
        'charts.viewDistribution': 'View Distribution',
        'charts.backToList': 'Back to List',
        'charts.currentKey': 'Current Property',
        'charts.noData': 'No data. Please configure path and rebuild cache in Settings.',

        // Settings Page
        'settings.title': 'Settings',
        'settings.pathTitle': 'Logseq Graph Path',
        'settings.pathDesc': 'Enter your Logseq graph root directory (containing pages and journals folders)',
        'settings.pathPlaceholder': 'e.g., D:\\Logseq\\MyGraph',
        'settings.cacheTitle': 'Cache Management',
        'settings.cacheHint': 'Click "Rebuild Cache" for first use or after Logseq content updates',
        'settings.rebuildCache': 'Rebuild Cache',
        'settings.clearCache': 'Clear Cache',
        'settings.clearCacheConfirm': 'Clear cache?',
        'settings.clearCacheDesc': 'This will delete local cache files. Rebuild required next time.',
        'settings.cleanupTitle': 'Cleanup Settings',
        'settings.clearSortMemory': 'Clear Sort Memory',
        'settings.clearColumnConfig': 'Clear Column Config',
        'settings.aboutTitle': 'About',
        'settings.version': 'Logseq Property Query Tool v2.0',
        'settings.techStack': 'Built with FastAPI + React + AG Grid',

        // Language
        'settings.language': 'Language',
        'settings.langChinese': '中文',
        'settings.langEnglish': 'English',
    }
};

// Context
interface I18nContextType {
    locale: Locale;
    setLocale: (locale: Locale) => void;
    t: (key: string, params?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nContextType | undefined>(undefined);

// Provider
export const I18nProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [locale, setLocale] = useState<Locale>(() => {
        const saved = localStorage.getItem('app_locale');
        return (saved === 'en' || saved === 'zh') ? saved : 'zh';
    });

    useEffect(() => {
        localStorage.setItem('app_locale', locale);
    }, [locale]);

    const t = (key: string, params?: Record<string, string | number>): string => {
        let text = translations[locale][key] || key;
        if (params) {
            Object.entries(params).forEach(([k, v]) => {
                text = text.replace(`{${k}}`, String(v));
            });
        }
        return text;
    };

    return (
        <I18nContext.Provider value={{ locale, setLocale, t }}>
            {children}
        </I18nContext.Provider>
    );
};

// Hook
export const useI18n = (): I18nContextType => {
    const context = useContext(I18nContext);
    if (!context) {
        throw new Error('useI18n must be used within I18nProvider');
    }
    return context;
};
