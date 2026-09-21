import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api } from '../api/services';
import { setAccessToken } from '../api/client';
import type { Analysis, User } from '../types/api';
interface Session {
  demo: boolean;
  setDemo: (value: boolean) => void;
  user: User | null;
  signIn: (email: string, password: string, register?: boolean) => Promise<void>;
  signOut: () => void;
  recent: Analysis[];
  remember: (value: Analysis) => void;
  expired: boolean;
}
const Context = createContext<Session | null>(null);
export function SessionProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [demo, updateDemo] = useState(true);
  const [user, setUser] = useState<User | null>(null);
  const [recent, setRecent] = useState<Analysis[]>([]);
  const [expired, setExpired] = useState(false);
  function setDemo(value: boolean) {
    queryClient.cancelQueries();
    queryClient.clear();
    setRecent([]);
    updateDemo(value);
  }
  function signOut() {
    setAccessToken(null);
    setUser(null);
    queryClient.cancelQueries();
    queryClient.clear();
    setRecent([]);
  }
  useEffect(() => {
    const handler = () => {
      signOut();
      setExpired(true);
    };
    window.addEventListener('session-expired', handler);
    return () => window.removeEventListener('session-expired', handler);
  }, [queryClient]);
  async function signIn(email: string, password: string, register = false) {
    if (register) await api.register(email, password);
    const token = await api.login(email, password);
    setAccessToken(token.access_token);
    try {
      const nextUser = await api.me();
      queryClient.clear();
      setUser(nextUser);
      updateDemo(false);
      setExpired(false);
      setRecent([]);
    } catch (error) {
      setAccessToken(null);
      throw error;
    }
  }
  function remember(value: Analysis) {
    setRecent((previous) =>
      [value, ...previous.filter((item) => item.ticker !== value.ticker)].slice(0, 12),
    );
  }
  return (
    <Context.Provider value={{ demo, setDemo, user, signIn, signOut, recent, remember, expired }}>
      {children}
    </Context.Provider>
  );
}
export function useSession() {
  const value = useContext(Context);
  if (!value) throw new Error('Session provider is missing.');
  return value;
}
