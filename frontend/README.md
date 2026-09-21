# Aether investment research frontend

A complete React + TypeScript research interface for the existing FastAPI project. The visual theme uses deep navy surfaces, cyan accents, fine borders, and a circular intelligence graphic inspired by the supplied reference.

## Start on this Windows computer

Open PowerShell and run:

```powershell
cd C:\Users\kla89\Documents\AI-investment-app\frontend
.\Start-Frontend.ps1
```

The launcher uses an installed Node.js runtime or the bundled Codex runtime on this computer. If dependencies are missing, it installs the exact versions from the lockfile. It does not change the PowerShell execution policy. If your shell blocks local scripts, use the direct command below after dependency installation:

```powershell
cd C:\Users\kla89\Documents\AI-investment-app\frontend
& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" .\node_modules\vite\bin\vite.js --host 127.0.0.1 --port 3000
```

Open **http://127.0.0.1:3000**. You should see the Aether dashboard with a dark navy sidebar, cyan circular illustration, a clearly labeled $8,000 simulated portfolio, and four sample positions. The app starts in demo mode so no sign-in or brokerage connection is required.

With a normal Node.js installation (Node 22.12+ recommended), the standard commands are:

```powershell
npm ci
npm run dev
```

## Connect the current backend

The default API URL is `http://127.0.0.1:8000`. Override it by copying `.env.example` to `.env` **inside the frontend folder** and editing `VITE_API_BASE_URL`. Restart Vite after changing an environment variable. Every `VITE_` variable is public browser configuration; never put provider credentials there.

The backend inspected for this implementation already permits `http://localhost:3000` and `http://127.0.0.1:3000` through CORS. Port 3000 is fixed so Vite cannot silently move to an unapproved origin.

During implementation, the process already running on port 8000 exposed an older route set than the backend source on disk. Restart that backend from the current repository in your existing Python environment:

```powershell
cd C:\Users\kla89\Documents\AI-investment-app
uvicorn backend.main:app --reload
```

Stop the old server in its own terminal first. Keep your existing backend `.env`, credentials, database, and migrations. Follow the root backend README if its Python dependencies or database have not yet been initialized. The frontend changes do not alter them.

Check `http://127.0.0.1:8000/docs` for `/auth/login`, `/screen`, `/ai_screen`, `/demo/portfolio_analysis`, `/watchlist`, `/saved_screens`, and `/scan_history`. A root health response only proves that the server is reachable; it does not prove that all providers are configured.

## What is implemented

- **Dashboard:** portfolio summary, real backend allocation values, holdings, research shortcuts, and recent analysis from the current browser session.
- **Stock research:** ticker search, quote, deterministic score, category weights, metrics, backend reasons, separate on-demand AI interpretation, and historical return/volatility/moving-average statistics.
- **Screener:** optional numeric criteria, custom ticker lists or a bounded U.S. equity universe, input validation, sortable matches, rejected criteria, missing-data explanations, summary counts, and saved criteria for signed-in accounts.
- **AI search:** natural-language input, interpreted criteria, reusable screening results, and partial AI-explanation error handling.
- **Portfolio and holdings:** Plaid Link, public-token exchange, allocation chart, sector percentage bars, concentration measures, equity scores, and optional AI insights.
- **Account:** registration, login, logout, and expired-session handling. Private views require a signed-in account; the backend enforces authorization.
- **Library:** watchlist add/remove/analyze, saved-screen create/load/delete, account scan history, and session-only recent stock analysis.
- **Settings:** live/demo switch, server connectivity, account status, connection listing/removal, and an explanation of the research approach.
- **Shared behavior:** mobile navigation drawer, keyboard focus states, reduced-motion support, loading/empty/error states, request cancellation and timeouts, missing values as N/A, route-level code splitting, and unknown-route handling.

## Honest boundaries

