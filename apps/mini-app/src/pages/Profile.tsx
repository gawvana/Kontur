import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../session';
import { request } from '../api';
import type { NotificationItem } from '../api';

interface SessionItem {
  id: string;
  user_id: number;
  expires_at: string;
  user_agent: string | null;
  created_at: string;
}

export default function Profile() {
  const { user, logout } = useAuth();
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const [supportModal, setSupportModal] = useState(false);
  const [supportSubject, setSupportSubject] = useState('');
  const [supportMessage, setSupportMessage] = useState('');
  const [toast, setToast] = useState('');

  const cache = useQueryClient();

  // Active sessions query
  const sessionsQuery = useQuery({
    queryKey: ['my-sessions'],
    queryFn: ({ signal }) => request<SessionItem[]>('/auth/sessions', { signal }),
    retry: false,
  });

  // Notifications query
  const notificationsQuery = useQuery({
    queryKey: ['my-notifications'],
    queryFn: ({ signal }) => request<NotificationItem[]>('/notifications', { signal }),
    retry: false,
  });

  // Revoke session
  const revokeSession = useMutation({
    mutationFn: (sessionId: string) => request(`/auth/sessions/${sessionId}`, { method: 'DELETE' }),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ['my-sessions'] });
      setToast('Сессия отозвана');
      setTimeout(() => setToast(''), 3000);
    },
  });

  // Support ticket
  const sendSupport = useMutation({
    mutationFn: () =>
      request('/support', {
        method: 'POST',
        body: JSON.stringify({
          subject: supportSubject.trim(),
          message: supportMessage.trim(),
        }),
      }),
    onSuccess: () => {
      setSupportModal(false);
      setSupportSubject('');
      setSupportMessage('');
      setToast('Обращение в поддержку отправлено');
      setTimeout(() => setToast(''), 4000);
    },
  });

  return (
    <section>
      <h2>Профиль и настройки</h2>

      {toast && (
        <div style={{ background: 'var(--primary)', color: 'var(--on-primary)', padding: '10px 14px', borderRadius: '12px', margin: '12px 0' }}>
          {toast}
        </div>
      )}

      <article>
        <h3>{user.first_name || user.username || 'Пользователь'}</h3>
        <p>Telegram ID: <code>{user.telegram_id}</code></p>
        {user.username && <p>Username: <code>@{user.username}</code></p>}
        <p>Роль: <strong>{user.role}</strong></p>
        <p className="muted" style={{ fontSize: '13px' }}>
          Вход подтверждает доступ к аккаунту в Telegram. Ваши заметки и списки контактов остаются приватными.
        </p>
      </article>

      {/* Theme */}
      <article>
        <label htmlFor="theme" style={{ fontWeight: 650 }}>Оформление</label>
        <select
          id="theme"
          defaultValue={localStorage.getItem('kontur-theme') || 'system'}
          onChange={(e) => {
            localStorage.setItem('kontur-theme', e.target.value);
            window.dispatchEvent(new Event('kontur-theme'));
          }}
        >
          <option value="system">Системное (автоматически)</option>
          <option value="dark">Тёмная тема</option>
          <option value="light">Светлая тема</option>
        </select>
      </article>

      {/* Notifications */}
      <article>
        <h3>Уведомления ({notificationsQuery.data?.length || 0})</h3>
        {notificationsQuery.isLoading && <p className="muted">Загрузка…</p>}
        {notificationsQuery.data?.length === 0 && <p className="muted">Нет новых уведомлений.</p>}
        {notificationsQuery.data?.slice(0, 5).map((n) => (
          <div key={n.id} style={{ borderTop: '1px solid var(--line)', paddingTop: '8px', marginTop: '8px' }}>
            <strong>{n.title}</strong>
            <p style={{ margin: '4px 0', fontSize: '14px' }}>{n.message}</p>
            <small className="muted">{new Date(n.created_at).toLocaleDateString()}</small>
          </div>
        ))}
      </article>

      {/* Active Sessions */}
      <article>
        <h3>Активные сессии ({sessionsQuery.data?.length || 0})</h3>
        {sessionsQuery.data?.map((s) => (
          <div
            key={s.id}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              borderTop: '1px solid var(--line)',
              paddingTop: '8px',
              marginTop: '8px',
            }}
          >
            <div>
              <div style={{ fontSize: '13px', fontWeight: 600 }}>{s.user_agent || 'Устройство'}</div>
              <small className="muted">Создана: {new Date(s.created_at).toLocaleDateString()}</small>
            </div>
            <button
              onClick={() => revokeSession.mutate(s.id)}
              style={{ fontSize: '12px', padding: '4px 8px', minHeight: '30px', background: 'var(--line)', color: 'var(--ink)' }}
            >
              Отозвать
            </button>
          </div>
        ))}
      </article>

      {/* Support & Logout */}
      <div style={{ display: 'grid', gap: '10px', marginTop: '20px' }}>
        <button
          onClick={() => setSupportModal(true)}
          style={{ background: 'var(--surface)', color: 'var(--ink)' }}
        >
          💬 Написать в поддержку
        </button>

        <button
          disabled={pending}
          onClick={async () => {
            setPending(true);
            setError('');
            try {
              await logout();
            } catch {
              setError('Не удалось отозвать сессию. Повторите выход.');
            } finally {
              setPending(false);
            }
          }}
          style={{ background: 'var(--red, #922b4e)', color: '#fff' }}
        >
          Выйти и отозвать текущую сессию
        </button>
      </div>

      {error && <p role="alert">{error}</p>}

      {/* Support Modal */}
      {supportModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'grid', placeItems: 'center', zIndex: 100, padding: '16px' }}>
          <article style={{ background: 'var(--surface)', maxWidth: '420px', width: '100%', borderRadius: '20px', padding: '20px' }}>
            <h3>Обращение в поддержку</h3>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                sendSupport.mutate();
              }}
            >
              <label htmlFor="sup-sub">Тема обращения</label>
              <input
                id="sup-sub"
                value={supportSubject}
                onChange={(e) => setSupportSubject(e.target.value)}
                placeholder="Коротко о проблеме"
                required
                minLength={3}
              />
              <label htmlFor="sup-msg">Сообщение</label>
              <textarea
                id="sup-msg"
                value={supportMessage}
                onChange={(e) => setSupportMessage(e.target.value)}
                placeholder="Опишите вопрос или найденную ошибку…"
                style={{ width: '100%', minHeight: '100px', borderRadius: '12px', border: '1px solid var(--line)', padding: '10px', background: 'var(--surface)', color: 'var(--ink)' }}
                required
                minLength={10}
              />
              <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                <button type="button" onClick={() => setSupportModal(false)} style={{ background: 'var(--line)', color: 'var(--ink)' }}>
                  Отмена
                </button>
                <button type="submit" disabled={supportMessage.trim().length < 10 || sendSupport.isPending}>
                  {sendSupport.isPending ? 'Отправка…' : 'Отправить'}
                </button>
              </div>
            </form>
          </article>
        </div>
      )}
    </section>
  );
}
