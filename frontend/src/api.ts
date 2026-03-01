import axios from 'axios';

// 配置 baseURL，开发环境指向后端端口
// 如果是从前端 dev server (5173) 访问后端 (8000)，需要 CORS 支持 (后端已配)
const API = axios.create({
    baseURL: 'http://127.0.0.1:8000/api',
    timeout: 10000,
});

export interface AppConfig {
    graph_path: string;
    language: string;
}

export interface SearchResultItem {
    id: number;
    page: string;
    content: string;
    [key: string]: any; // 动态属性
}

export interface SearchResponse {
    results: SearchResultItem[];
    count: number;
}

export const apiService = {
    // 检查服务健康
    checkHealth: async () => {
        const res = await API.get('/health');
        return res.data;
    },

    // 获取配置
    getConfig: async () => {
        const res = await API.get<AppConfig>('/config');
        return res.data;
    },

    // 更新配置
    updateConfig: async (graph_path: string) => {
        const res = await API.post('/config', { graph_path });
        return res.data;
    },

    // 执行搜索
    search: async (query: string, graph_path?: string) => {
        const res = await API.post<SearchResponse>('/search', { query, graph_path });
        return res.data;
    },

    // 重建缓存
    buildCache: async (graph_path: string) => {
        const res = await API.post('/cache/build', { graph_path });
        return res.data;
    },

    // 获取属性键统计
    getStats: async () => {
        const res = await API.get('/stats');
        return res.data;
    },

    // 获取某个属性键的值分布
    getValueDistribution: async (key: string) => {
        const res = await API.get(`/stats/values/${encodeURIComponent(key)}`);
        return res.data;
    },

    // 清除缓存
    clearCache: async () => {
        const res = await API.post('/cache/clear');
        return res.data;
    },

    // 清除排序记忆
    clearSortMemory: async () => {
        const res = await API.post('/config/clear-sort-memory');
        return res.data;
    },

    // 获取用户偏好
    getPreferences: async () => {
        const res = await API.get('/preferences');
        return res.data;
    },

    // 保存查询历史
    saveQueryHistory: async (history: string[]) => {
        const res = await API.post('/preferences/query-history', { history });
        return res.data;
    },

    // 保存全局隐藏列
    saveGlobalHiddenColumns: async (columns: string[]) => {
        const res = await API.post('/preferences/global-hidden-columns', { columns });
        return res.data;
    },

    // 保存列配置
    saveColumnConfig: async (queryKey: string, config: any) => {
        const res = await API.post('/preferences/column-config', { query_key: queryKey, config });
        return res.data;
    },

    // 恢复出厂设置 - 清除所有数据
    resetAll: async () => {
        const res = await API.post('/reset-all');
        return res.data;
    },

    // 设置自动更新
    setAutoUpdate: async (enabled: boolean) => {
        const res = await API.post('/config/auto-update', { enabled });
        return res.data;
    },

    // 检查数据源更新
    checkUpdates: async () => {
        const res = await API.get('/check-updates');
        return res.data;
    },

    // 应用增量更新
    applyUpdates: async () => {
        const res = await API.post('/apply-updates');
        return res.data;
    },

    // 打开用户数据目录
    openDataDir: async () => {
        const res = await API.post('/open-data-dir');
        return res.data;
    }
};
