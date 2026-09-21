import type { Analysis, EquityScore } from '../../types/api';
import { label, number, percent } from '../../utils/format';
import { Badge, Panel } from './UI';
export function ScoreGauge({ score }: { score: EquityScore }) {
  return (
    <div className="score-gauge">
      <svg viewBox="0 0 180 180" aria-hidden="true">
        <circle cx="90" cy="90" r="74" fill="none" stroke="#183247" strokeWidth="6" />
        <circle
          cx="90"
          cy="90"
          r="74"
          fill="none"
          stroke="#44d9ee"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={`${((score.overall_score ?? 0) / 100) * 465} 465`}
          transform="rotate(-90 90 90)"
        />
        <circle cx="90" cy="90" r="63" fill="none" stroke="#1b4a60" strokeDasharray="1 7" />
      </svg>
      <div>
        <strong>{number(score.overall_score)}</strong>
        <span>OUT OF 100</span>
      </div>
    </div>
  );
}
export function ScorePanel({ analysis }: { analysis: Analysis }) {
  const score = analysis.score;
  return (
    <div className="score-grid">
      <Panel title="Investment score" subtitle="Deterministic financial model">
        <ScoreGauge score={score} />
        <div className="score-caption">
          <Badge>{label(score.signal)} fundamentals</Badge>
          <p>{percent(score.data_coverage)} data coverage</p>
        </div>
      </Panel>
      <Panel title="Behind the score" subtitle="Category scores and their configured weights">
        <div className="category-list">
          {Object.entries(score.categories).map(([category, value]) => (
            <div key={category}>
              <div>
                <span>{label(category)}</span>
                <small>{percent(score.weights[category])} weight</small>
                <strong>{number(value)}</strong>
              </div>
              <div
                className="meter"
                role="meter"
                aria-label={label(category)}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={value ?? undefined}
                aria-valuetext={value === null ? 'Unavailable' : `${value} out of 100`}
              >
                <span style={{ width: `${value ?? 0}%` }} />
              </div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
export function MetricsGrid({ analysis }: { analysis: Analysis }) {
  const fields = [
    ['pe_ratio', 'P/E ratio', false],
    ['eps', 'Earnings per share', false],
    ['revenue_growth', 'Revenue growth', true],
    ['eps_growth', 'EPS growth', true],
    ['profit_margin', 'Profit margin', true],
    ['return_on_equity', 'Return on equity', true],
    ['current_ratio', 'Current ratio', false],
    ['beta', 'Beta', false],
    ['52_week_return', '52-week return', true],
  ] as const;
  return (
    <div className="metrics-grid">
      {fields.map(([key, title, isPercent]) => (
        <div className="metric" key={key}>
          <span>{title}</span>
          <strong>
            {isPercent ? percent(analysis.metrics[key]) : number(analysis.metrics[key], 2)}
          </strong>
        </div>
      ))}
    </div>
  );
}
