import { useState, type FormEvent } from 'react';
import { Search, ArrowUpRight } from 'lucide-react';
import { useNavigate } from 'react-router';
import { tickerPattern } from '../../utils/format';
export function StockSearch({ large = false }: { large?: boolean }) {
  const [ticker, setTicker] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();
  function submit(event: FormEvent) {
    event.preventDefault();
    const value = ticker.trim().toUpperCase();
    if (!tickerPattern.test(value)) {
      setError('Enter a valid ticker, such as AAPL.');
      return;
    }
    setError('');
    navigate(`/stocks/${encodeURIComponent(value)}`);
    setTicker('');
  }
  return (
    <form className={`stock-search ${large ? 'large' : ''}`} onSubmit={submit} role="search">
      <Search size={18} />
      <input
        aria-label="Search by ticker"
        placeholder="Search a ticker…"
        value={ticker}
        maxLength={15}
        onChange={(event) => {
          setTicker(event.target.value);
          setError('');
        }}
        aria-invalid={Boolean(error)}
      />
      <button aria-label="Research ticker" title="Research ticker" type="submit">
        <ArrowUpRight size={18} />
      </button>
      {error && (
        <span className="search-error" role="alert">
          {error}
        </span>
      )}
    </form>
  );
}