- Financial scores, allocations, concentration, and screening decisions are never calculated in the browser. Display formatting, chart geometry, input validation, and sorting existing values are frontend responsibilities.
- The demo portfolio first requests the backend’s simulated portfolio. If unavailable, it displays a labeled bundled snapshot derived from the existing backend scoring and portfolio code.
- Offline stock analysis covers AAPL and MSFT. Offline screening and AI discovery are guided **stored examples**, not arbitrary local financial screening or live AI. Switch to live research to change their criteria/query.
- Demo commentary is explicitly marked illustrative, not AI generated. No successful AI request is invented.
- Cash and ETFs show “Not analyzed” rather than an equity score.
- The historical endpoint provides summary statistics, not a candle/price series. The frontend displays those real statistics without inventing a price chart.
- The backend stores stock-analysis history internally but exposes no read endpoint for it. Recent stock analysis is therefore labeled “this browser session only.” Scan history uses the existing backend endpoint.
- The bearer token is held in memory, not localStorage. Refreshing the page signs the user out. Persisted watchlists/screens remain in the backend. Changing data mode and signing out clear cached private results.
- “Remove saved connection” deletes the app’s stored connection using the existing backend endpoint. It does not claim to revoke permissions at the institution.
- Real provider access depends on Finnhub, OpenAI, and Plaid configuration and plan permissions. The browser tests replace those services; no real brokerage account or financial credentials were used.

## How the components fit together

`main.tsx` mounts React and the three providers: routing, server-data caching, and the current session. `App.tsx` chooses the page for the current URL. `AppLayout.tsx` surrounds every page with the sidebar, header, demo indicator, and footer.

A page asks a service in `api/services.ts` for data. That service calls `api/client.ts`, which adds the base URL, timeout, cancellation, JSON headers, and current bearer token. FastAPI responds with its own calculated values. TanStack Query stores the response and tracks pending/error/success. The page passes data into reusable components as **props**; those components render it.

```text
User action or page load
  -> React Query query/mutation
  -> API service
  -> centralized HTTP client
  -> FastAPI and its providers
  -> typed response
  -> page state
  -> reusable display components
```

Form values stay in their page because they only affect that form. Session state lives in `SessionProvider` because navigation and multiple pages need it. Server results live in TanStack Query because multiple screens use the same portfolio/analysis data; this avoids unnecessary duplicate requests and gives private-data cache cleanup a single home. Read requests use a two-minute freshness window and do not refetch merely because the browser regains focus. Screens and AI requests run only on explicit actions.

## File map

All paths below are relative to `C:\Users\kla89\Documents\AI-investment-app\frontend`.

