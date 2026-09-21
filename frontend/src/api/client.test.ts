import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, request, setAccessToken } from './client';
afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  setAccessToken(null);
});
describe('central API client', () => {
  it('sends JSON and attaches the current bearer token', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ticker: 'AAPL' })));
    vi.stubGlobal('fetch', fetchMock);
    setAccessToken('test-session-token');
    await request('/watchlist', { method: 'POST', body: { ticker: 'AAPL' } });
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer test-session-token');
    expect(fetchMock.mock.calls[0][1].body).toBe('{"ticker":"AAPL"}');
  });
  it('handles an empty successful deletion', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    expect(await request('/watchlist/AAPL', { method: 'DELETE' })).toBeUndefined();
  });
  it('preserves the backend error and status', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            JSON.stringify({ error: { code: 'rate_limit', message: 'Provider limit reached' } }),
            { status: 429 },
          ),
        ),
    );
    await expect(request('/screen')).rejects.toMatchObject({
      status: 429,
      code: 'rate_limit',
      message: 'Provider limit reached',
    });
  });
  it('rejects a non-JSON successful response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>wrong server</html>')));
    await expect(request('/')).rejects.toMatchObject({ code: 'invalid_response' });
  });
  it('turns transport failures into readable errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    await expect(request('/')).rejects.toBeInstanceOf(ApiError);
  });
  it('cancels requests when callers cancel them', async () => {
    const controller = new AbortController();
    controller.abort();
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((_url, options) => Promise.reject(options.signal.reason)),
    );
    await expect(request('/', { signal: controller.signal })).rejects.toMatchObject({
      name: 'AbortError',
    });
  });
  it('clears the session on unauthorized responses', async () => {
    const target = new EventTarget();
    const listener = vi.fn();
    target.addEventListener('session-expired', listener);
    vi.stubGlobal('window', target);
    setAccessToken('expired');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 401 })));
    await expect(request('/auth/me')).rejects.toMatchObject({ status: 401 });
    expect(listener).toHaveBeenCalledOnce();
  });
});
