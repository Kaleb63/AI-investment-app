import { Link } from 'react-router';
import {
  ArrowRight,
  ArrowUpRight,
  Layers3,
  Radar,
  ScanLine,
  ShieldCheck,
  Sparkles,
  Wallet,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useSession } from '../context/Session';
import { getPortfolio } from '../data/demo';
import { currency, number, percent } from '../utils/format';
import { Allocation, HoldingsTable } from '../components/common/PortfolioViews';
import { IntelligenceCore } from '../components/common/IntelligenceCore';
import { Badge, Empty, ErrorState, Loading, PageHeader, Panel } from '../components/common/UI';

export default function DashboardPage() {
  const { demo, user, recent } = useSession();
  const result = useQuery({
    queryKey: ['portfolio', demo, user?.id],
    queryFn: ({ signal }) => getPortfolio(demo, signal),
    enabled: demo || Boolean(user),
  });
  const portfolio = result.data?.portfolio;
  return (
    <>
      <PageHeader
        eyebrow="YOUR RESEARCH COMMAND CENTER"
        title="A clearer view of your investments."
        description="Financial fundamentals. Transparent scoring. Intelligence you can explore."
        actions={
          <Link to="/stocks" className="button secondary">
            <ScanLine size={16} /> Research a stock <ArrowUpRight size={15} />
          </Link>
        }
      />
      <section className="hero-panel">
        <div className="hero-copy">
          <span className="hero-kicker">
            <span className="status-dot" /> RESEARCH WITH PERSPECTIVE
          </span>
          <h2>
            More signal.
            <br />
            <span>Less uncertainty.</span>
          </h2>
          <p>
            Look beneath the price. Connect company fundamentals, rule-based scores, and AI-assisted
            explanations in one research workspace.
          </p>
          <div className="hero-actions">
            <Link className="button primary" to="/ai-search">
              <Sparkles size={16} /> Explore with AI <ArrowRight size={16} />
            </Link>
            <Link className="text-link" to="/screener">
              Open screener <ArrowUpRight size={15} />
            </Link>
          </div>
          <div className="hero-bottom">
            <span>
              <ShieldCheck size={13} /> Transparent methodology
            </span>
            <span>
              <Layers3 size={13} /> Fundamentals first
            </span>
          </div>
        </div>
        <div className="hero-visual">
          <span className="hud-top">INTELLIGENCE / CORE 01</span>
          <IntelligenceCore />
          <div className="hud-bottom">
            <i /> MARKET DATA <span>×</span> FINANCIAL REASONING
          </div>
        </div>
      </section>
      <div className="section-title">
        <h2>Portfolio at a glance</h2>
        <div>
          {demo && <Badge>Simulated data</Badge>}
          <Link className="text-link" to="/portfolio">
            View portfolio <ArrowUpRight size={15} />
          </Link>
        </div>
      </div>
      {result.isPending && (demo || user) ? (
        <Loading text="Loading your portfolio overview…" />
      ) : result.isError ? (
        <ErrorState error={result.error} retry={() => result.refetch()} />
      ) : portfolio ? (
        <>
          <div className="stat-grid">
            <div className="stat-card">
              <span>
                Total portfolio value <Wallet size={16} />
              </span>
              <strong>{currency(portfolio.total_value)}</strong>
              <small>{demo ? 'Demo portfolio · USD' : 'Connected portfolio · USD'}</small>
            </div>
            <div className="stat-card">
              <span>
                Portfolio positions <Layers3 size={16} />
              </span>
              <strong>
                {number(portfolio.position_count, 0)}
                <em>assets</em>
              </strong>
              <small>Across your investment accounts</small>
            </div>
            <div className="stat-card">
              <span>
                Largest position <Radar size={16} />
              </span>
              <strong>{percent(portfolio.largest_position?.weight)}</strong>
              <small>
                {portfolio.largest_position?.ticker ||
                  portfolio.largest_position?.name ||
                  'No positions'}
              </small>
            </div>
            <div className="stat-card">
              <span>
                Top 3 concentration <ScanLine size={16} />
              </span>
              <strong>{percent(portfolio.top_3_concentration)}</strong>
              <small>Share of total portfolio value</small>
            </div>
          </div>
          <div className="dashboard-grid">
            <Panel
              title="Your holdings"
              subtitle="A closer look at what you own"
              actions={
                <Link to="/holdings" className="text-link">
                  View all <ArrowUpRight size={14} />
                </Link>
              }
            >
              <HoldingsTable holdings={portfolio.holdings.slice(0, 4)} compact />
            </Panel>
            <Panel title="Asset allocation" subtitle="How your portfolio is distributed">
              <Allocation portfolio={portfolio} />
            </Panel>
          </div>
          {result.data?.source === 'bundled-demo' && (
            <p className="data-note">
              Offline demo snapshot · Generated from the backend’s simulated holdings and scoring
              rules. Values are illustrative, not current market prices.
            </p>
          )}
        </>
      ) : (
        <Panel>
          <Empty
            title="Your portfolio starts here"
            text="Connect your investment account, or explore the workspace with a simulated portfolio."
            action={
              <Link className="button primary" to="/portfolio">
                Set up portfolio <ArrowRight size={16} />
              </Link>
            }
          />
        </Panel>
      )}
      <div className="section-title">
        <h2>Go deeper with your research</h2>
        <span className="muted small">A question is a good place to start.</span>
      </div>
      <div className="research-grid">
        {[
          {
            icon: ScanLine,
            title: 'Understand a company',
            text: 'Explore financial metrics, category scores, and the reasoning behind them.',
            to: '/stocks',
            action: 'Stock analysis',
          },
          {
            icon: Layers3,
            title: 'Find what fits your criteria',
            text: 'Filter equities with transparent, configurable financial requirements.',
            to: '/screener',
            action: 'Stock screener',
          },
          {
            icon: Sparkles,
            title: 'Start with an idea',
            text: 'Describe your research criteria in plain language. See how they translate.',
            to: '/ai-search',
            action: 'AI search',
          },
        ].map((item) => (
          <Link key={item.to} to={item.to} className="research-card">
            <span className="research-icon">
              <item.icon size={21} />
            </span>
            <h3>{item.title}</h3>
            <p>{item.text}</p>
            <span className="text-link">
              {item.action}
              <ArrowUpRight size={16} />
            </span>
          </Link>
        ))}
      </div>
      {recent.length > 0 && (
        <Panel title="Recently explored" subtitle="Research from this session" className="mt-6">
          <div className="recent-row">
            {recent.slice(0, 4).map((item) => (
              <Link to={`/stocks/${item.ticker}`} key={item.ticker}>
                <strong>{item.ticker}</strong>
                <Badge>{number(item.score.overall_score)} / 100</Badge>
                <ArrowUpRight size={15} />
              </Link>
            ))}
          </div>
        </Panel>
      )}
    </>
  );
}
