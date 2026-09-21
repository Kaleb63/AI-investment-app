import { ApiError, request } from './client';
import type {
  AIScreenResult,
  Analysis,
  Connection,
  Criteria,
  Historical,
  Portfolio,
  Quote,
  SavedScreen,
  ScanHistory,
  ScreenResult,
  Universe,
  User,
  WatchlistEntry,
} from '../types/api';
const symbol = (ticker: string) => encodeURIComponent(ticker);
function requireContract<T>(value: T, valid: boolean): T {
  if (!valid)
    throw new ApiError(
      'This server is running an older or incompatible API. Restart FastAPI from the current project source and try again.',
      200,
      'incompatible_api',
    );
  return value;
}
export const api = {
  health: (signal?: AbortSignal) => request<{ message: string }>('/', { signal, timeout: 5000 }),
  analysis: async (ticker: string, signal?: AbortSignal) => {
    const data = await request<Analysis>(`/analysis/${symbol(ticker)}`, { signal });
    return requireContract(
      data,
      Boolean(
        data.metrics &&
        data.score &&
        data.score.categories &&
        data.score.weights &&
        Array.isArray(data.score.reasons),
      ),
    );
  },
  quote: (ticker: string, signal?: AbortSignal) =>
    request<Quote>(`/stock/${symbol(ticker)}`, { signal }),
  explanation: (ticker: string) =>
    request<Analysis & { ai_explanation: string }>(`/ai_analysis/${symbol(ticker)}`, {
      timeout: 90000,
    }),
  historical: (ticker: string, signal?: AbortSignal) =>
    request<Historical>(`/historical/${symbol(ticker)}`, { signal }),
  universe: (limit = 100, search = '', offset = 0, signal?: AbortSignal) =>
    request<Universe>(
      `/stock_universe?asset_type=equity&limit=${limit}&offset=${offset}&search=${encodeURIComponent(search)}`,
      { signal },
    ),
  screen: (tickers: string[], criteria: Criteria) =>
    request<ScreenResult>('/screen', {
      method: 'POST',
      body: { tickers, ...criteria },
      timeout: 180000,
    }),
  aiScreen: (query: string, tickers?: string[], universe_limit = 100) =>
    request<AIScreenResult>('/ai_screen', {
      method: 'POST',
      body: { query, ...(tickers ? { tickers } : {}), universe_limit, include_explanations: true },
      timeout: 240000,
    }),
  portfolio: async (demo: boolean, includeAi = false, signal?: AbortSignal) => {
    const data = await request<Portfolio>(
      `${demo ? '/demo' : ''}/portfolio_analysis?include_ai=${includeAi}`,
      { signal, timeout: includeAi ? 90000 : 30000 },
    );
    return requireContract(
      data,
      Boolean(
        Array.isArray(data.holdings) &&
        data.asset_type_allocation &&
        data.sector_allocation &&
        typeof data.total_value === 'number',
      ),
    );
  },
  login: (email: string, password: string) =>
    request<{ access_token: string }>('/auth/login', { method: 'POST', body: { email, password } }),
  register: (email: string, password: string) =>
    request<User>('/auth/register', { method: 'POST', body: { email, password } }),
  me: () => request<User>('/auth/me'),
  watchlist: (signal?: AbortSignal) => request<WatchlistEntry[]>('/watchlist', { signal }),
  addWatchlist: (ticker: string) =>
    request<WatchlistEntry>('/watchlist', { method: 'POST', body: { ticker } }),
  removeWatchlist: (ticker: string) =>
    request<void>(`/watchlist/${symbol(ticker)}`, { method: 'DELETE' }),
  analyzeWatchlist: () => request<ScreenResult>('/watchlist/analysis', { timeout: 180000 }),
  savedScreens: (signal?: AbortSignal) => request<SavedScreen[]>('/saved_screens', { signal }),
  saveScreen: (name: string, criteria: Criteria) =>
    request<SavedScreen>('/saved_screens', { method: 'POST', body: { name, criteria } }),
  deleteScreen: (id: string) =>
    request<void>(`/saved_screens/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  history: (signal?: AbortSignal) => request<ScanHistory[]>('/scan_history', { signal }),
  connections: (signal?: AbortSignal) => request<Connection[]>('/plaid/connections', { signal }),
  linkToken: () => request<{ link_token: string }>('/create_link_token', { method: 'POST' }),
  exchangeToken: (public_token: string, institution_id?: string, institution_name?: string) =>
    request<Connection>('/exchange_public_token', {
      method: 'POST',
      body: { public_token, institution_id, institution_name },
    }),
  removeConnection: (id: string) =>
    request<void>(`/plaid/connections/${encodeURIComponent(id)}`, { method: 'DELETE' }),
};
