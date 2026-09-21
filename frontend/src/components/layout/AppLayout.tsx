import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router';
import {
  Activity,
  ArrowUpRight,
  Bookmark,
  ChevronDown,
  CircleHelp,
  Command,
  History,
  LayoutDashboard,
  ListFilter,
  Menu,
  Radar,
  Search,
  Settings2,
  Sparkles,
  Wallet,
  X,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useSession } from '../../context/Session';
import { StockSearch } from '../common/StockSearch';
import { api } from '../../api/services';

const groups = [
  { label: 'WORKSPACE', links: [{ to: '/', text: 'Dashboard', icon: LayoutDashboard }] },
  {
    label: 'RESEARCH',
    links: [
      { to: '/stocks', text: 'Stock analysis', icon: Search },
      { to: '/screener', text: 'Stock screener', icon: ListFilter },
      { to: '/ai-search', text: 'AI search', icon: Sparkles },
    ],
  },
  {
    label: 'YOUR PORTFOLIO',
    links: [
      { to: '/portfolio', text: 'Overview', icon: Wallet },
      { to: '/holdings', text: 'Holdings', icon: Activity },
    ],
  },
  {
    label: 'LIBRARY',
    links: [
      { to: '/watchlist', text: 'Watchlist', icon: Bookmark },
      { to: '/saved-screens', text: 'Saved screens', icon: ListFilter },
      { to: '/history', text: 'Research history', icon: History },
    ],
  },
];
function Navigation({ close }: { close: () => void }) {
  const { demo, user } = useSession();
  return (
    <>
      <Link to="/" className="brand" onClick={close}>
        <span className="brand-mark">
          <Radar size={29} />
        </span>
        <span>
          AETHER<small>INVESTMENT INTELLIGENCE</small>
        </span>
      </Link>
      <div className="workspace-label">
        <span className="workspace-icon">
          <Command size={17} />
        </span>
        <span>
          Research workspace<small>{demo ? 'Demo environment' : 'Live research'}</small>
        </span>
        <ChevronDown size={13} />
      </div>
      <nav aria-label="Main navigation">
        {groups.map((group) => (
          <div className="nav-group" key={group.label}>
            <p>{group.label}</p>
            {group.links.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                onClick={close}
                className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              >
                <item.icon size={18} />
                <span>{item.text}</span>
                {item.to === '/ai-search' && <span className="ai-mini">AI</span>}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <NavLink to="/settings" className="nav-link" onClick={close}>
          <Settings2 size={18} />
          Settings
        </NavLink>
        <Link to="/settings#about" className="nav-link" onClick={close}>
          <CircleHelp size={18} />
          About Aether
          <ArrowUpRight size={14} />
        </Link>
        <div className="profile">
          <span className="avatar">{user ? user.email[0].toUpperCase() : 'R'}</span>
          <div>
            {user ? 'Your workspace' : 'Research explorer'}
            <small>{user ? user.email : 'Discover with clarity'}</small>
          </div>
          <span className="status-dot" />
        </div>
      </div>
    </>
  );
}
export default function AppLayout() {
  const [open, setOpen] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);
  const { demo, setDemo, user } = useSession();
  const location = useLocation();
  const health = useQuery({
    queryKey: ['health'],
    queryFn: ({ signal }) => api.health(signal),
    staleTime: 60000,
    retry: false,
  });
  useEffect(() => {
    if (open) dialog.current?.showModal();
    else if (dialog.current?.open) dialog.current.close();
  }, [open]);
  useEffect(() => {
    setOpen(false);
    window.scrollTo(0, 0);
  }, [location.pathname]);
  const section =
    groups
      .flatMap((group) => group.links)
      .find(
        (item) =>
          item.to === location.pathname ||
          (item.to === '/stocks' && location.pathname.startsWith('/stocks/')),
      )?.text || (location.pathname === '/settings' ? 'Settings' : 'Account');
  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      <aside className="sidebar">
        <Navigation close={() => setOpen(false)} />
      </aside>
      <dialog
        ref={dialog}
        className="nav-dialog"
        onCancel={() => setOpen(false)}
        onClose={() => {
          setOpen(false);
          menuButton.current?.focus();
        }}
        onClick={(event) => {
          if (event.target === event.currentTarget) setOpen(false);
        }}
      >
        <div className="drawer">
          <button
            className="drawer-close icon-button"
            onClick={() => setOpen(false)}
            aria-label="Close navigation"
          >
            <X size={21} />
          </button>
          <Navigation close={() => setOpen(false)} />
        </div>
      </dialog>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              ref={menuButton}
              className="mobile-menu icon-button"
              aria-label="Open navigation"
              aria-expanded={open}
              onClick={() => setOpen(true)}
            >
              <Menu size={21} />
            </button>
            <span className="breadcrumb-parent">
              Workspace <span>/</span>
            </span>
            <strong>{section}</strong>
          </div>
          <div className="header-actions">
            <StockSearch />
            <button
              className={`mode-toggle ${demo ? 'is-demo' : ''}`}
              onClick={() => setDemo(!demo)}
              title="Switch between simulated data and live research"
            >
              <span className="status-dot" />
              {demo ? 'Demo mode' : 'Live research'}
            </button>
            {!user && (
              <Link className="signin-link" to="/login">
                Sign in <ArrowUpRight size={14} />
              </Link>
            )}
          </div>
        </header>
        {demo && (
          <div className="demo-banner">
            <span>
              <Sparkles size={13} /> Demo workspace <span className="banner-divider">/</span>{' '}
              <span>Simulated portfolio and sample research. No brokerage connection needed.</span>
            </span>
            <button onClick={() => setDemo(false)}>
              Go to live research <ArrowUpRight size={13} />
            </button>
          </div>
        )}
        <main id="main-content" className="page-content" tabIndex={-1}>
          <Outlet />
        </main>
        <footer className="app-footer">
          <span>
            <span
              className={`status-dot ${health.isError ? 'offline' : health.isPending ? 'pending' : ''}`}
            />
            {health.isPending
              ? 'Checking research server'
              : health.isError
                ? 'Research server unavailable'
                : 'Research server reachable'}
          </span>
          <span>
            Research with perspective. <span className="footer-detail">Not investment advice.</span>
          </span>
          <span className="mono">AETHER / 01</span>
        </footer>
      </div>
    </div>
  );
}
