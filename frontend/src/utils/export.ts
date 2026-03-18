import type { SearchResultItem } from '../api';

export function stripInternalFields(rows: SearchResultItem[]): Record<string, unknown>[] {
  return rows.map((row) =>
    Object.fromEntries(
      Object.entries(row).filter(([key]) => !['id', 'content'].includes(key)),
    ),
  );
}

export function buildCsvContent(
  rows: Record<string, unknown>[],
  headers: string[],
): string {
  const csvRows = [headers.join(',')];
  rows.forEach((row) => {
    const values = headers.map((header) => {
      const value = String(row[header] ?? '').replace(/"/g, '""');
      return `"${value}"`;
    });
    csvRows.push(values.join(','));
  });
  return `\uFEFF${csvRows.join('\n')}`;
}
