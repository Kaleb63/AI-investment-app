import { useState } from 'react';
import { Link } from 'react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowUpRight, Play, Plus, Trash2 } from 'lucide-react';
import { api } from '../api/services';
import { useSession } from '../context/Session';
import { date, number, parseTickers } from '../utils/format';
import {
  Badge,
  Empty,
  ErrorState,
  Loading,
  PageHeader,
  Panel,
  SignInRequired,
} from '../components/common/UI';
import { CriteriaSummary, ScreenResults } from '../components/common/ScreenResults';

export function WatchlistPage() {
  const { user, demo } = useSession();
  const queryClient = useQueryClient();
  const [ticker, setTicker] = useState('');
  const list = useQuery({
    queryKey: ['watchlist', user?.id],
    queryFn: ({ signal }) => api.watchlist(signal),
    enabled: Boolean(user) && !demo,
  });
  const analyze = useMutation({ mutationFn: api.analyzeWatchlist });
  function refresh() {
    queryClient.invalidateQueries({ queryKey: ['watchlist'] });
    analyze.reset();
  }
  const add = useMutation({
    mutationFn: () => {
      const symbols = parseTickers(ticker);
      if (symbols.length !== 1) throw new Error('Add one ticker at a time.');
      return api.addWatchlist(symbols[0]);
    },
    onSuccess: () => {
      setTicker('');
      refresh();
    },
  });
  const remove = useMutation({ mutationFn: api.removeWatchlist, onSuccess: refresh });
  return (
    <>
      <PageHeader
        eyebrow="LIBRARY / WATCHLIST"
        title="Keep interesting companies in view."
        description="Save tickers to your account and revisit their fundamentals as your research develops."
      />
      {!user || demo ? (
        <SignInRequired feature="watchlist" />
      ) : (
        <>
          <Panel
            title="Your watchlist"
            actions={
              <button
                className="button secondary"
                disabled={!list.data?.length || analyze.isPending}
                onClick={() => analyze.mutate()}
              >
                <Play size={14} />
                Analyze watchlist
              </button>
            }
          >
            <form
              className="inline-form pad"
              onSubmit={(event) => {
                event.preventDefault();
                add.mutate();
              }}
            >
              <label className="sr-only" htmlFor="watch-ticker">
                Ticker to add
              </label>
              <input
                id="watch-ticker"
                value={ticker}
                onChange={(event) => setTicker(event.target.value.toUpperCase())}
                placeholder="Add ticker, e.g. AAPL"
                maxLength={15}
                required
              />
              <button className="button primary" disabled={add.isPending || remove.isPending}>
                <Plus size={16} />
                {add.isPending ? 'Adding…' : 'Add ticker'}
              </button>
            </form>
            {add.isError && <ErrorState error={add.error} />}
            {remove.isError && <ErrorState error={remove.error} />}
            {list.isPending ? (
              <Loading text="Loading your watchlist…" />
            ) : list.isError ? (
              <ErrorState error={list.error} retry={() => list.refetch()} />
            ) : !list.data?.length ? (
              <Empty
                title="A watchlist worth watching"
                text="Add your first company above. The backend validates each ticker before saving it."
              />
            ) : (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Ticker</th>
                      <th>Added</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {list.data.map((item) => (
                      <tr key={item.id}>
                        <td>
                          <Link className="ticker-link" to={`/stocks/${item.ticker}`}>
                            {item.ticker}
                          </Link>
                        </td>
                        <td>{date(item.created_at)}</td>
                        <td>
                          <button
                            className="icon-button danger"
                            aria-label={`Remove ${item.ticker} from watchlist`}
                            onClick={() => remove.mutate(item.ticker)}
                            disabled={remove.isPending || add.isPending}
                          >
                            <Trash2 size={16} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
          {analyze.isPending && <Loading text="Analyzing watchlist companies…" />}
          {analyze.isError && <ErrorState error={analyze.error} retry={() => analyze.mutate()} />}
          {analyze.data && <ScreenResults result={analyze.data} />}
        </>
      )}
    </>
  );
}
export function SavedScreensPage() {
  const { user, demo } = useSession();
  const queryClient = useQueryClient();
  const list = useQuery({
    queryKey: ['saved-screens', user?.id],
    queryFn: ({ signal }) => api.savedScreens(signal),
    enabled: Boolean(user) && !demo,
  });
  const remove = useMutation({
    mutationFn: api.deleteScreen,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['saved-screens'] }),
  });
  return (
    <>
      <PageHeader
        eyebrow="LIBRARY / SAVED SCREENS"
        title="Good criteria are worth keeping."
        description="Your saved financial requirements, ready for another look at the market."
        actions={
          <Link className="button secondary" to="/screener">
            <Plus size={16} />
            Create screen
          </Link>
        }
      />
      {!user || demo ? (
        <SignInRequired feature="saved screens" />
      ) : list.isPending ? (
        <Loading text="Loading saved screens…" />
      ) : list.isError ? (
        <ErrorState error={list.error} retry={() => list.refetch()} />
      ) : (
        <>
          {remove.isError && <ErrorState error={remove.error} />}
          {!list.data?.length ? (
            <Panel>
              <Empty
                title="No saved screens yet"
                text="Run a screen and save its criteria to revisit it here."
                action={
                  <Link className="button primary" to="/screener">
                    Open screener
                  </Link>
                }
              />
            </Panel>
          ) : (
            <div className="saved-grid">
              {list.data.map((item) => (
                <Panel title={item.name} subtitle={`Saved ${date(item.created_at)}`} key={item.id}>
                  <div className="pad">
                    <CriteriaSummary criteria={item.criteria} />
                    <div className="flex justify-between mt-4">
                      <Link
                        className="button secondary"
                        to="/screener"
                        state={{ criteria: item.criteria }}
                      >
                        Load criteria <ArrowUpRight size={15} />
                      </Link>
                      <button
                        className="icon-button danger"
                        disabled={remove.isPending}
                        onClick={() => remove.mutate(item.id)}
                        aria-label={`Delete ${item.name}`}
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                </Panel>
              ))}
            </div>
          )}
        </>
      )}
    </>
  );
}
export function HistoryPage() {
  const { user, demo, recent } = useSession();
  const history = useQuery({
    queryKey: ['history', user?.id],
    queryFn: ({ signal }) => api.history(signal),
    enabled: Boolean(user) && !demo,
  });
  return (
    <>
      <PageHeader
        eyebrow="LIBRARY / RESEARCH HISTORY"
        title="Pick up where you left off."
        description="Revisit recently explored companies and your account’s previous screens."
      />
      <Panel
        title="Recent stock analysis"
        subtitle="This browser session only; cleared when you change data mode or sign out."
      >
        {!recent.length ? (
          <Empty
            title="No analysis in this session"
            text="Research a company and it will appear here."
            action={
              <Link className="button secondary" to="/stocks">
                Research a stock
              </Link>
            }
          />
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Score</th>
                  <th>Signal</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((item) => (
                  <tr key={item.ticker}>
                    <td>
                      <Link to={`/stocks/${item.ticker}`} className="ticker-link">
                        {item.ticker}
                      </Link>
                    </td>
                    <td>{number(item.score.overall_score)}</td>
                    <td>
                      <Badge>{item.score.signal}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
      <div className="section-title">
        <h2>Previous scans</h2>
      </div>
      {!user || demo ? (
        <SignInRequired feature="scan history" />
      ) : history.isPending ? (
        <Loading text="Loading scan history…" />
      ) : history.isError ? (
        <ErrorState error={history.error} retry={() => history.refetch()} />
      ) : (
        <Panel>
          {!history.data?.length ? (
            <Empty
              title="Your research history starts here"
              text="Run a screen while signed in to save a record of the result."
            />
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Analyzed</th>
                    <th>Matches</th>
                    <th>Unavailable / errors</th>
                    <th>Duration</th>
                    <th>Criteria</th>
                  </tr>
                </thead>
                <tbody>
                  {history.data.map((item) => (
                    <tr key={item.id}>
                      <td>{date(item.created_at)}</td>
                      <td>{item.stocks_analyzed}</td>
                      <td>{item.matches}</td>
                      <td>{item.failures}</td>
                      <td>{number(item.duration_seconds, 2)}s</td>
                      <td>
                        <Link
                          className="text-link"
                          to="/screener"
                          state={{ criteria: item.criteria }}
                        >
                          Reuse <ArrowUpRight size={14} />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      )}
    </>
  );
}
