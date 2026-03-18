import axios from 'axios';

export interface AppConfig {
  graph_path: string;
  language: string;
  auto_update_enabled: boolean;
}

export interface SearchResultItem {
  id: number;
  page: string;
  block_content: string;
  content: string;
  file_path: string;
  line_start?: number;
  line_end?: number;
  block_path: string;
  properties: Record<string, string>;
  [key: string]: unknown;
}

export interface SearchResponse {
  results: SearchResultItem[];
  count: number;
}

export interface KeyStatsItem {
  key: string;
  count: number;
  uniqueValues: number;
}

export interface KeyStatsResponse {
  keys: KeyStatsItem[];
  total: number;
}

export interface ValueDistributionItem {
  value: string;
  count: number;
}

export interface ValueDistributionResponse {
  values: ValueDistributionItem[];
  total: number;
}

export interface GlobalValueTopKey {
  key: string;
  count: number;
}

export interface GlobalValueStat {
  value: string;
  count: number;
  keyCount: number;
  topKeys: GlobalValueTopKey[];
}

export interface GlobalValueStatsResponse {
  values: GlobalValueStat[];
  total: number;
}

export interface ValueKeyDistributionItem {
  key: string;
  count: number;
}

export interface ValueKeyDistributionResponse {
  value: string;
  keys: ValueKeyDistributionItem[];
  total: number;
}

export interface PreferencesResponse {
  query_history: string[];
  global_hidden_columns: string[];
  column_configs: Record<string, unknown>;
  sidebar_collapsed: boolean;
  auto_update_enabled: boolean;
  query_case_sensitive: boolean;
  graph_name: string;
  language: 'zh' | 'en';
  data_dir: string;
  log_dir: string;
  cache_version: number;
}

export interface ResetOptions {
  clear_cache?: boolean;
  clear_logs?: boolean;
  clear_graph_path?: boolean;
  clear_preferences?: boolean;
  clear_history?: boolean;
}

export interface DiagnosticsResponse {
  emptyValues: Array<{ key: string; count: number }>;
  caseConflicts: Array<{ normalizedKey: string; variants: string[]; count: number }>;
  suspectedSynonyms: Array<{ normalizedKey: string; variants: string[] }>;
  lowSignalKeys: Array<{ key: string; count: number; uniqueValues: number }>;
  singletonKeys: Array<{ key: string; count: number }>;
}

const API = axios.create({
  baseURL: '/api',
  timeout: 15000,
});

export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (!axios.isAxiosError(error)) {
    return fallback;
  }

  const detail = error.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }
  if (detail && typeof detail === 'object') {
    const message = 'message' in detail ? detail.message : undefined;
    if (typeof message === 'string' && message.trim()) {
      return message;
    }
  }
  if (typeof error.message === 'string' && error.message.trim()) {
    return error.message;
  }
  return fallback;
}

export const apiService = {
  checkHealth: async () => (await API.get('/health')).data,

  getConfig: async () => (await API.get<AppConfig>('/config')).data,

  updateConfig: async (graph_path: string) => (await API.post('/config', { graph_path })).data,

  search: async (query: string, graph_path?: string, case_sensitive = false) =>
    (await API.post<SearchResponse>('/search', { query, graph_path, case_sensitive })).data,

  buildCache: async (graph_path: string) => (await API.post('/cache/build', { graph_path })).data,

  getStats: async () => (await API.get<KeyStatsResponse>('/stats')).data,

  getDiagnostics: async () => (await API.get<DiagnosticsResponse>('/stats/diagnostics')).data,

  getValueDistribution: async (key: string) =>
    (await API.get<ValueDistributionResponse>(`/stats/values/${encodeURIComponent(key)}`)).data,

  getGlobalValueStats: async () =>
    (await API.get<GlobalValueStatsResponse>('/stats/global-values')).data,

  getValueKeyDistribution: async (value: string) =>
    (await API.get<ValueKeyDistributionResponse>('/stats/value-keys', { params: { value } })).data,

  clearCache: async () => (await API.post('/cache/clear')).data,

  clearSortMemory: async () => (await API.post('/config/clear-sort-memory')).data,

  getPreferences: async () => (await API.get<PreferencesResponse>('/preferences')).data,

  saveQueryHistory: async (history: string[]) =>
    (await API.post('/preferences/query-history', { history })).data,

  saveGlobalHiddenColumns: async (columns: string[]) =>
    (await API.post('/preferences/global-hidden-columns', { columns })).data,

  saveColumnConfig: async (queryKey: string, config: unknown) =>
    (await API.post('/preferences/column-config', { query_key: queryKey, config })).data,

  saveSidebarState: async (collapsed: boolean) =>
    (await API.post('/preferences/sidebar', { collapsed })).data,

  saveLanguage: async (language: 'zh' | 'en') =>
    (await API.post('/preferences/language', { language })).data,

  saveQueryCaseSensitive: async (case_sensitive: boolean) =>
    (await API.post('/preferences/query-case-sensitive', { case_sensitive })).data,

  resetAll: async (options?: ResetOptions) => (await API.post('/reset-all', options)).data,

  setAutoUpdate: async (enabled: boolean) =>
    (await API.post('/config/auto-update', { enabled })).data,

  checkUpdates: async () => (await API.get('/check-updates')).data,

  applyUpdates: async () => (await API.post('/apply-updates')).data,

  openDataDir: async () => (await API.post('/open-data-dir')).data,

  openLogDir: async () => (await API.post('/open-log-dir')).data,
};
