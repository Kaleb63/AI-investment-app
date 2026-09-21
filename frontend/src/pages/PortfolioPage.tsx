import { useMutation, useQuery } from '@tanstack/react-query';
import { Link, useLocation } from 'react-router';
import { Sparkles } from 'lucide-react';
import { api } from '../api/services';
import { getPortfolio } from '../data/demo';
import { useSession } from '../context/Session';
import { currency, number, percent } from '../utils/format';
import { Allocation, HoldingsTable } from '../components/common/PortfolioViews';
import { ConnectPortfolio } from '../components/common/ConnectPortfolio';
import { Badge, Empty, ErrorState, Loading, PageHeader, Panel } from '../components/common/UI';
export default function PortfolioPage() {
  const { demo, setDemo, user } = useSession();
  const holdingsOnly = useLocation().pathname === '/holdings';
  const result = useQuery({
    queryKey: ['portfolio', demo, user?.id],
    queryFn: ({ signal }) => getPortfolio(demo, signal),
    enabled: demo || Boolean(user),
  });
  const insights = useMutation({ mutationFn: () => api.portfolio(demo, true) });
  const portfolio = result.data?.portfolio;
  return (
    <>
      <PageHeader
        eyebrow="PORTFOLIO INTELLIGENCE"
        title={holdingsOnly ? 'Every position. One perspective.' : 'See the bigger picture.'}
        description={
          holdingsOnly
            ? 'Your positions, allocations, and equity scores in one place.'
            : 'Understand how your assets fit together, and where your exposure is concentrated.'
        }
        actions={
          demo ? (
            <Badge>Demo portfolio · simulated data</Badge>
          ) : user ? (
            <ConnectPortfolio />
          ) : undefined
        }
      />
      {!demo && !user ? (
        <Panel>
          <Empty
            title="Bring your portfolio into focus"
            text="Sign in to connect an investment account securely through Plaid, or explore a simulated portfolio."
            action={
              <div className="flex gap-3">
                <Link className="button primary" to="/login">
                  Sign in to connect
                </Link>
                <button className="button secondary" onClick={() => setDemo(true)}>
                  Try demo portfolio
                </button>
              </div>
            }
          />
        </Panel>
      ) : result.isPending ? (
        <Loading text="Retrieving holdings and portfolio analysis…" />
      ) : result.isError ? (
        <>
          <ErrorState error={result.error} retry={() => result.refetch()} />
          {user && (
            <p className="notice">
              If you have not connected an account, use “Connect investment account” above to get
              started.
            </p>
          )}
        </>
      ) : portfolio ? (
        <>
          {!holdingsOnly && (
            <>
              <div className="stat-grid">
                <div className="stat-card">
                  <span>Portfolio value</span>
                  <strong>{currency(portfolio.total_value)}</strong>
                  <small>{demo ? 'Simulated holdings' : 'Connected holdings'}</small>
                </div>
                <div className="stat-card">
                  <span>Positions</span>
                  <strong>{portfolio.position_count}</strong>
                  <small>Total assets in portfolio</small>
                </div>
                <div className="stat-card">
                  <span>Top 3 concentration</span>
                  <strong>{percent(portfolio.top_3_concentration)}</strong>
                  <small>Share of total portfolio</small>
                </div>
                <div className="stat-card">
                  <span>Effective positions</span>
                  <strong>{number(portfolio.effective_position_count, 2)}</strong>
                  <small>Backend concentration measure</small>
                </div>
              </div>
              <div className="two-column mt-6">
                <Panel title="Asset allocation" subtitle="By type of investment">
                  <Allocation portfolio={portfolio} />
                </Panel>
                <Panel title="Sector exposure" subtitle="Equity allocation across sectors">
                  <Allocation portfolio={portfolio} sectors />
                </Panel>
              </div>
            </>
          )}
          <Panel
            title="Portfolio holdings"
            subtitle={`${portfolio.position_count} positions · all values in USD`}
            className="mt-6"
          >
            <HoldingsTable holdings={portfolio.holdings} />
          </Panel>
          {!holdingsOnly && (
            <>
              <Panel
                title="Concentration details"
                subtitle="Calculated from the portfolio by the backend"
                className="mt-6"
              >
                <div className="metrics-grid">
                  <div className="metric">
                    <span>Largest position</span>
                    <strong>{percent(portfolio.largest_position?.weight)}</strong>
                    <small>
                      {portfolio.largest_position?.ticker ||
                        portfolio.largest_position?.name ||
                        'N/A'}
                    </small>
                  </div>
                  <div className="metric">
                    <span>Top 5 concentration</span>
                    <strong>{percent(portfolio.top_5_concentration)}</strong>
                  </div>
                  <div className="metric">
                    <span>Concentration index (HHI)</span>
                    <strong>{number(portfolio.concentration_hhi, 2)}</strong>
                  </div>
                </div>
              </Panel>
              <Panel
                title="Portfolio insights"
                subtitle="AI interpretation of your backend-calculated portfolio data"
                actions={<Sparkles size={18} className="accent" />}
                className="mt-6"
              >
                {insights.isPending ? (
                  <Loading text="Generating portfolio insights…" />
                ) : insights.isError ? (
                  <ErrorState error={insights.error} retry={() => insights.mutate()} />
                ) : insights.isSuccess ? (
                  insights.data.ai_explanation ? (
                    <div className="ai-copy">
                      <Badge>AI-generated interpretation</Badge>
                      <p className="preserve-lines">{insights.data.ai_explanation}</p>
                    </div>
                  ) : (
                    <div className="notice">
                      The portfolio analysis is available, but the AI explanation could not be
                      generated.{' '}
                      <button className="text-button" onClick={() => insights.mutate()}>
                        Try again
                      </button>
                    </div>
                  )
                ) : (
                  <div className="pad">
                    <p className="muted mb-4">
                      Explore concentration and diversification in plain language. This request
                      requires an available analysis server and AI provider.
                    </p>
                    <button className="button secondary" onClick={() => insights.mutate()}>
                      <Sparkles size={16} />
                      Generate portfolio insights
                    </button>
                  </div>
                )}
              </Panel>
            </>
          )}
          {result.data?.source === 'bundled-demo' && (
            <p className="data-note">
              Offline demo snapshot · backend-generated sample calculations, not current market
              data.
            </p>
          )}
        </>
      ) : null}
    </>
  );
}
