import { describe, expect, it } from 'vitest';
import { currency, number, parseCriteria, parseTickers, percent } from './format';
describe('financial display', () => {
  it('distinguishes missing values from genuine zeros', () => {
    expect(currency(null)).toBe('N/A');
    expect(currency(0)).toBe('$0.00');
    expect(number(undefined)).toBe('N/A');
    expect(number(0)).toBe('0');
    expect(percent(null)).toBe('N/A');
    expect(percent(0)).toBe('0%');
    expect(percent(Number.NaN)).toBe('N/A');
  });
  it('displays backend percentage points without multiplying them', () => {
    expect(percent(18.42)).toBe('18.42%');
  });
});
describe('screen inputs', () => {
  it('omits blank criteria while retaining zero and negative thresholds', () => {
    expect(
      parseCriteria({
        min_score: '',
        max_pe_ratio: ' ',
        min_current_ratio: '0',
        min_revenue_growth: '-5',
      }),
    ).toEqual({ min_current_ratio: 0, min_revenue_growth: -5 });
  });
  it('rejects invalid numerical constraints', () => {
    const inputs: Record<string, string>[] = [
      { min_score: '101' },
      { max_pe_ratio: '0' },
      { min_current_ratio: '-1' },
      { min_score: 'Infinity' },
    ];
    for (const input of inputs) expect(() => parseCriteria(input)).toThrow();
  });
  it('normalizes and deduplicates user-supplied symbols', () => {
    expect(parseTickers(' aapl, MSFT; aapl BRK.B ')).toEqual(['AAPL', 'MSFT', 'BRK.B']);
  });
  it('rejects empty or malformed symbols before any API request', () => {
    expect(() => parseTickers('')).toThrow();
    expect(() => parseTickers('AAPL, invalid/ticker')).toThrow();
  });
});
