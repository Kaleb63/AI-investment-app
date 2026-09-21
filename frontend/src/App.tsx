import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router';
import AppLayout from './components/layout/AppLayout';
import { Loading } from './components/common/UI';
import { useSession } from './context/Session';
const Dashboard = lazy(() => import('./pages/DashboardPage'));
const StockAnalysis = lazy(() => import('./pages/StockAnalysisPage'));
const Screener = lazy(() => import('./pages/ScreenerPage'));
const AISearch = lazy(() => import('./pages/AISearchPage'));
const Portfolio = lazy(() => import('./pages/PortfolioPage'));
const Watchlist = lazy(() =>
  import('./pages/LibraryPages').then((module) => ({ default: module.WatchlistPage })),
);
const SavedScreens = lazy(() =>
  import('./pages/LibraryPages').then((module) => ({ default: module.SavedScreensPage })),
);
const History = lazy(() =>
  import('./pages/LibraryPages').then((module) => ({ default: module.HistoryPage })),
);
const Settings = lazy(() => import('./pages/SettingsPage'));
const Login = lazy(() => import('./pages/LoginPage'));
const NotFound = lazy(() => import('./pages/NotFoundPage'));
export default function App() {
  const { demo, user } = useSession();
  return (
    <Suspense fallback={<Loading text="Opening workspace…" />}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Dashboard key={`${demo}-${user?.id}`} />} />
          <Route path="stocks" element={<StockAnalysis key={`${demo}-${user?.id}`} />} />
          <Route path="stocks/:ticker" element={<StockAnalysis key={`${demo}-${user?.id}`} />} />
          <Route path="screener" element={<Screener key={`${demo}-${user?.id}`} />} />
          <Route path="ai-search" element={<AISearch key={`${demo}-${user?.id}`} />} />
          <Route path="portfolio" element={<Portfolio key={`${demo}-${user?.id}`} />} />
          <Route path="holdings" element={<Portfolio key={`${demo}-${user?.id}`} />} />
          <Route path="watchlist" element={<Watchlist key={`${demo}-${user?.id}`} />} />
          <Route path="saved-screens" element={<SavedScreens key={`${demo}-${user?.id}`} />} />
          <Route path="history" element={<History key={`${demo}-${user?.id}`} />} />
          <Route path="settings" element={<Settings key={`${demo}-${user?.id}`} />} />
          <Route path="login" element={<Login />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
