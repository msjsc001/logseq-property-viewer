import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { message } from 'antd';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import QueryPage from '../components/QueryPage';
import { I18nProvider } from '../i18n';


const mockedApi = vi.hoisted(() => ({
  getPreferences: vi.fn(),
  saveQueryHistory: vi.fn(),
  saveGlobalHiddenColumns: vi.fn(),
  saveColumnConfig: vi.fn(),
  saveQueryCaseSensitive: vi.fn(),
  search: vi.fn(),
}));

vi.mock('../api', () => ({
  apiService: {
    getPreferences: mockedApi.getPreferences,
    saveQueryHistory: mockedApi.saveQueryHistory,
    saveGlobalHiddenColumns: mockedApi.saveGlobalHiddenColumns,
    saveColumnConfig: mockedApi.saveColumnConfig,
    saveQueryCaseSensitive: mockedApi.saveQueryCaseSensitive,
    search: mockedApi.search,
  },
}));

vi.mock('../utils/errors', () => ({
  toUserMessage: vi.fn((_error: unknown, fallback: string) => fallback),
}));


describe('QueryPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(message, 'success').mockImplementation(() => message as never);
    vi.spyOn(message, 'error').mockImplementation(() => message as never);
    vi.spyOn(message, 'warning').mockImplementation(() => message as never);
    mockedApi.getPreferences.mockReset();
    mockedApi.saveQueryHistory.mockReset();
    mockedApi.saveGlobalHiddenColumns.mockReset();
    mockedApi.saveColumnConfig.mockReset();
    mockedApi.saveQueryCaseSensitive.mockReset();
    mockedApi.search.mockReset();

    mockedApi.getPreferences.mockResolvedValue({
      query_history: [],
      global_hidden_columns: [],
      column_configs: {},
      sidebar_collapsed: false,
      auto_update_enabled: false,
      query_case_sensitive: false,
      graph_name: 'main',
      language: 'zh',
      data_dir: 'D:/AppData/PropertyQuery',
      log_dir: 'D:/AppData/PropertyQuery/logs',
      cache_version: 3,
    });
    mockedApi.saveQueryHistory.mockResolvedValue({ status: 'success' });
    mockedApi.saveGlobalHiddenColumns.mockResolvedValue({ status: 'success' });
    mockedApi.saveColumnConfig.mockResolvedValue({ status: 'success' });
    mockedApi.saveQueryCaseSensitive.mockResolvedValue({
      status: 'success',
      query_case_sensitive: true,
    });
    mockedApi.search.mockResolvedValue({
      count: 1,
      results: [
        {
          id: 1,
          page: 'Sample',
          block_content: 'ai-提示词:: [[提示词-书籍总结]]',
          content: 'ai-提示词:: [[提示词-书籍总结]]',
          file_path: 'D:/Graph/pages/Sample.md',
          block_path: 'Sample',
          properties: { 'ai-提示词': '[[提示词-书籍总结]]' },
        },
      ],
    });
  });

  it('shows mode-based help content and sends the case sensitivity flag with search', async () => {
    render(
      <I18nProvider>
        <QueryPage />
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(mockedApi.getPreferences).toHaveBeenCalled();
    });

    fireEvent.click(screen.getByRole('button', { name: '查询帮助' }));

    expect(await screen.findByText('精确匹配模式')).toBeInTheDocument();
    expect(screen.getByText('模糊匹配模式')).toBeInTheDocument();
    expect(screen.getByText('键存在模式')).toBeInTheDocument();
    expect(screen.getByText('全文模式')).toBeInTheDocument();
    expect(screen.getByText('has:ai-提示词')).toBeInTheDocument();

    const caseSensitiveToggle = screen.getByRole('button', { name: '大小写敏感' });
    expect(caseSensitiveToggle).toHaveAttribute('aria-pressed', 'false');

    fireEvent.click(caseSensitiveToggle);

    await waitFor(() => {
      expect(mockedApi.saveQueryCaseSensitive).toHaveBeenCalledWith(true);
    });
    expect(caseSensitiveToggle).toHaveAttribute('aria-pressed', 'true');

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'has:ai-提示词' } });
    fireEvent.click(screen.getByRole('button', { name: /搜索/ }));

    await waitFor(() => {
      expect(mockedApi.search).toHaveBeenCalledWith('has:ai-提示词', undefined, true);
    });
  });

  it('restores the saved case sensitivity preference from backend preferences', async () => {
    mockedApi.getPreferences.mockResolvedValueOnce({
      query_history: [],
      global_hidden_columns: [],
      column_configs: {},
      sidebar_collapsed: false,
      auto_update_enabled: false,
      query_case_sensitive: true,
      graph_name: 'main',
      language: 'zh',
      data_dir: 'D:/AppData/PropertyQuery',
      log_dir: 'D:/AppData/PropertyQuery/logs',
      cache_version: 3,
    });

    render(
      <I18nProvider>
        <QueryPage />
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '大小写敏感' })).toHaveAttribute(
        'aria-pressed',
        'true',
      );
    });
  });
});
