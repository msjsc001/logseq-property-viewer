import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ChartsPage from '../components/ChartsPage';
import { I18nProvider } from '../i18n';


const mockedApi = vi.hoisted(() => ({
  getPreferences: vi.fn(),
  saveLanguage: vi.fn(),
  getStats: vi.fn(),
  getDiagnostics: vi.fn(),
  getGlobalValueStats: vi.fn(),
  getValueKeyDistribution: vi.fn(),
  getValueDistribution: vi.fn(),
}));

vi.mock('echarts-for-react', () => ({
  default: () => <div data-testid="echarts" />,
}));

vi.mock('../api', () => ({
  getApiErrorMessage: vi.fn((_error: unknown, fallback: string) => fallback),
  apiService: {
    getPreferences: mockedApi.getPreferences,
    saveLanguage: mockedApi.saveLanguage,
    getStats: mockedApi.getStats,
    getDiagnostics: mockedApi.getDiagnostics,
    getGlobalValueStats: mockedApi.getGlobalValueStats,
    getValueKeyDistribution: mockedApi.getValueKeyDistribution,
    getValueDistribution: mockedApi.getValueDistribution,
  },
}));


describe('ChartsPage', () => {
  beforeEach(() => {
    localStorage.clear();
    mockedApi.getPreferences.mockReset();
    mockedApi.saveLanguage.mockReset();
    mockedApi.getStats.mockReset();
    mockedApi.getDiagnostics.mockReset();
    mockedApi.getGlobalValueStats.mockReset();
    mockedApi.getValueKeyDistribution.mockReset();
    mockedApi.getValueDistribution.mockReset();

    mockedApi.getPreferences.mockResolvedValue({ language: 'zh' });
    mockedApi.saveLanguage.mockResolvedValue({ status: 'success', language: 'zh' });
    mockedApi.getStats.mockResolvedValue({
      keys: [{ key: 'status', count: 4, uniqueValues: 3 }],
      total: 1,
    });
    mockedApi.getDiagnostics.mockResolvedValue({
      emptyValues: [],
      caseConflicts: [],
      suspectedSynonyms: [],
      lowSignalKeys: [],
      singletonKeys: [],
    });
    mockedApi.getGlobalValueStats.mockResolvedValue({
      values: [
        {
          value: 'done',
          count: 4,
          keyCount: 3,
          topKeys: [
            { key: 'status', count: 2 },
            { key: 'review', count: 1 },
            { key: 'result', count: 1 },
          ],
        },
        {
          value: '',
          count: 1,
          keyCount: 1,
          topKeys: [{ key: 'empty', count: 1 }],
        },
      ],
      total: 2,
    });
    mockedApi.getValueKeyDistribution.mockResolvedValue({
      value: 'done',
      keys: [
        { key: 'status', count: 2 },
        { key: 'review', count: 1 },
        { key: 'result', count: 1 },
      ],
      total: 3,
    });
    mockedApi.getValueDistribution.mockResolvedValue({
      values: [{ value: 'done', count: 2 }],
      total: 1,
    });
  });

  it('shows the new segmented order and renders global value stats including empty values', async () => {
    render(
      <I18nProvider>
        <ChartsPage />
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(mockedApi.getStats).toHaveBeenCalled();
      expect(mockedApi.getDiagnostics).toHaveBeenCalled();
    });

    expect(screen.getByRole('radio', { name: '键统计' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: '值统计' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: '数据诊断' })).toBeInTheDocument();

    fireEvent.click(screen.getByText('值统计'));

    await waitFor(() => {
      expect(mockedApi.getGlobalValueStats).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText('(空值)')).toBeInTheDocument();
      expect(screen.getByText('所有值（共 2 个，总出现 5 次）')).toBeInTheDocument();
    });
  });

  it('drills from a global value into its key distribution', async () => {
    render(
      <I18nProvider>
        <ChartsPage />
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(mockedApi.getStats).toHaveBeenCalled();
    });

    fireEvent.click(screen.getByText('值统计'));

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: '查看键分布' }).length).toBeGreaterThan(0);
    });

    fireEvent.click(screen.getAllByRole('button', { name: '查看键分布' })[0]);

    await waitFor(() => {
      expect(mockedApi.getValueKeyDistribution).toHaveBeenCalledWith('done');
      expect(screen.getByText(/当前值:/)).toBeInTheDocument();
      expect(screen.getByText('status')).toBeInTheDocument();
      expect(screen.getByText('review')).toBeInTheDocument();
      expect(screen.getByTestId('echarts')).toBeInTheDocument();
    });
  });
});
