import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { request, setAccessToken, getAccessToken, refreshSession } from '../api';
import type { CurrentUser } from '../api';
import { AuthContext } from '../session';

interface WebApp {
  initData: string;
  colorScheme?: string;
  ready?: () => void;
  BackButton?: {
    show: () => void;
    hide: () => void;
    onClick: (fn: () => void) => void;
    offClick: (fn: () => void) => void;
  };
}

declare global {
  interface Window {
    Telegram?: { WebApp: WebApp };
  }
}

export default function Auth({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);
  const cache = useQueryClient();

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    async function initializeAuth() {
      setLoading(true);
      window.Telegram?.WebApp?.ready?.();

      // F04: Check existing session first (reloads after 300s window)
      const existingToken = getAccessToken();
      if (existingToken) {
        try {
          const current = await request<CurrentUser>('/auth/me', { signal: controller.signal });
          if (active) {
            setUser(current);
            setLoading(false);
            return;
          }
        } catch {
          // Token expired, try refresh
          const refreshed = await refreshSession();
          if (refreshed) {
            try {
              const current = await request<CurrentUser>('/auth/me', { signal: controller.signal });
              if (active) {
                setUser(current);
                setLoading(false);
                return;
              }
            } catch {
              // fall through to initData
            }
          }
        }
      }

      // No valid session, authenticate via Telegram initData
      const initData = window.Telegram?.WebApp?.initData;
      if (initData) {
        try {
          const data = await request<{ access_token: string }>('/auth/telegram', {
            method: 'POST',
            body: JSON.stringify({ initData }),
            signal: controller.signal,
          });
          if (!active) return;
          setAccessToken(data.access_token);
          const current = await request<CurrentUser>('/auth/me', { signal: controller.signal });
          if (active) {
            setUser(current);
            setError('');
          }
        } catch (err: any) {
          if (active) {
            setError(err?.message || 'Не удалось войти. Проверьте соединение и заново откройте приложение через Telegram.');
          }
        }
      } else {
        if (active) {
          setError('Откройте «Контур» через Telegram. Вход в обычном браузере недоступен.');
        }
      }
      if (active) setLoading(false);
    }

    initializeAuth();
    return () => {
      active = false;
      controller.abort();
    };
  }, [attempt]);

  async function logout() {
    try {
      await request<void>('/auth/logout', { method: 'POST' });
    } catch {
      // ignore
    }
    setAccessToken('');
    cache.clear();
    setUser(null);
    setError('Вы вышли. Для нового входа откройте приложение через Telegram.');
  }

  if (loading) {
    return (
      <main className="session-screen">
        <h1>Контур</h1>
        <p role="status">Проверка сессии…</p>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="session-screen">
        <h1>Контур</h1>
        <p role="status">{error || 'Проверка входа…'}</p>
        {error && (
          <button
            onClick={() => {
              setError('');
              setAttempt(attempt + 1);
            }}
          >
            Повторить вход
          </button>
        )}
      </main>
    );
  }

  return <AuthContext.Provider value={{ user, logout }}>{children}</AuthContext.Provider>;
}
