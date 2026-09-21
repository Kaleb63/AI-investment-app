import { Component, type ReactNode, type ErrorInfo } from 'react';
import { AlertCircle, ArrowUpRight, LoaderCircle, Search, ShieldCheck } from 'lucide-react';
import { Link } from 'react-router';
import { errorMessage } from '../../api/client';
import { useSession } from '../../context/Session';
export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {actions && <div className="heading-actions">{actions}</div>}
    </div>
  );
}
export function Panel({
  title,
  subtitle,
  actions,
  children,
  className = '',
}: {
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      {title && (
        <div className="panel-heading">
          <div>
            <h2>{title}</h2>
            {subtitle && <p>{subtitle}</p>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}
export function Badge({
  children,
  tone = 'cyan',
}: {
  children: ReactNode;
  tone?: 'cyan' | 'muted' | 'amber' | 'green';
}) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}
export function Loading({ text = 'Retrieving financial data…' }: { text?: string }) {
  return (
    <div className="loading-state" role="status">
      <LoaderCircle className="spin" size={22} />
      <span>{text}</span>
      <div className="skeleton" />
      <div className="skeleton short" />
    </div>
  );
}
export function ErrorState({ error, retry }: { error: unknown; retry?: () => void }) {
  return (
    <div className="error-state" role="alert">
      <AlertCircle size={20} />
      <div>
        <strong>We couldn’t complete that request</strong>
        <p>{errorMessage(error)}</p>
        {retry && (
          <button className="text-button" onClick={retry}>
            Try again <ArrowUpRight size={14} />
          </button>
        )}
      </div>
    </div>
  );
}
export function Empty({
  title,
  text,
  action,
}: {
  title: string;
  text: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <div className="empty-icon">
        <Search size={24} />
      </div>
      <h3>{title}</h3>
      <p>{text}</p>
      {action}
    </div>
  );
}
export function SignInRequired({ feature }: { feature: string }) {
  const { user, demo, setDemo } = useSession();
  return (
    <Panel>
      <Empty
        title={`Your ${feature}, in one place`}
        text={
          user && demo
            ? 'Switch to live research to access the private library associated with your account.'
            : 'Sign in to access your private research workspace. Your saved data stays associated with your account.'
        }
        action={
          user && demo ? (
            <button className="button primary" onClick={() => setDemo(false)}>
              Open live research
            </button>
          ) : (
            <Link className="button primary" to="/login">
              <ShieldCheck size={16} /> Sign in
            </Link>
          )
        }
      />
    </Panel>
  );
}
export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch(_error: Error, _info: ErrorInfo) {
    /* Avoid logging potentially sensitive response data. */
  }
  render() {
    return this.state.failed ? (
      <main className="fatal">
        <h1>Something interrupted the workspace.</h1>
        <p>Reload to start a fresh session.</p>
        <button className="button primary" onClick={() => window.location.reload()}>
          Reload workspace
        </button>
      </main>
    ) : (
      this.props.children
    );
  }
}
