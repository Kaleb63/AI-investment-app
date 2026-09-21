import { Link } from 'react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { LogOut, RefreshCw, Unplug } from 'lucide-react';
import { API_BASE_URL } from '../api/client';
import { api } from '../api/services';
import { useSession } from '../context/Session';
import { Badge, Empty, ErrorState, Loading, PageHeader, Panel } from '../components/common/UI';
import { ConnectPortfolio } from '../components/common/ConnectPortfolio';
export default function SettingsPage() {
  const { demo, setDemo, user, signOut } = useSession();
  const queryClient = useQueryClient();
  const health = useQuery({
    queryKey: ['health'],
    queryFn: ({ signal }) => api.health(signal),
    staleTime: 60000,
    retry: false,
  });
  const connections = useQuery({
    queryKey: ['connections', user?.id],
    queryFn: ({ signal }) => api.connections(signal),
    enabled: Boolean(user) && !demo,
  });
  const remove = useMutation({
    mutationFn: api.removeConnection,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connections'] });
      queryClient.removeQueries({ queryKey: ['portfolio'] });
    },
  });
  return (
    <>
      <PageHeader
        eyebrow="WORKSPACE / SETTINGS"
        title="Make the workspace yours."
        description="Manage your session, data environment, and connected investment accounts."
      />
      <div className="two-column">
        <Panel title="Data environment">
          <div className="pad">
            <div className="setting-row">
              <div>
                <strong>{demo ? 'Demo workspace' : 'Live research'}</strong>
                <p className="muted small">
                  Demo data is simulated and labeled throughout the workspace.
                </p>
              </div>
              <button className="button secondary" onClick={() => setDemo(!demo)}>
                {demo ? 'Use live research' : 'Use demo'}
              </button>
            </div>
          </div>
        </Panel>
        <Panel title="Your session">
          <div className="pad">
            <strong>{user?.email || 'Guest explorer'}</strong>
            <p className="muted small mb-4">
              {user
                ? 'Your sign-in token is kept in memory. Refreshing the page ends the session.'
                : 'Research public stocks, or sign in to access your private library.'}
            </p>
            {user ? (
              <button className="button secondary" onClick={signOut}>
                <LogOut size={15} />
                Sign out
              </button>
            ) : (
              <Link className="button secondary" to="/login">
                Sign in / create account
              </Link>
            )}
          </div>
        </Panel>
      </div>
      <Panel
        title="Research server"
        subtitle="Connectivity and configuration"
        className="mt-6"
        actions={
          <button
            className="text-button"
            disabled={health.isFetching}
            onClick={() => health.refetch()}
          >
            <RefreshCw size={14} />
            Check connection
          </button>
        }
      >
        <div className="pad">
          <div className="setting-row">
            <code>{API_BASE_URL}</code>
            <Badge tone={health.isError ? 'amber' : 'cyan'}>
              {health.isFetching ? 'Checking' : health.isError ? 'Unavailable' : 'Reachable'}
            </Badge>
          </div>
          {health.data && <p className="muted small mt-4">{health.data.message}</p>}
          {health.isError && <ErrorState error={health.error} />}
          <p className="muted small mt-4">
            A reachable server does not guarantee that every data provider is configured. Provider
            errors appear within the affected feature.
          </p>
        </div>
      </Panel>
      {user && !demo && (
        <Panel
          title="Connected accounts"
          subtitle="Connections stored by your backend"
          className="mt-6"
          actions={<ConnectPortfolio />}
        >
          {remove.isError && <ErrorState error={remove.error} />}
          {connections.isPending ? (
            <Loading text="Loading connections…" />
          ) : connections.isError ? (
            <ErrorState error={connections.error} retry={() => connections.refetch()} />
          ) : !connections.data?.length ? (
            <Empty
              title="No investment accounts connected"
              text="Connect an account through Plaid to begin viewing your holdings."
            />
          ) : (
            <div className="connection-list">
              {connections.data.map((item) => (
                <div key={item.id}>
                  <strong>{item.institution_name || 'Investment account'}</strong>
                  <Badge tone="muted">{item.connection_status}</Badge>
                  <button
                    className="text-button danger"
                    disabled={remove.isPending}
                    onClick={() => {
                      if (
                        window.confirm(
                          `Remove the saved connection to ${item.institution_name || 'this investment account'}?`,
                        )
                      )
                        remove.mutate(item.id);
                    }}
                  >
                    <Unplug size={15} />
                    Remove saved connection
                  </button>
                </div>
              ))}
            </div>
          )}
        </Panel>
      )}
      <div id="about">
        <Panel
          title="Built for understanding"
          subtitle="The Aether research approach"
          className="mt-6"
        >
          <div className="about-grid">
            <div>
              <span>01</span>
              <h3>Market evidence</h3>
              <p>Financial data comes through the backend. Unavailable metrics remain N/A.</p>
            </div>
            <div>
              <span>02</span>
              <h3>Transparent rules</h3>
              <p>
                The backend calculates scores, filters companies, and measures portfolio
                concentration.
              </p>
            </div>
            <div>
              <span>03</span>
              <h3>AI interpretation</h3>
              <p>
                AI explains evidence and translates queries into criteria. Its output is clearly
                distinguished.
              </p>
            </div>
          </div>
          <p className="data-note pad">
            Aether is a research and demonstration tool. It cannot place trades. Scoring is not a
            prediction or investment advice.
          </p>
        </Panel>
      </div>
    </>
  );
}
