import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { usePlaidLink } from 'react-plaid-link';
import { Link2 } from 'lucide-react';
import { api } from '../../api/services';
import { ErrorState } from './UI';
function PlaidLauncher({
  token,
  finished,
  cancel,
}: {
  token: string;
  finished: () => void;
  cancel: () => void;
}) {
  const [exitError, setExitError] = useState<string | null>(null);
  const exchange = useMutation({
    mutationFn: ({
      publicToken,
      institutionId,
      institutionName,
    }: {
      publicToken: string;
      institutionId?: string;
      institutionName?: string;
    }) => api.exchangeToken(publicToken, institutionId, institutionName),
    onSuccess: finished,
  });
  const { open, ready, error } = usePlaidLink({
    token,
    onSuccess: (publicToken, metadata) =>
      exchange.mutate({
        publicToken,
        institutionId: metadata.institution?.institution_id,
        institutionName: metadata.institution?.name,
      }),
    onExit: (err) => {
      if (err)
        setExitError(err.display_message || err.error_message || 'The connection was interrupted.');
      else cancel();
    },
  });
  return (
    <div>
      <div className="flex gap-2">
        <button
          className="button primary"
          disabled={!ready || exchange.isPending || exchange.isSuccess}
          onClick={() => {
            setExitError(null);
            open();
          }}
        >
          {exchange.isPending
            ? 'Saving connection…'
            : ready
              ? 'Continue with Plaid'
              : 'Loading Plaid…'}
        </button>
        <button className="button secondary" disabled={exchange.isPending} onClick={cancel}>
          Cancel
        </button>
      </div>
      {error && (
        <ErrorState
          error={new Error('Plaid could not load. Check your connection and try again.')}
        />
      )}
      {exitError && <ErrorState error={new Error(exitError)} />}
      {exchange.isError && (
        <ErrorState error={exchange.error} retry={() => exchange.mutate(exchange.variables!)} />
      )}
    </div>
  );
}
export function ConnectPortfolio() {
  const [token, setToken] = useState<string | null>(null);
  const [complete, setComplete] = useState(false);
  const queryClient = useQueryClient();
  const create = useMutation({
    mutationFn: api.linkToken,
    onSuccess: (data) => {
      setComplete(false);
      setToken(data.link_token);
    },
  });
  function finish() {
    setToken(null);
    setComplete(true);
    queryClient.invalidateQueries({ queryKey: ['portfolio'] });
    queryClient.invalidateQueries({ queryKey: ['connections'] });
  }
  return (
    <div>
      {token ? (
        <PlaidLauncher token={token} finished={finish} cancel={() => setToken(null)} />
      ) : (
        <button
          className="button primary"
          disabled={create.isPending}
          onClick={() => create.mutate()}
        >
          <Link2 size={16} />
          {create.isPending ? 'Preparing secure connection…' : 'Connect investment account'}
        </button>
      )}
      {create.isError && <ErrorState error={create.error} />}
      {complete && (
        <p className="notice" role="status">
          Account connected. Your holdings are refreshing.
        </p>
      )}
    </div>
  );
}
