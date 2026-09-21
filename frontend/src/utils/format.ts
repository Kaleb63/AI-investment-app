export function number(value: number | null | undefined, digits = 1) {
  return value == null || !Number.isFinite(value)
    ? 'N/A'
    : new Intl.NumberFormat('en-US', { maximumFractionDigits: digits }).format(value);
}
export function currency(value: number | null | undefined) {
  return value == null || !Number.isFinite(value)
    ? 'N/A'
    : new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        maximumFractionDigits: 2,
      }).format(value);
}
export function percent(value: number | null | undefined) {
  return value == null || !Number.isFinite(value) ? 'N/A' : `${number(value, 2)}%`;
}
export function label(value: string) {
  return value.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());
}
export function date(value: string) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? 'N/A'
    : parsed.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}
export const tickerPattern = /^[A-Z][A-Z0-9.\-]{0,14}$/;
export function parseTickers(value: string) {
  const tickers = [
    ...new Set(
      value
        .toUpperCase()
        .split(/[\s,;]+/)
        .filter(Boolean),
    ),
  ];
  if (!tickers.length) throw new Error('Enter at least one ticker.');
  if (tickers.some((ticker) => !tickerPattern.test(ticker)))
    throw new Error('Use valid ticker symbols, such as AAPL or BRK.B.');
  return tickers;
}
export const criteriaFields = [
  ['min_score', 'Minimum score', '', 0, 100],
  ['max_pe_ratio', 'Maximum P/E', '×', 0.01],
  ['min_revenue_growth', 'Minimum revenue growth', '%'],
  ['min_eps_growth', 'Minimum EPS growth', '%'],
  ['min_profit_margin', 'Minimum profit margin', '%'],
  ['min_return_on_equity', 'Minimum return on equity', '%'],
  ['min_current_ratio', 'Minimum current ratio', '×', 0],
] as const;
export function parseCriteria(values: Record<string, string>) {
  const result: Record<string, number> = {};
  for (const [key, value] of Object.entries(values)) {
    if (value.trim() === '') continue;
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) throw new Error('Criteria must be finite numbers.');
    if (key === 'min_score' && (numeric < 0 || numeric > 100))
      throw new Error('Score must be between 0 and 100.');
    if (key === 'max_pe_ratio' && numeric <= 0)
      throw new Error('Maximum P/E must be greater than zero.');
    if (key === 'min_current_ratio' && numeric < 0)
      throw new Error('Current ratio cannot be negative.');
    result[key] = numeric;
  }
  return result;
}
