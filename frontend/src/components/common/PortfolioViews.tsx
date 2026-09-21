import { Link } from 'react-router';
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import type { Holding, Portfolio } from '../../types/api';
import { currency, label, number, percent } from '../../utils/format';
import { Badge, Empty } from './UI';
const colors = ['#42d8ed', '#548cf5', '#a48ae8', '#79a5b8', '#4d7089'];
export function Allocation({
  portfolio,
  sectors = false,
}: {
  portfolio: Portfolio;
  sectors?: boolean;
}) {
  const entries = Object.entries(
    sectors ? portfolio.sector_allocation : portfolio.asset_type_allocation,
  ).map(([name, value]) => ({ name: label(name), value }));
  if (!entries.length)
    return (
      <Empty
        title="No allocation data"
        text="Allocation will appear when holdings are available."
      />
    );
  if (sectors)
    return (
      <div className="sector-list">
        {entries.map((entry) => (
          <div key={entry.name}>
            <div>
              <span>{entry.name}</span>
              <strong>{percent(entry.value)}</strong>
            </div>
            <div className="meter">
              <span style={{ width: `${Math.min(Math.max(entry.value, 0), 100)}%` }} />
            </div>
          </div>
        ))}
        <p className="small muted">
          Equity sectors as a percentage of total portfolio value. ETF and cash exposure are
          excluded from this sector breakdown.
        </p>
      </div>
    );
  return (
    <div className="allocation">
      <div className="donut">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={entries}
              dataKey="value"
              nameKey="name"
              innerRadius="72%"
              outerRadius="94%"
              paddingAngle={5}
              stroke="none"
              isAnimationActive={false}
            >
              {entries.map((entry, i) => (
                <Cell key={entry.name} fill={colors[i % colors.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value) => percent(Number(value))}
              contentStyle={{
                background: '#101e30',
                border: '1px solid #284057',
                borderRadius: 8,
                color: '#e4f2fb',
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="donut-center">
          <strong>{sectors ? entries.length : portfolio.position_count}</strong>
          <span>{sectors ? 'SECTORS' : 'POSITIONS'}</span>
        </div>
      </div>
      <div className="allocation-legend">
        {entries.map((entry, i) => (
          <div key={entry.name}>
            <span>
              <i style={{ background: colors[i % colors.length] }} />
              {entry.name}
            </span>
            <strong>{percent(entry.value)}</strong>
          </div>
        ))}
      </div>
      {sectors && (
        <p className="small muted">
          Equity sectors as a percentage of total portfolio value. ETF exposure is not broken down.
        </p>
      )}
    </div>
  );
}
export function HoldingsTable({
  holdings,
  compact = false,
}: {
  holdings: Holding[];
  compact?: boolean;
}) {
  if (!holdings.length)
    return (
      <Empty title="No holdings yet" text="Connect an investment account to see your positions." />
    );
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Asset</th>
            {!compact && (
              <>
                <th>Type</th>
                <th className="numeric">Shares</th>
                <th className="numeric">Price</th>
              </>
            )}
            <th className="numeric">Value</th>
            <th className="numeric">Weight</th>
            <th className="numeric">Score</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((item, index) => (
            <tr key={`${item.ticker}-${index}`}>
              <td>
                <div className="asset-cell">
                  <span className={`ticker-avatar ticker-${index % 4}`}>
                    {(item.ticker || '$').slice(0, 1)}
                  </span>
                  <div>
                    {item.ticker && item.type === 'equity' ? (
                      <Link
                        className="ticker-link"
                        to={`/stocks/${encodeURIComponent(item.ticker)}`}
                      >
                        {item.ticker}
                      </Link>
                    ) : (
                      <strong>{item.ticker || 'Cash'}</strong>
                    )}
                    <small>{item.name || 'Name unavailable'}</small>
                  </div>
                </div>
              </td>
              {!compact && (
                <>
                  <td>
                    <Badge tone="muted">{label(item.type)}</Badge>
                  </td>
                  <td className="numeric">{number(item.shares, 4)}</td>
                  <td className="numeric">{currency(item.price)}</td>
                </>
              )}
              <td className="numeric">{currency(item.value)}</td>
              <td className="numeric">{percent(item.weight)}</td>
              <td className="numeric">
                {item.type === 'equity' && item.analysis?.score ? (
                  <Badge>{number(item.analysis.score.overall_score)}</Badge>
                ) : (
                  <span className="muted small" title={item.analysis?.reason}>
                    Not analyzed
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
