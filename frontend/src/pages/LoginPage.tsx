import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router';
import { useMutation } from '@tanstack/react-query';
import { ArrowRight, ShieldCheck } from 'lucide-react';
import { useSession } from '../context/Session';
import { ErrorState } from '../components/common/UI';
import { IntelligenceCore } from '../components/common/IntelligenceCore';
export default function LoginPage() {
  const { signIn, user, expired, setDemo } = useSession();
  const navigate = useNavigate();
  const [register, setRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const auth = useMutation({
    mutationFn: () => signIn(email.trim(), password, register),
    onSuccess: () => {
      setPassword('');
      navigate('/');
    },
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    auth.mutate();
  }
  return (
    <div className="auth-layout">
      <div className="auth-intro">
        <IntelligenceCore />
        <div className="eyebrow">AETHER INVESTMENT INTELLIGENCE</div>
        <h1>
          Your research.
          <br />
          <span className="accent">A clearer perspective.</span>
        </h1>
        <p className="muted">
          A private workspace for your portfolio, watchlists, and financial research.
        </p>
      </div>
      <section className="auth-card">
        <ShieldCheck className="accent" size={26} />
        <h2>{register ? 'Create your workspace' : 'Welcome back'}</h2>
        <p>
          {register
            ? 'Save your research and connect your portfolio.'
            : 'Sign in to continue your research.'}
        </p>
        {expired && (
          <div className="notice">
            Your session expired. Sign in again to access your private data.
          </div>
        )}
        {user ? (
          <>
            <p>Signed in as {user.email}</p>
            <Link className="button primary" to="/">
              Open workspace
            </Link>
          </>
        ) : (
          <form onSubmit={submit}>
            <label className="field">
              Email address
              <input
                autoComplete="email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                maxLength={320}
                required
              />
            </label>
            <div className="field">
              <label htmlFor="account-password">Password</label>
              <input
                id="account-password"
                type="password"
                aria-describedby={register ? 'password-hint' : undefined}
                autoComplete={register ? 'new-password' : 'current-password'}
                minLength={register ? 12 : 1}
                maxLength={128}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
              {register && <small id="password-hint">At least 12 characters.</small>}
            </div>
            {auth.isError && <ErrorState error={auth.error} />}
            <button className="button primary full-width" disabled={auth.isPending}>
              {auth.isPending ? 'Opening your workspace…' : register ? 'Create account' : 'Sign in'}
              <ArrowRight size={16} />
            </button>
          </form>
        )}
        <div className="auth-switch">
          {register ? 'Already have an account?' : 'New to Aether?'}{' '}
          <button
            className="text-button"
            disabled={auth.isPending}
            onClick={() => {
              setRegister(!register);
              auth.reset();
              setPassword('');
            }}
          >
            {register ? 'Sign in' : 'Create an account'}
          </button>
        </div>
        <button
          className="text-button"
          onClick={() => {
            setDemo(true);
            navigate('/');
          }}
        >
          Explore the demo first <ArrowRight size={14} />
        </button>
      </section>
    </div>
  );
}
