import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { I18nProvider, useI18n } from '../i18n';


const mockedApi = vi.hoisted(() => ({
  getPreferences: vi.fn(),
  saveLanguage: vi.fn(),
}));

vi.mock('../api', () => ({
  apiService: {
    getPreferences: mockedApi.getPreferences,
    saveLanguage: mockedApi.saveLanguage,
  },
}));


const Probe = () => {
  const { t } = useI18n();
  return <span>{t('nav.settings')}</span>;
};


describe('I18nProvider', () => {
  beforeEach(() => {
    mockedApi.getPreferences.mockReset();
    mockedApi.saveLanguage.mockReset();
    localStorage.clear();
  });

  it('hydrates locale from backend preferences', async () => {
    mockedApi.getPreferences.mockResolvedValue({
      language: 'en',
    });

    render(
      <I18nProvider>
        <Probe />
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText('Settings')).toBeInTheDocument();
    });
  });
});
