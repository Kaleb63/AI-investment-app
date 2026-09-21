import { useState, type FormEvent } from 'react';
import { useMutation } from '@tanstack/react-query';
import { ArrowRight, Sparkles } from 'lucide-react';
import { api } from '../api/services';
import { useSession } from '../context/Session';
import { demoScreen } from '../data/demo';
import { parseTickers } from '../utils/format';
import { Badge, ErrorState, Loading, PageHeader, Panel } from '../components/common/UI';
import { CriteriaSummary, ScreenResults } from '../components/common/ScreenResults';
const sampleQuery =
  'Find profitable companies with a score of at least 70, a P/E no higher than 30, and a profit margin of at least 20%.';
export default function AISearchPage() {
  const { demo, setDemo } = useSession();
  const [query, setQuery] = useState('');
  const [tickers, setTickers] = useState('');
  const [limit, setLimit] = useState(100);
  const [showSample, setShowSample] = useState(false);
  const [inputError, setInputError] = useState('');
  const run = useMutation({
    mutationFn: () =>
      api.aiScreen(query.trim(), tickers.trim() ? parseTickers(tickers) : undefined, limit),
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    setInputError('');
    if (demo) {
      setShowSample(true);
      return;
    }
    try {
      if (tickers.trim()) parseTickers(tickers);
      if (query.trim().length < 3)
        throw new Error('Describe your criteria in at least 3 characters.');
      run.mutate();
    } catch (error) {
      setInputError((error as Error).message);
    }
  }
  return (
    <>
      <PageHeader
        eyebrow="RESEARCH / AI-ASSISTED DISCOVERY"
        title="Start with a question."
        description="Turn an investment research idea into clear, testable financial criteria."
      />
      <div className="ai-search-hero">
        <span className="ai-search-icon">
          <Sparkles size={27} />
        </span>
        <h2>What are you looking for?</h2>
        <p>Describe the kinds of companies you want to explore.</p>
        <form onSubmit={submit}>
          <label className="sr-only" htmlFor="ai-query">
            Describe your investment criteria
          </label>
          <textarea
            id="ai-query"
            value={demo ? sampleQuery : query}
            readOnly={demo}
            onChange={(event) => setQuery(event.target.value)}
            minLength={3}
            maxLength={1000}
            placeholder="Find profitable companies with strong growth, reasonable valuations, and healthy balance sheets…"
            required
          />
          <div className="ai-search-bottom">
            <span className="muted small">
              {demo ? 'Guided example · simulated data' : `${query.length}/1,000 characters`}
            </span>
            <button className="button primary" disabled={run.isPending}>
              <Sparkles size={16} />
              {run.isPending
                ? 'Interpreting and screening…'
                : demo
                  ? 'Explore sample search'
                  : 'Search companies'}
              <ArrowRight size={16} />
            </button>
          </div>
          {!demo && (
            <details className="search-options">
              <summary>Choose the search universe</summary>
              <div className="two-column">
                <label className="field">
                  Custom tickers (optional)
                  <input
                    value={tickers}
                    onChange={(event) => setTickers(event.target.value)}
                    placeholder="AAPL, MSFT, NVDA"
                  />
                </label>
                <label className="field">
                  Universe limit when tickers are blank
                  <input
                    type="number"
                    min={1}
                    max={1000}
                    value={limit}
                    onChange={(event) => setLimit(Number(event.target.value))}
                  />
                </label>
              </div>
            </details>
          )}
        </form>
        {demo && (
          <button className="text-button mt-4" onClick={() => setDemo(false)}>
            Switch to live research to write your own query <ArrowRight size={14} />
          </button>
        )}
      </div>
      <div className="ai-flow">
        {[
          'Your request',
          'AI interpretation',
          'Structured criteria',
          'Deterministic screen',
          'Results',
        ].map((step, i) => (
          <div key={step}>
            <span>{String(i + 1).padStart(2, '0')}</span>
            {step}
            {i < 4 && <ArrowRight size={14} />}
          </div>
        ))}
      </div>
      <p className="data-note">
        AI translates your request. Financial rules evaluate the companies. You can inspect the
        criteria and every result.
      </p>
      {inputError && <ErrorState error={new Error(inputError)} />}
      {run.isPending && <Loading text="Interpreting your request and evaluating companies…" />}
      {run.isError && <ErrorState error={run.error} retry={() => run.mutate()} />}
      {(demo && showSample) || (!demo && run.data) ? (
        <>
          <Panel
            title={demo ? 'Example interpretation' : 'We interpreted your search as'}
            subtitle={
              demo
                ? 'A stored demonstration of the request-to-criteria flow; no AI request was made.'
                : run.data!.query
            }
            className="mt-6"
          >
            <div className="pad">
              <CriteriaSummary
                criteria={demo ? demoScreen.criteria : run.data!.interpreted_criteria}
              />
              <Badge>{demo ? 'Simulated example' : 'Backend-interpreted criteria'}</Badge>
            </div>
          </Panel>
          {!demo && Object.keys(run.data!.explanation_errors).length > 0 && (
            <div className="notice">
              Some AI explanations were unavailable. The deterministic results are still shown.
            </div>
          )}
          <ScreenResults result={demo ? demoScreen : run.data!.results} />
        </>
      ) : null}
    </>
  );
}
