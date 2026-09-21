export type Nullable = number | null;
export interface Metrics {
  ticker: string;
  pe_ratio: Nullable;
  eps: Nullable;
  revenue_growth: Nullable;
  eps_growth: Nullable;
  profit_margin: Nullable;
  return_on_equity: Nullable;
  current_ratio: Nullable;
  beta: Nullable;
  '52_week_return': Nullable;
}
export interface EquityScore {
  overall_score: Nullable;
  signal: string;
  data_coverage: number;
  categories: Record<string, Nullable>;
  weights: Record<string, number>;
  reasons: string[];
}
export interface Analysis {
  ticker: string;
  metrics: Metrics;
  score: EquityScore;
}
export interface Quote {
  ticker: string;
  price: number;
  quote: {
    c: number;
    d: Nullable;
    dp: Nullable;
    h: Nullable;
    l: Nullable;
    o: Nullable;
    pc: Nullable;
    t: number;
  };
}
export interface Historical {
  ticker: string;
  start_date: string;
  end_date: string;
  observations: number;
  latest_close: number;
  returns: Record<string, Nullable>;
  annualized_volatility: Nullable;
  moving_averages: Record<string, Nullable>;
  note: string;
}
export interface Criteria {
  min_score?: number | null;
  max_pe_ratio?: number | null;
  min_revenue_growth?: number | null;
  min_eps_growth?: number | null;
  min_profit_margin?: number | null;
  min_return_on_equity?: number | null;
  min_current_ratio?: number | null;
}
export interface Match extends Analysis {
  passed_criteria: string[];
  ai_explanation?: string | null;
}
export interface Rejected extends Match {
  failed_criteria: {
    criterion: string;
    comparison: string;
    required_value: number;
    actual_value: number;
  }[];
  unevaluated_criteria: { criterion: string; required_value: number; reason: string }[];
}
export interface ScreenResult {
  criteria: Criteria;
  summary: {
    total_requested: number;
    successfully_analyzed: number;
    matched: number;
    rejected: number;
    unavailable: number;
    errored: number;
  };
  performance: {
    duration_seconds: number;
    stocks_attempted: number;
    stocks_successfully_analyzed: number;
    stocks_failed: number;
    average_processing_seconds: number;
    successful_stocks_per_second: number;
    failure_percentage: number;
    cache_hits: number;
    cache_misses: number;
  };
  matching_stocks: Match[];
  rejected_stocks: Rejected[];
  unavailable_stocks: {
    ticker: string;
    status: string;
    reason: string;
    missing_criteria: { criterion: string; reason: string }[];
  }[];
}
export interface AIScreenResult {
  query: string;
  interpreted_criteria: Criteria;
  number_of_stocks_searched: number;
  results: ScreenResult;
  explanation_errors: Record<string, string>;
}
export interface Holding {
  ticker: string | null;
  name: string | null;
  type: string;
  shares: Nullable;
  price: Nullable;
  value: number;
  weight: number;
  sector?: string | null;
  analysis?: { metrics?: Metrics; score?: EquityScore; status?: string; reason?: string } | null;
}
export interface Portfolio {
  simulated: boolean;
  total_value: number;
  position_count: number;
  largest_position: { ticker: string | null; name: string | null; weight: number } | null;
  top_3_concentration: number;
  top_5_concentration: number;
  concentration_hhi: number;
  effective_position_count: Nullable;
  asset_type_allocation: Record<string, number>;
  sector_allocation: Record<string, number>;
  largest_sector: { sector: string; weight: number } | null;
  holdings: Holding[];
  ai_explanation: string | null;
}
export interface User {
  id: string;
  email: string;
  created_at: string;
}
export interface WatchlistEntry {
  id: string;
  ticker: string;
  created_at: string;
}
export interface SavedScreen {
  id: string;
  name: string;
  criteria: Criteria;
  created_at: string;
}
export interface ScanHistory {
  id: string;
  criteria: Criteria;
  stocks_analyzed: number;
  matches: number;
  failures: number;
  duration_seconds: number;
  created_at: string;
}
export interface Connection {
  id: string;
  item_id: string;
  institution_id: string | null;
  institution_name: string | null;
  connection_status: string;
}
export interface Universe {
  source: string;
  total_available: number;
  offset: number;
  limit: number;
  symbols: { ticker: string; name: string; asset_type: string; exchange: string }[];
}
