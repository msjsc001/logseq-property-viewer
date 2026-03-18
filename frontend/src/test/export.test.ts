import { describe, expect, it } from 'vitest';

import { buildCsvContent, stripInternalFields } from '../utils/export';


describe('export helpers', () => {
  it('adds a BOM for Excel-friendly CSV exports', () => {
    const csv = buildCsvContent([{ page: '中文页面', status: 'done' }], ['page', 'status']);
    expect(csv.startsWith('\uFEFF')).toBe(true);
    expect(csv).toContain('"中文页面"');
  });

  it('removes transport-only fields from exported rows', () => {
    const rows = stripInternalFields([
      {
        id: 1,
        page: 'Test',
        block_content: '- task',
        content: '- task',
        file_path: 'a.md',
        block_path: 'Test',
        properties: { status: 'done' },
      },
    ]);
    expect(rows[0]).not.toHaveProperty('id');
    expect(rows[0]).not.toHaveProperty('content');
    expect(rows[0]).toHaveProperty('block_content', '- task');
  });
});
