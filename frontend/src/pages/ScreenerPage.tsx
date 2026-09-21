import { useState, type FormEvent } from 'react';
import { Link, useLocation } from 'react-router';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { BookmarkPlus, Play, RotateCcw } from 'lucide-react';
import { api } from '../api/services';
import { useSession } from '../context/Session';
import { demoScreen } from '../data/demo';
import { criteriaFields, parseCriteria, parseTickers } from '../utils/format';
import { Badge, Empty, ErrorState, Loading, PageHeader, Panel } from '../components/common/UI';
import { CriteriaSummary, ScreenResults } from '../components/common/ScreenResults';
import type { Criteria } from '../types/api';

export default function ScreenerPage() {
  const { demo, setDemo, user } = useSession();
  const location = useLocation();
  const queryClient = useQueryClient();
  const savedCriteria = (location.state as { criteria?: Criteria } | null)?.criteria;
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      Object.entries(savedCriteria || {})
        .filter(([, value]) => value != null)
        .map(([key, value]) => [key, String(value)]),
    ),
  );
  const [scope, setScope] = useState('custom');
  const [tickers, setTickers] = useState('AAPL, MSFT, NVDA, GOOGL');
  const [limit, setLimit] = useState(100);
  const [inputError, setInputError] = useState('');
  const [showDemo, setShowDemo] = useState(false);
  const [name, setName] = useState('');
  const run = useMutation({
    mutationFn: async () => {
      const criteria = parseCriteria(values);
      const selected =
        scope === 'custom'
          ? parseTickers(tickers)
          : (await api.universe(limit)).symbols.map((item) => item.ticker);
      if (!selected.length) throw new Error('No stocks are available in the selected universe.');
      return api.screen(selected, criteria);
    },
  });
  const save = useMutation({
    mutationFn: () => api.saveScreen(name.trim(), run.data?.criteria || parseCriteria(values)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-screens'] });
      setName('');
    },
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    setInputError('');
    save.reset();
    if (demo) {
      setShowDemo(true);
      return;
    }
    try {
      parseCriteria(values);
      if (scope === 'custom') parseTickers(tickers);
      run.mutate();
    } catch (error) {
      setInputError((error as Error).message);
    }
  }
  return (
    <>
      <PageHeader
        eyebrow="RESEARCH / DETERMINISTIC SCREENING"
        title="Find companies that fit your criteria."
        description="Set the requirements. Let the financial evidence do the filtering."
        actions={demo ? <Badge>Sample screen</Badge> : undefined}
      />
      {demo && (
        <div className="notice flex-notice">
          <span>The demo runs a stored screen of AAPL and MSFT using the criteria below.</span>
          <button className="text-button" onClick={() => setDemo(false)}>
            Customize in live research
          </button>
        </div>
      )}
      <form onSubmit={submit}>
        <Panel
          title="Screening criteria"
          subtitle="Leave any criterion blank to keep it unset."
          actions={
            !demo && (
              <button type="button" className="text-button" onClick={() => setValues({})}>
                <RotateCcw size={14} />
                Reset
              </button>
            )
          }
        >
          <div className="criteria-form">
            {criteriaFields.map((field) => (
              <label className="field" key={field[0]}>
                {field[1]}
                <div className="input-unit">
                  <input
                    type="number"
                    step="any"
                    min={field[3]}
                    max={field.length > 4 ? field[4] : undefined}
                    disabled={demo}
                    value={demo ? (demoScreen.criteria[field[0]] ?? '') : values[field[0]] || ''}
                    onChange={(event) =>
                      setValues((previous) => ({ ...previous, [field[0]]: event.target.value }))
                    }
                    placeholder="No minimum / maximum"
                  />
                  <span>{field[2]}</span>
                </div>
              </label>
            ))}
          </div>
          <div className="screen-scope">
            <div className="scope-controls">
              <label className="field">
                Stock universe
                <select
                  value={demo ? 'custom' : scope}
                  onChange={(event) => setScope(event.target.value)}
                  disabled={demo}
                >
                  <option value="custom">Custom tickers</option>
                  <option value="universe">U.S. equities · bounded sample</option>
                </select>
              </label>
              {scope === 'custom' || demo ? (
                <label className="field grow">
                  Tickers
                  <input
                    value={demo ? 'AAPL, MSFT' : tickers}
                    disabled={demo}
                    onChange={(event) => setTickers(event.target.value)}
                    placeholder="AAPL, MSFT, NVDA"
                    required
                  />
                </label>
              ) : (
                <label className="field">
                  Maximum stocks
                  <input
                    type="number"
                    min={1}
                    max={1000}
                    value={limit}
                    onChange={(event) => setLimit(Number(event.target.value))}
                    required
                  />
                  <small>
                    First {limit} symbols, sorted by the provider. Larger scans take longer.
                  </small>
                </label>
              )}
            </div>
            <button className="button primary" disabled={run.isPending} type="submit">
              <Play size={15} />
              {run.isPending ? 'Analyzing market…' : demo ? 'View sample results' : 'Run screen'}
            </button>
          </div>
        </Panel>
      </form>
      {inputError && <ErrorState error={new Error(inputError)} />}
      {run.isPending && (
        <Loading text="Analyzing market… Individual provider responses may take time." />
      )}
      {run.isError && <ErrorState error={run.error} retry={() => run.mutate()} />}
      {(demo && showDemo) || (!demo && run.data) ? (
        <>
          <div className="section-title">
            <h2>Applied criteria</h2>
            {demo && <Badge>Simulated data</Badge>}
          </div>
          <CriteriaSummary criteria={demo ? demoScreen.criteria : run.data!.criteria} />
          <ScreenResults result={demo ? demoScreen : run.data!} />
          {!demo && user && (
            <Panel
              className="mt-6"
              title="Save this screen"
              subtitle="Keep the applied criteria for your next research session."
            >
              <form
                className="inline-form pad"
                onSubmit={(event) => {
                  event.preventDefault();
                  save.mutate();
                }}
              >
                <label className="sr-only" htmlFor="screen-name">
                  Screen name
                </label>
                <input
                  id="screen-name"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  maxLength={120}
                  placeholder="Name your screen"
                  required
                />
                <button className="button secondary" disabled={!name.trim() || save.isPending}>
                  <BookmarkPlus size={16} />
                  Save criteria
                </button>
              </form>
              {save.isError && <ErrorState error={save.error} />}
              {save.isSuccess && (
                <p className="notice">
                  Screen saved.{' '}
                  <Link to="/saved-screens" className="text-link">
                    View saved screens
                  </Link>
                </p>
              )}
            </Panel>
          )}
        </>
      ) : (
        !run.isPending &&
        !run.isError && (
          <Panel className="mt-6">
            <Empty
              title="Your next discovery starts with a screen"
              text="Choose your criteria and run a screen. Matches, rejected stocks, and unavailable data will be shown separately."
            />
          </Panel>
        )
      )}
    </>
  );
}
