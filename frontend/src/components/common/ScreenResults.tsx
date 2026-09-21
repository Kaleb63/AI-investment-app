import { useState } from 'react';
import { Link } from 'react-router';
import { ArrowDownUp } from 'lucide-react';
import type { Criteria, Match, ScreenResult } from '../../types/api';
import { label, number, percent } from '../../utils/format';
import { Badge, Empty, Panel } from './UI';
export function CriteriaSummary({ criteria }: { criteria: Criteria }) {
  return (
    <div className="criteria-chips">
      {Object.entries(criteria)
        .filter(([, value]) => value != null)
        .map(([key, value]) => (
          <span key={key}>
            {label(key)} <strong>{number(value)}</strong>
          </span>
        ))}
    </div>
  );
}
export function StockResultsTable({ stocks }: { stocks: Match[] }) {
  const [sort, setSort] = useState('score');
  const [ascending, setAscending] = useState(false);
  const columns = [
    ['score', 'Score'],
    ['pe_ratio', 'P/E'],
    ['revenue_growth', 'Revenue growth'],
    ['eps_growth', 'EPS growth'],
    ['profit_margin', 'Margin'],
    ['return_on_equity', 'ROE'],
    ['current_ratio', 'Current ratio'],
  ] as const;
  const value = (stock: Match): number | null =>
    sort === 'score'
      ? stock.score.overall_score
      : (stock.metrics[sort as keyof typeof stock.metrics] as number | null);
  const sorted = [...stocks].sort((a, b) => {
    const av = value(a),
      bv = value(b);
    if (av == null) return bv == null ? 0 : 1;
    if (bv == null) return -1;
    return (av - bv) * (ascending ? 1 : -1);
  });
  function toggle(key: string) {
    if (sort === key) setAscending(!ascending);
    else {
      setSort(key);
      setAscending(key === 'pe_ratio');
    }
  }
  if (!stocks.length)
    return (
      <Empty
        title="No companies matched"
        text="Try adjusting your criteria or expanding the selected universe."
      />
    );
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Company</th>
            {columns.map(([key, title]) => (
              <th
                className="numeric"
                key={key}
                aria-sort={sort === key ? (ascending ? 'ascending' : 'descending') : 'none'}
              >
                <button onClick={() => toggle(key)}>
                  {title}
                  <ArrowDownUp size={12} />
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((stock) => (
            <tr key={stock.ticker}>
              <td>
                <Link className="ticker-link" to={`/stocks/${stock.ticker}`}>
                  {stock.ticker}
                </Link>
                {stock.ai_explanation && (
                  <details className="inline-explanation">
                    <summary>AI explanation</summary>
                    <p>{stock.ai_explanation}</p>
                  </details>
                )}
              </td>
              <td className="numeric">
                <Badge>{number(stock.score.overall_score)}</Badge>
              </td>
              {columns.slice(1).map(([key]) => (
                <td className="numeric" key={key}>
                  {['pe_ratio', 'current_ratio'].includes(key)
                    ? number(stock.metrics[key as keyof typeof stock.metrics] as number | null, 2)
                    : percent(stock.metrics[key as keyof typeof stock.metrics] as number | null)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
export function ScreenResults({
  result,
}: {
  result: Omit<ScreenResult, 'performance'> & Partial<Pick<ScreenResult, 'performance'>>;
}) {
  const [tab, setTab] = useState('matched');
  const summary = result.summary;
  return (
    <div className="screen-results">
      <div className="scan-summary">
        {[
          ['Searched', summary.total_requested],
          ['Analyzed', summary.successfully_analyzed],
          ['Matched', summary.matched],
          ['Rejected', summary.rejected],
          ['Unavailable', summary.unavailable],
          ['Errors', summary.errored],
        ].map(([name, value]) => (
          <div key={name}>
            <strong>{value}</strong>
            <span>{name}</span>
          </div>
        ))}
      </div>
      <Panel
        title="Screening results"
        subtitle={
          result.performance
            ? `Completed in ${number(result.performance.duration_seconds, 2)} seconds`
            : 'Stored example · simulated financial data'
        }
      >
        <div className="result-tabs" role="tablist" aria-label="Screening result categories">
          {['matched', 'rejected', 'unavailable'].map((item) => (
            <button
              key={item}
              role="tab"
              id={`tab-${item}`}
              aria-controls="screen-result-panel"
              aria-selected={tab === item}
              tabIndex={tab === item ? 0 : -1}
              onKeyDown={(event) => {
                if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
                  event.preventDefault();
                  const tabs = ['matched', 'rejected', 'unavailable'];
                  const next =
                    tabs[(tabs.indexOf(item) + (event.key === 'ArrowRight' ? 1 : 2)) % 3];
                  setTab(next);
                  document.getElementById(`tab-${next}`)?.focus();
                }
              }}
              onClick={() => setTab(item)}
            >
              {label(item)}{' '}
              <span>
                {item === 'matched'
                  ? summary.matched
                  : item === 'rejected'
                    ? summary.rejected
                    : summary.unavailable + summary.errored}
              </span>
            </button>
          ))}
        </div>
        <div role="tabpanel" id="screen-result-panel" aria-labelledby={`tab-${tab}`}>
          {tab === 'matched' ? (
            <StockResultsTable stocks={result.matching_stocks} />
          ) : tab === 'rejected' ? (
            result.rejected_stocks.length ? (
              <div className="rejected-list">
                {result.rejected_stocks.map((stock) => (
                  <details key={stock.ticker}>
                    <summary>
                      {stock.ticker}
                      <span>{stock.failed_criteria.length} criteria not met</span>
                    </summary>
                    {stock.failed_criteria.map((item) => (
                      <p key={item.criterion}>
                        {label(item.criterion)}: reported {number(item.actual_value)}; required{' '}
                        {item.comparison === 'less_than_or_equal' ? 'at most' : 'at least'}{' '}
                        {number(item.required_value)}.
                      </p>
                    ))}
                    {stock.unevaluated_criteria.map((item) => (
                      <p key={item.criterion}>Could not evaluate: {item.reason}</p>
                    ))}
                    <Link className="text-link" to={`/stocks/${stock.ticker}`}>
                      View stock analysis
                    </Link>
                  </details>
                ))}
              </div>
            ) : (
              <Empty
                title="No rejected companies"
                text="No evaluated stocks failed a numerical requirement."
              />
            )
          ) : result.unavailable_stocks.length ? (
            <div className="rejected-list">
              {result.unavailable_stocks.map((item) => (
                <div key={item.ticker}>
                  <strong>{item.ticker}</strong>
                  <Badge tone="amber">{label(item.status)}</Badge>
                  <p>{item.reason}</p>
                  {item.missing_criteria.map((criterion) => (
                    <p key={criterion.criterion}>{criterion.reason}</p>
                  ))}
                </div>
              ))}
            </div>
          ) : (
            <Empty
              title="All selected stocks were evaluated"
              text="There are no unavailable stocks or provider errors in this result."
            />
          )}
        </div>
      </Panel>
    </div>
  );
}
