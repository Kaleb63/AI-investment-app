import { useEffect } from 'react';
import { Link, useParams } from 'react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BookmarkPlus, Clock3, Sparkles } from 'lucide-react';
import { api } from '../api/services';
import { useSession } from '../context/Session';
import { demoPortfolio, getDemoAnalysis } from '../data/demo';
import { currency, date, label, number, percent, tickerPattern } from '../utils/format';
import { Badge, Empty, ErrorState, Loading, PageHeader, Panel } from '../components/common/UI';
import { StockSearch } from '../components/common/StockSearch';
import { MetricsGrid, ScorePanel } from '../components/common/ScoreViews';

export default function StockAnalysisPage() {
  const { ticker: routeTicker } = useParams();
  const ticker = (routeTicker || '').toUpperCase();
  const { demo, user, remember } = useSession();
  const queryClient = useQueryClient();
  const valid = tickerPattern.test(ticker);
  const analysis = useQuery({
    queryKey: ['analysis', demo, ticker],
    queryFn: ({ signal }) =>
      demo ? Promise.resolve(getDemoAnalysis(ticker)) : api.analysis(ticker, signal),
    enabled: valid,
  });
  const quote = useQuery({
    queryKey: ['quote', ticker],
    queryFn: ({ signal }) => api.quote(ticker, signal),
    enabled: valid && !demo,
  });
  const history = useQuery({
    queryKey: ['historical', ticker],
    queryFn: ({ signal }) => api.historical(ticker, signal),
    enabled: false,
  });
  const explanation = useMutation({ mutationFn: () => api.explanation(ticker) });
  const watch = useMutation({
    mutationFn: () => api.addWatchlist(ticker),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['watchlist'] }),
  });
  useEffect(() => {
    if (analysis.data) remember(analysis.data);
  }, [analysis.data]);
  useEffect(() => {
    explanation.reset();
    watch.reset();
  }, [ticker]);
  const sample = demoPortfolio.holdings.find((item) => item.ticker === ticker);
  if (!ticker)
    return (
      <>
        <PageHeader
          eyebrow="EQUITY RESEARCH"
          title="Look beneath the ticker."
          description="Understand the fundamentals, the score, and the evidence behind a company."
        />
        <Panel>
          <div className="research-start">
            <StockSearch large />
            <p className="muted">
              {demo
                ? 'Explore a simulated equity analysis'
                : 'Enter a stock ticker to begin your research'}
            </p>
            <div className="flex gap-3 justify-center">
              <Link className="button secondary" to="/stocks/AAPL">
                AAPL <span className="muted">Apple</span>
              </Link>
              <Link className="button secondary" to="/stocks/MSFT">
                MSFT <span className="muted">Microsoft</span>
              </Link>
            </div>
          </div>
        </Panel>
      </>
    );
  return (
    <>
      <PageHeader
        eyebrow="EQUITY RESEARCH / STOCK ANALYSIS"
        title={ticker}
        description={
          demo && sample?.name
            ? sample.name
            : 'Company fundamentals and transparent financial scoring.'
        }
        actions={
          <>
            <StockSearch />
            {user && !demo && (
              <button
                className="button secondary"
                disabled={watch.isPending || watch.isSuccess}
                onClick={() => watch.mutate()}
              >
                <BookmarkPlus size={16} />
                {watch.isSuccess ? 'Added to watchlist' : 'Add to watchlist'}
              </button>
            )}
          </>
        }
      />
      {watch.isError && <ErrorState error={watch.error} />}
      {!valid ? (
        <ErrorState
          error={
            new Error('This ticker is not valid. Use letters, numbers, a period, or a hyphen.')
          }
        />
      ) : analysis.isPending ? (
        <Loading />
      ) : analysis.isError ? (
        <ErrorState error={analysis.error} retry={() => analysis.refetch()} />
      ) : (
        analysis.data && (
          <>
            <div className="quote-strip">
              <strong>{currency(demo ? sample?.price : quote.data?.price)}</strong>
              {!demo && quote.data?.quote.dp != null && (
                <span className={quote.data.quote.dp >= 0 ? 'positive' : 'negative'}>
                  {quote.data.quote.dp >= 0 ? '+' : ''}
                  {percent(quote.data.quote.dp)} today
                </span>
              )}
              <span className="muted small">
                {demo
                  ? 'Simulated price · not a live quote'
                  : quote.isError
                    ? 'Quote unavailable; financial analysis remains available'
                    : quote.isPending
                      ? 'Retrieving quote…'
                      : 'Latest available quote'}
              </span>
              {demo && <Badge>Simulated data</Badge>}
            </div>
            <ScorePanel analysis={analysis.data} />
            <Panel
              title="Financial metrics"
              subtitle="Missing values are shown as N/A"
              className="mt-6"
            >
              <MetricsGrid analysis={analysis.data} />
            </Panel>
            <div className="two-column mt-6">
              <Panel
                title="Why this score?"
                subtitle="Rule-based observations from the scoring model"
              >
                <ul className="reason-list">
                  {analysis.data.score.reasons.map((reason, index) => (
                    <li key={index}>
                      <span />
                      {reason}
                    </li>
                  ))}
                </ul>
                {Object.entries(analysis.data.metrics).some(
                  ([key, value]) => key !== 'ticker' && value == null,
                ) && (
                  <p className="notice">
                    Some metrics are unavailable. Data coverage shows how much of the scoring model
                    is supported.
                  </p>
                )}
              </Panel>
              <Panel
                title="AI interpretation"
                subtitle="A separate explanation of the financial evidence"
                actions={<Sparkles className="accent" size={19} />}
              >
                {demo ? (
                  <div className="ai-copy">
                    <Badge tone="muted">Illustrative commentary · not AI generated</Badge>
                    <p>
                      This sample combines strong profitability with an elevated P/E ratio. Review
                      the category scores and underlying metrics together; the overall score
                      summarizes a rule-based model.
                    </p>
                    <p className="muted small">
                      Switch to live research to request an AI-generated explanation from the
                      backend.
                    </p>
                  </div>
                ) : explanation.isPending ? (
                  <Loading text="Generating an explanation…" />
                ) : explanation.isError ? (
                  <>
                    <ErrorState error={explanation.error} retry={() => explanation.mutate()} />
                    <p className="muted small pad">
                      Your deterministic analysis remains available.
                    </p>
                  </>
                ) : explanation.data ? (
                  <div className="ai-copy">
                    <Badge>AI-generated interpretation</Badge>
                    <p className="preserve-lines">{explanation.data.ai_explanation}</p>
                  </div>
                ) : (
                  <Empty
                    title="Put the evidence in context"
                    text="Request an AI explanation based on the metrics and score shown here."
                    action={
                      <button className="button secondary" onClick={() => explanation.mutate()}>
                        <Sparkles size={16} />
                        Generate explanation
                      </button>
                    }
                  />
                )}
              </Panel>
            </div>
            <Panel
              title="Historical perspective"
              subtitle="Returns, volatility, and moving averages are separate from the fundamental score."
              className="mt-6"
              actions={<Clock3 size={18} className="muted" />}
            >
              {demo ? (
                <p className="pad muted">
                  The demo contains no historical price data. Switch to live research to load
                  historical statistics.
                </p>
              ) : history.isFetching ? (
                <Loading text="Retrieving historical statistics…" />
              ) : history.isError ? (
                <ErrorState error={history.error} retry={() => history.refetch()} />
              ) : history.data ? (
                <>
                  <div className="metrics-grid">
                    {Object.entries(history.data.returns).map(([key, value]) => (
                      <div className="metric" key={key}>
                        <span>{label(key)} return</span>
                        <strong>{percent(value)}</strong>
                      </div>
                    ))}
                    <div className="metric">
                      <span>Annualized volatility</span>
                      <strong>{percent(history.data.annualized_volatility)}</strong>
                    </div>
                    {Object.entries(history.data.moving_averages).map(([key, value]) => (
                      <div className="metric" key={key}>
                        <span>{label(key)}</span>
                        <strong>{currency(value)}</strong>
                      </div>
                    ))}
                  </div>
                  <p className="data-note pad">
                    {date(history.data.start_date)} – {date(history.data.end_date)} ·{' '}
                    {number(history.data.observations, 0)} observations
                  </p>
                </>
              ) : (
                <div className="pad">
                  <button className="button secondary" onClick={() => history.refetch()}>
                    Load historical statistics
                  </button>
                </div>
              )}
            </Panel>
          </>
        )
      )}
    </>
  );
}
