import { afterEach, expect, it, vi } from 'vitest';
import { api } from './services';
afterEach(() => vi.unstubAllGlobals());
it('rejects older stock response contracts with an actionable message', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(new Response('{"ticker":"AAPL","overall_score":80}')),
  );
  await expect(api.analysis('AAPL')).rejects.toMatchObject({ code: 'incompatible_api' });
});
it('rejects older portfolio response contracts instead of rendering them', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"portfolio":[]}')));
  await expect(api.portfolio(false)).rejects.toMatchObject({ code: 'incompatible_api' });
});
