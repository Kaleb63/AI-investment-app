import { test, expect, type Page } from '@playwright/test';
import snapshot from '../src/data/demo.json' with { type: 'json' };
const analysis = snapshot.screen.matching_stocks[0];
const user = { id: 'test-user', email: 'research@example.test', created_at: '2026-01-01' };
const result = {
  ...snapshot.screen,
  performance: {
    duration_seconds: 0.3,
    stocks_attempted: 2,
    stocks_successfully_analyzed: 2,
    stocks_failed: 0,
    average_processing_seconds: 0.15,
    successful_stocks_per_second: 6.6,
    failure_percentage: 0,
    cache_hits: 0,
    cache_misses: 2,
  },
};
async function setup(page: Page) {
  const failures: string[] = [];
  page.on('pageerror', (error) => failures.push(error.message));
  let watchlist: { id: string; ticker: string; created_at: string }[] = [];
  let saved: { id: string; name: string; criteria: object; created_at: string }[] = [];
  await page.route('http://127.0.0.1:8000/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    const method = route.request().method();
    let body: unknown = {};
    let status = 200;
    if (method === 'OPTIONS')
      return route.fulfill({
        status: 204,
        headers: {
          'access-control-allow-origin': '*',
          'access-control-allow-headers': '*',
          'access-control-allow-methods': '*',
        },
      });
    if (path === '/') body = { message: 'Investment app backend is running' };
    else if (path === '/demo/portfolio_analysis') {
      status = 404;
      body = { error: { message: 'Demo endpoint disabled for offline fallback test' } };
    } else if (path.startsWith('/analysis/'))
      body = {
        ...analysis,
        ticker: path.split('/').at(-1),
        metrics: { ...analysis.metrics, eps: null, current_ratio: 0 },
      };
    else if (path.startsWith('/stock/'))
      body = {
        ticker: 'AAPL',
        price: 201.25,
        quote: { c: 201.25, d: 0, dp: 0, h: 203, l: 199, o: 201.25, pc: 201.25, t: 1 },
      };
    else if (path.startsWith('/ai_analysis/')) {
      status = 503;
      body = { error: { message: 'AI provider is unavailable' } };
    } else if (path.startsWith('/historical/'))
      body = {
        ticker: 'AAPL',
        start_date: '2025-01-01',
        end_date: '2026-01-01',
        observations: 252,
        latest_close: 201.25,
        returns: { one_month: 0, three_month: null, six_month: 12.8, one_year: 19 },
        annualized_volatility: 21.1,
        moving_averages: { sma_50: 199, sma_200: 183 },
        note: 'Separate from scoring',
      };
    else if (path === '/stock_universe')
      body = {
        source: 'finnhub',
        total_available: 2,
        offset: 0,
        limit: 100,
        symbols: [
          { ticker: 'AAPL', name: 'Apple', asset_type: 'equity', exchange: 'US' },
          { ticker: 'MSFT', name: 'Microsoft', asset_type: 'equity', exchange: 'US' },
        ],
      };
    else if (path === '/screen' || path === '/watchlist/analysis') body = result;
    else if (path === '/ai_screen')
      body = {
        query: route.request().postDataJSON().query,
        interpreted_criteria: snapshot.screen.criteria,
        number_of_stocks_searched: 2,
        results: result,
        explanation_errors: { AAPL: 'AI explanation unavailable' },
      };
    else if (path === '/auth/register' || path === '/auth/me') body = user;
    else if (path === '/auth/login') body = { access_token: 'test-token', token_type: 'bearer' };
    else if (path === '/portfolio_analysis') body = { ...snapshot.portfolio, simulated: false };
    else if (path === '/plaid/connections') body = [];
    else if (path === '/create_link_token') body = { link_token: 'link-test' };
    else if (path === '/exchange_public_token')
      body = {
        id: 'connection',
        item_id: 'item',
        institution_id: 'ins_test',
        institution_name: 'Test institution',
        connection_status: 'active',
      };
    else if (path === '/watchlist' && method === 'POST') {
      const ticker = route.request().postDataJSON().ticker;
      const entry = { id: ticker, ticker, created_at: '2026-01-01' };
      watchlist.push(entry);
      body = entry;
    } else if (path === '/watchlist') body = watchlist;
    else if (path.startsWith('/watchlist/') && method === 'DELETE') {
      watchlist = watchlist.filter((item) => item.ticker !== path.split('/').at(-1));
      status = 204;
    } else if (path === '/saved_screens' && method === 'POST') {
      const entry = { id: 'saved-1', ...route.request().postDataJSON(), created_at: '2026-01-01' };
      saved.push(entry);
      body = entry;
    } else if (path === '/saved_screens') body = saved;
    else if (path.startsWith('/saved_screens/') && method === 'DELETE') {
      saved = [];
      status = 204;
    } else if (path === '/scan_history')
      body = [
        {
          id: 'scan-1',
          criteria: snapshot.screen.criteria,
          stocks_analyzed: 2,
          matches: 1,
          failures: 0,
          duration_seconds: 0.3,
          created_at: '2026-01-01',
        },
      ];
    else {
      status = 404;
      body = { error: { message: 'Test route not found' } };
    }
    await route.fulfill({
      status,
      contentType: 'application/json',
      headers: { 'access-control-allow-origin': '*' },
      body: status === 204 ? undefined : JSON.stringify(body),
    });
  });
  return failures;
}
async function nav(page: Page, name: string) {
  const mobile = page.getByRole('button', { name: 'Open navigation' });
  if (await mobile.isVisible()) {
    await mobile.click();
    await page.getByRole('dialog').getByRole('link', { name, exact: true }).click();
  } else await page.locator('aside').getByRole('link', { name, exact: true }).click();
}
async function live(page: Page) {
  await page.getByRole('button', { name: 'Demo mode', exact: true }).click();
}
async function signIn(page: Page) {
  await page.goto('/login');
  await page.getByLabel('Email address').fill(user.email);
  await page.getByLabel('Password', { exact: true }).fill('test-password-123');
  await page.locator('form').getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'A clearer view of your investments.' }),
  ).toBeVisible();
}