| File                                         | Purpose                                                                                      |
| -------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `package.json`                               | Dependencies and development, build, test, and formatting commands.                          |
| `package-lock.json`                          | Exact dependency versions for repeatable installs.                                           |
| `index.html`                                 | Browser document, page metadata, and React mounting point.                                   |
| `vite.config.ts`                             | React/Tailwind build plugins, port 3000, and a separate chart bundle.                        |
| `tsconfig.json`                              | Strict TypeScript checks and JSX/module settings.                                            |
| `.env.example`                               | Public backend URL configuration example.                                                    |
| `.gitignore`                                 | Excludes dependencies, build output, local environment settings, and test artifacts.         |
| `.prettierrc.json`                           | Consistent source formatting.                                                                |
| `Start-Frontend.ps1`                         | Windows launcher and optional `-Build` command.                                              |
| `README.md`                                  | This startup, architecture, validation, and limitations guide.                               |
| `public/favicon.svg`                         | Small Aether tab icon.                                                                       |
| `public/_redirects`                          | Single-page-app route fallback for Netlify/Cloudflare Pages.                                 |
| `vercel.json`                                | Single-page-app route fallback for Vercel.                                                   |
| `src/vite-env.d.ts`                          | Type declarations for Vite environment variables.                                            |
| `src/main.tsx`                               | Starts React and its shared providers.                                                       |
| `src/App.tsx`                                | URL routes, lazy page imports, and page reset when account/data mode changes.                |
| `src/context/Session.tsx`                    | In-memory login state, live/demo mode, and recent session research.                          |
| `src/types/api.ts`                           | TypeScript response shapes derived from backend schemas/routes.                              |
| `src/api/client.ts`                          | Shared Fetch client, readable errors, cancellation, timeout, and authorization.              |
| `src/api/services.ts`                        | Named methods for actual backend endpoints and key compatibility checks.                     |
| `src/data/demo.json`                         | Stored sample holdings, scores, and criterion results from backend code.                     |
| `src/data/demo.ts`                           | Isolates demo data and labeled offline fallback from live services.                          |
| `src/utils/format.ts`                        | Consistent currency, percentage, number, date, ticker, and criteria handling.                |
| `src/styles/index.css`                       | Tailwind import, design tokens, theme, layouts, responsive rules, and motion preferences.    |
| `src/components/layout/AppLayout.tsx`        | Shared sidebar, accessible mobile drawer, header, search, and server status.                 |
| `src/components/common/UI.tsx`               | Page headers, panels, badges, loading/errors/empty states, account gate, and error boundary. |
| `src/components/common/IntelligenceCore.tsx` | Decorative SVG rings inspired by the theme reference.                                        |
| `src/components/common/StockSearch.tsx`      | Ticker validation and navigation to the common stock detail route.                           |
| `src/components/common/PortfolioViews.tsx`   | Reusable holdings table, allocation donut, and sector bars.                                  |
| `src/components/common/ScoreViews.tsx`       | Score gauge, category weights, and financial metric cards.                                   |
| `src/components/common/ScreenResults.tsx`    | Shared criteria summary, sorting, and matched/rejected/unavailable results.                  |
| `src/components/common/ConnectPortfolio.tsx` | Plaid Link preparation, user-controlled launch, token exchange, exit/error handling.         |
| `src/pages/DashboardPage.tsx`                | Main portfolio/research overview.                                                            |
| `src/pages/StockAnalysisPage.tsx`            | Common equity detail page used by all ticker links.                                          |
| `src/pages/ScreenerPage.tsx`                 | Criteria form, universe choice, results, and saving applied criteria.                        |
| `src/pages/AISearchPage.tsx`                 | Natural-language form and transparent query-to-results flow.                                 |
| `src/pages/PortfolioPage.tsx`                | Portfolio overview and holdings routes using the same source data.                           |
| `src/pages/LibraryPages.tsx`                 | Watchlist, saved-screen, and research-history pages.                                         |
| `src/pages/LoginPage.tsx`                    | Sign-in and registration forms.                                                              |
| `src/pages/SettingsPage.tsx`                 | Session, mode, connection management, connectivity, and methodology.                         |
| `src/pages/NotFoundPage.tsx`                 | Helpful fallback for unrecognized URLs.                                                      |
| `vitest.config.ts`                           | Unit test runner configuration.                                                              |
| `src/api/client.test.ts`                     | Verifies HTTP errors, JSON, authorization, cancellation, and expiry handling.                |
| `src/api/services.test.ts`                   | Verifies older backend contracts produce actionable errors.                                  |
| `src/utils/format.test.ts`                   | Verifies missing versus zero values and valid screen/ticker inputs.                          |
| `playwright.config.ts`                       | Desktop/mobile browser test configuration.                                                   |
| `tests/workspace.spec.ts`                    | End-to-end navigation and interaction tests with isolated API/Plaid fixtures.                |

## Validation commands

```powershell
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

Alternatively, to use installed Google Chrome for browser tests:

```powershell
$env:PLAYWRIGHT_CHANNEL = 'chrome'
npm run test:e2e
```

The browser suite checks desktop and mobile behavior, demo fallback, genuine-zero versus missing metrics, stable deterministic results after AI errors, optional screen criteria, sorting, interpreted AI criteria, watchlist CRUD, saved criteria, account history, sign-out, registration, Plaid public-token exchange, rate-limit recovery, deep links, and keyboard dismissal of the mobile menu. Browser API responses are controlled fixtures so the suite never creates real accounts or brokerage connections.

For manual verification: open the dashboard; visit AAPL from Holdings; run the sample screener and expand the rejected MSFT result; try the guided AI search; resize to a phone-sized window and open the menu. Switch to live research after restarting/configuring the backend, then sign in to test private data.

## Build and deploy

`npm run build` type-checks the application and produces `dist/`. Configure `VITE_API_BASE_URL` for your production backend before building. Configure that backend’s CORS with the final website origin. No site has been published by this task.

Deployment services can use `frontend` as the root directory, `npm run build` as the build command, and `dist` as the output directory. Deep links require a fallback to `index.html`; configurations for common static hosts are included.

Implementation references: [Vite setup](https://vite.dev/guide/), [Tailwind’s Vite plugin](https://tailwindcss.com/docs/installation/using-vite), [React Router](https://reactrouter.com/start/declarative/installation), [TanStack Query](https://tanstack.com/query/latest/docs/framework/react/overview), and [Plaid Link](https://plaid.com/docs/link/web/).
