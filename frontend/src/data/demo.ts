import snapshot from './demo.json';
import type { Analysis, Portfolio, ScreenResult } from '../types/api';
import { api } from '../api/services';
export const demoPortfolio = snapshot.portfolio as Portfolio;
// Stored backend results. The browser never runs financial scoring or screen rules.
export const demoScreen = snapshot.screen as Omit<ScreenResult, 'performance'>;
export async function getPortfolio(demo: boolean, signal?: AbortSignal) {
  if (!demo)
    return { portfolio: await api.portfolio(false, false, signal), source: 'connected' as const };
  try {
    return { portfolio: await api.portfolio(true, false, signal), source: 'server-demo' as const };
  } catch (error) {
    if (signal?.aborted) throw error;
    return { portfolio: demoPortfolio, source: 'bundled-demo' as const };
  }
}
export function getDemoAnalysis(ticker: string): Analysis {
  const holding = demoPortfolio.holdings.find((item) => item.ticker === ticker);
  if (!holding?.analysis?.metrics || !holding.analysis.score)
    throw new Error(
      'The demo includes equity analysis for AAPL and MSFT. Switch to live research for other tickers.',
    );
  return { ticker, metrics: holding.analysis.metrics, score: holding.analysis.score };
}