test('dashboard, simulated holdings, stock research and responsive layout', async ({
  page,
}, info) => {
  const failures = await setup(page);
  await page.goto('/');
  await expect(page.getByText('$8,000.00', { exact: true })).toBeVisible();
  await expect(page.getByText(/Offline demo snapshot/)).toBeVisible();
  await expect(page.getByText('Not analyzed', { exact: true })).toHaveCount(2);
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy();
  await page.screenshot({
    path: `test-results/dashboard-${info.project.name}.png`,
    fullPage: true,
  });
  await nav(page, 'Holdings');
  await expect(
    page.getByRole('heading', { name: 'Every position. One perspective.' }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy();
  await page.getByRole('link', { name: 'AAPL', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Investment score' })).toBeVisible();
  await expect(page.getByText('75.6', { exact: true })).toBeVisible();
  await expect(page.getByText('Illustrative commentary · not AI generated')).toBeVisible();
  expect(failures).toEqual([]);
});
test('demo screen distinguishes rejection from unavailability and opens consistent stock details', async ({
  page,
}) => {
  await setup(page);
  await page.goto('/screener');
  await page.getByRole('button', { name: 'View sample results' }).click();
  await expect(page.getByRole('link', { name: 'AAPL', exact: true })).toBeVisible();
  await page.getByRole('tab', { name: 'Rejected' }).click();
  await page.locator('summary').filter({ hasText: 'MSFT' }).click();
  await expect(page.getByText(/reported 32; required at most 30/)).toBeVisible();
  await page.getByRole('tab', { name: 'Unavailable' }).click();
  await expect(
    page.getByRole('heading', { name: 'All selected stocks were evaluated' }),
  ).toBeVisible();
});
test('live stock keeps deterministic data when AI fails and preserves missing versus zero', async ({
  page,
}) => {
  await setup(page);
  await page.goto('/stocks/AAPL');
  await live(page);
  await expect(page.getByText('$201.25', { exact: true })).toBeVisible();
  await expect(
    page.locator('.metric').filter({ hasText: 'Earnings per share' }).getByText('N/A'),
  ).toBeVisible();
  await expect(
    page.locator('.metric').filter({ hasText: 'Current ratio' }).getByText('0', { exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Generate explanation' }).click();
  await expect(page.getByText('AI provider is unavailable')).toBeVisible();
  await expect(page.getByText('75.6', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Load historical statistics' }).click();
  await expect(page.getByText('252 observations', { exact: false })).toBeVisible();
});
test('live screen sends only populated criteria and deduplicated tickers', async ({ page }) => {
  await setup(page);
  await page.goto('/screener');
  await live(page);
  await page.getByLabel('Minimum score', { exact: true }).fill('70');
  await page.getByLabel('Tickers', { exact: true }).fill('aapl, MSFT, AAPL');
  const request = page.waitForRequest(
    (request) => request.url().endsWith('/screen') && request.method() === 'POST',
  );
  await page.getByRole('button', { name: 'Run screen', exact: true }).click();
  expect((await request).postDataJSON()).toEqual({ tickers: ['AAPL', 'MSFT'], min_score: 70 });
  await expect(page.getByRole('heading', { name: 'Screening results' })).toBeVisible();
  await page.getByRole('columnheader', { name: 'P/E' }).getByRole('button').click();
  await expect(page.getByRole('columnheader', { name: 'P/E' })).toHaveAttribute(
    'aria-sort',
    'ascending',
  );
});
test('natural-language search displays interpreted criteria and partial explanation errors', async ({
  page,
}) => {
  await setup(page);
  await page.goto('/ai-search');
  await live(page);
  await page
    .getByLabel('Describe your investment criteria')
    .fill('Find profitable companies with reasonable valuations.');
  await page.getByRole('button', { name: 'Search companies' }).click();
  await expect(page.getByRole('heading', { name: 'We interpreted your search as' })).toBeVisible();
  await expect(page.getByText(/Some AI explanations were unavailable/)).toBeVisible();
  await expect(page.getByRole('link', { name: 'AAPL', exact: true })).toBeVisible();
});
test('authenticated watchlist, saved screens, history and sign-out', async ({ page }) => {
  const failures = await setup(page);
  await signIn(page);
  await nav(page, 'Watchlist');
  await page.getByLabel('Ticker to add').fill('aapl');
  await page.getByRole('button', { name: 'Add ticker', exact: true }).click();
  await expect(page.getByRole('link', { name: 'AAPL', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Remove AAPL from watchlist' }).click();
  await expect(page.getByRole('heading', { name: 'A watchlist worth watching' })).toBeVisible();
  await nav(page, 'Stock screener');
  await page.getByRole('button', { name: 'Run screen', exact: true }).click();
  await page.getByLabel('Screen name').fill('Quality research');
  await page.getByRole('button', { name: 'Save criteria' }).click();
  await expect(page.getByText('Screen saved.')).toBeVisible();
  await nav(page, 'Saved screens');
  await expect(page.getByRole('heading', { name: 'Quality research' })).toBeVisible();
  await page.getByRole('link', { name: 'Load criteria' }).click();
  await expect(page.getByLabel('Minimum score', { exact: true })).toHaveValue('70');
  await nav(page, 'Research history');
  await expect(page.getByRole('link', { name: 'Reuse' })).toBeVisible();
  await nav(page, 'Settings');
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await nav(page, 'Watchlist');
  await expect(page.getByRole('heading', { name: 'Your watchlist, in one place' })).toBeVisible();
  expect(failures).toEqual([]);
});
test('direct routes and mobile drawer keyboard dismissal', async ({ page }, info) => {
  await setup(page);
  await page.goto('/not-a-real-page');
  await expect(
    page.getByRole('heading', { name: 'This page isn’t in the workspace' }),
  ).toBeVisible();
  await page.getByRole('link', { name: 'Back to dashboard' }).click();
  await expect(page.getByText('$8,000.00', { exact: true })).toBeVisible();
  if (info.project.name === 'mobile') {
    await page.getByRole('button', { name: 'Open navigation' }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).not.toBeVisible();
    await expect(page.getByRole('button', { name: 'Open navigation' })).toBeFocused();
  }
});
test('registration validates password length and opens a private session', async ({ page }) => {
  await setup(page);
  await page.goto('/login');
  await page.getByRole('button', { name: 'Create an account', exact: true }).click();
  await expect(page.getByLabel('Password', { exact: true })).toHaveAttribute('minlength', '12');
  await page.getByLabel('Email address').fill(user.email);
  await page.getByLabel('Password', { exact: true }).fill('a-valid-test-password');
  const registration = page.waitForRequest((request) => request.url().endsWith('/auth/register'));
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  expect((await registration).postDataJSON().email).toBe(user.email);
  await expect(page.getByRole('button', { name: 'Live research', exact: true })).toBeVisible();
});
test('Plaid sends only its public token and institution metadata to the backend', async ({
  page,
}) => {
  await setup(page);
  await page.route('https://cdn.plaid.com/**', (route) =>
    route.fulfill({
      contentType: 'application/javascript',
      body: `window.Plaid = { create(options) { setTimeout(() => options.onLoad?.(), 0); return { open() { options.onSuccess('public-test-token', { institution: { institution_id: 'ins_test', name: 'Test institution' } }); }, exit() {}, destroy() {}, submit() {} }; } };`,
    }),
  );
  await signIn(page);
  await nav(page, 'Overview');
  const create = page.waitForRequest((request) => request.url().endsWith('/create_link_token'));
  await page.getByRole('button', { name: 'Connect investment account' }).click();
  expect((await create).headers().authorization).toBe('Bearer test-token');
  const exchange = page.waitForRequest((request) =>
    request.url().endsWith('/exchange_public_token'),
  );
  await page.getByRole('button', { name: 'Continue with Plaid' }).click();
  expect((await exchange).postDataJSON()).toEqual({
    public_token: 'public-test-token',
    institution_id: 'ins_test',
    institution_name: 'Test institution',
  });
  await expect(page.getByText('Account connected. Your holdings are refreshing.')).toBeVisible();
});
test('backend errors are visible and a retry recovers without changing data mode', async ({
  page,
}) => {
  await setup(page);
  let failed = true;
  await page.route('http://127.0.0.1:8000/analysis/AAPL', (route) =>
    route.fulfill({
      status: failed ? 429 : 200,
      contentType: 'application/json',
      headers: { 'access-control-allow-origin': '*' },
      body: JSON.stringify(
        failed ? { error: { message: 'Market data is temporarily rate limited.' } } : analysis,
      ),
    }),
  );
  await page.goto('/stocks/AAPL');
  await live(page);
  await expect(page.getByText('Market data is temporarily rate limited.')).toBeVisible();
  failed = false;
  await page.getByRole('button', { name: 'Try again' }).click();
  await expect(page.getByText('75.6', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Live research', exact: true })).toBeVisible();
});
