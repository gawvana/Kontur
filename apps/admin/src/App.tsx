import { useState, useEffect } from 'react';
import {
  request,
  setAccessToken,
  ApiError,
  type CurrentUser,
  type AdminDashboardStats,
  type AdminCase,
  type AdminAppeal,
  type AdminSupportTicket,
  type AdminUserItem,
  type AdminAuditLog,
  type TwoFactorSetup,
} from './api';

export default function App() {
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [authError, setAuthError] = useState('');
  const [loading, setLoading] = useState(true);

  // 2FA state
  const [twoFaNeeded, setTwoFaNeeded] = useState(false);
  const [twoFaSetup, setTwoFaSetup] = useState<TwoFactorSetup | null>(null);
  const [twoFaCode, setTwoFaCode] = useState('');
  const [twoFaError, setTwoFaError] = useState('');

  // Dashboard tab
  const [tab, setTab] = useState<'cases' | 'appeals' | 'support' | 'users' | 'audit'>('cases');
  const [stats, setStats] = useState<AdminDashboardStats | null>(null);

  // Cases list & decision modal
  const [cases, setCases] = useState<AdminCase[]>([]);
  const [selectedCase, setSelectedCase] = useState<AdminCase | null>(null);
  const [decisionType, setDecisionType] = useState<'APPROVE' | 'REJECT' | 'REQUEST_INFO'>('APPROVE');
  const [decisionReason, setDecisionReason] = useState('');

  // Appeals
  const [appeals, setAppeals] = useState<AdminAppeal[]>([]);
  const [selectedAppeal, setSelectedAppeal] = useState<AdminAppeal | null>(null);
  const [appealDecisionStatus, setAppealDecisionStatus] = useState<'UPHELD' | 'OVERTURNED' | 'REJECTED'>('UPHELD');
  const [appealNote, setAppealNote] = useState('');

  // Support
  const [supportTickets, setSupportTickets] = useState<AdminSupportTicket[]>([]);
  const [answeringTicket, setAnsweringTicket] = useState<AdminSupportTicket | null>(null);
  const [supportAnswer, setSupportAnswer] = useState('');

  // Users & roles
  const [users, setUsers] = useState<AdminUserItem[]>([]);
  const [userSearch, setUserSearch] = useState('');
  const [editingUser, setEditingUser] = useState<AdminUserItem | null>(null);
  const [newRole, setNewRole] = useState('USER');
  const [roleReason, setRoleReason] = useState('');

  // Audit logs
  const [auditLogs, setAuditLogs] = useState<AdminAuditLog[]>([]);

  const [toast, setToast] = useState('');

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(''), 3500);
  }

  // Initial Auth
  useEffect(() => {
    async function initAuth() {
      const initData = (window as Window & { Telegram?: { WebApp?: { initData?: string } } }).Telegram?.WebApp?.initData;
      if (!initData) {
        setAuthError('Откройте панель через Telegram Mini App. Обычный браузер не предоставляет подтверждённый вход.');
        setLoading(false);
        return;
      }

      try {
        const authRes = await request<{ access_token: string; user: CurrentUser }>('/auth/telegram', {
          method: 'POST',
          body: JSON.stringify({ initData }),
        });
        setAccessToken(authRes.access_token);
        const me = await request<CurrentUser>('/auth/me');
        setCurrentUser(me);

        // Check staff permissions
        if (!['MODERATOR', 'SENIOR_MODERATOR', 'ADMIN', 'OWNER'].includes(me.role)) {
          setAuthError('Недостаточно прав. Панель доступна только сотрудникам Контура.');
          setLoading(false);
          return;
        }

        // Try accessing dashboard to see if 2FA is needed
        try {
          const statsRes = await request<AdminDashboardStats>('/admin/dashboard');
          setStats(statsRes);
          loadTabData(tab);
        } catch (e) {
          if (e instanceof ApiError && e.status === 503) {
            setTwoFaNeeded(true);
          } else {
            setAuthError((e as Error).message);
          }
        }
      } catch (err: any) {
        setAuthError(err.message || 'Ошибка входа');
      } finally {
        setLoading(false);
      }
    }

    initAuth();
  }, []);

  async function loadTabData(currentTab: string) {
    try {
      if (currentTab === 'cases') {
        const list = await request<AdminCase[]>('/admin/cases');
        setCases(list);
      } else if (currentTab === 'appeals') {
        const list = await request<AdminAppeal[]>('/admin/appeals');
        setAppeals(list);
      } else if (currentTab === 'support') {
        const list = await request<AdminSupportTicket[]>('/admin/support');
        setSupportTickets(list);
      } else if (currentTab === 'users') {
        const list = await request<AdminUserItem[]>(`/admin/users${userSearch ? `?search=${encodeURIComponent(userSearch)}` : ''}`);
        setUsers(list);
      } else if (currentTab === 'audit') {
        const list = await request<AdminAuditLog[]>('/admin/audit-log');
        setAuditLogs(list);
      }
      const st = await request<AdminDashboardStats>('/admin/dashboard');
      setStats(st);
    } catch (e: any) {
      if (e.status === 503) {
        setTwoFaNeeded(true);
      }
    }
  }

  useEffect(() => {
    if (currentUser && !twoFaNeeded) {
      loadTabData(tab);
    }
  }, [tab]);

  // 2FA Setup Flow
  async function startTwoFaSetup() {
    try {
      const res = await request<TwoFactorSetup>('/auth/2fa/setup', { method: 'POST' });
      setTwoFaSetup(res);
    } catch (err: any) {
      setTwoFaError(err.message);
    }
  }

  async function handleVerifyTwoFa(e: React.FormEvent) {
    e.preventDefault();
    setTwoFaError('');
    try {
      await request('/auth/2fa/verify', {
        method: 'POST',
        body: JSON.stringify({ code: twoFaCode.trim() }),
      });
      setTwoFaNeeded(false);
      setTwoFaSetup(null);
      showToast('2FA успешно подтверждён');
      loadTabData(tab);
    } catch (err: any) {
      setTwoFaError(err.message || 'Неверный код 2FA');
    }
  }

  // Handle case decision
  async function submitCaseDecision(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedCase) return;
    try {
      await request(`/admin/cases/${selectedCase.id}/decision`, {
        method: 'POST',
        body: JSON.stringify({
          decision: decisionType,
          reason: decisionReason.trim(),
        }),
      });
      setSelectedCase(null);
      setDecisionReason('');
      showToast(`Решение по обращению #${selectedCase.id} принято`);
      loadTabData('cases');
    } catch (err: any) {
      showToast(err.message || 'Ошибка сохранения решения');
    }
  }

  // Handle appeal decision
  async function submitAppealDecision(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedAppeal) return;
    try {
      await request(`/admin/appeals/${selectedAppeal.id}/decide`, {
        method: 'POST',
        body: JSON.stringify({
          status: appealDecisionStatus,
          decision_note: appealNote.trim(),
        }),
      });
      setSelectedAppeal(null);
      setAppealNote('');
      showToast(`Решение по апелляции #${selectedAppeal.id} принято`);
      loadTabData('appeals');
    } catch (err: any) {
      showToast(err.message || 'Ошибка');
    }
  }

  // Handle support ticket answer
  async function submitSupportAnswer(e: React.FormEvent) {
    e.preventDefault();
    if (!answeringTicket) return;
    try {
      await request(`/admin/support/${answeringTicket.id}/answer`, {
        method: 'POST',
        body: JSON.stringify({ answer: supportAnswer.trim() }),
      });
      setAnsweringTicket(null);
      setSupportAnswer('');
      showToast('Ответ пользователю отправлен');
      loadTabData('support');
    } catch (err: any) {
      showToast(err.message || 'Ошибка');
    }
  }

  // Handle user role update
  async function submitRoleChange(e: React.FormEvent) {
    e.preventDefault();
    if (!editingUser) return;
    try {
      await request(`/admin/users/${editingUser.id}/role`, {
        method: 'POST',
        body: JSON.stringify({
          role: newRole,
          reason: roleReason.trim(),
        }),
      });
      setEditingUser(null);
      setRoleReason('');
      showToast(`Роль пользователя @${editingUser.username || editingUser.id} изменена на ${newRole}`);
      loadTabData('users');
    } catch (err: any) {
      showToast(err.message || 'Ошибка при изменении роли');
    }
  }

  if (loading) {
    return (
      <main className="session-screen">
        <h1>Контур · Панель сотрудников</h1>
        <p role="status">Проверка прав доступа…</p>
      </main>
    );
  }

  if (authError) {
    return (
      <main className="session-screen">
        <h1>Контур · Панель сотрудников</h1>
        <p role="alert" style={{ color: 'var(--red, #922b4e)' }}>{authError}</p>
      </main>
    );
  }

  // 2FA Setup / Verification screen
  if (twoFaNeeded) {
    return (
      <main className="session-screen" style={{ maxWidth: '440px', margin: '40px auto', padding: '24px' }}>
        <h2>Двухфакторная аутентификация (2FA)</h2>
        <p className="muted">
          Для доступа к модерации и административным функциям обязательно подтверждение 2FA.
        </p>

        {twoFaError && <p role="alert" style={{ color: 'var(--red)' }}>{twoFaError}</p>}

        {!twoFaSetup ? (
          <div>
            <form onSubmit={handleVerifyTwoFa}>
              <label htmlFor="totp-code">Введите 6-значный код из Authenticator</label>
              <input
                id="totp-code"
                value={twoFaCode}
                onChange={(e) => setTwoFaCode(e.target.value)}
                placeholder="123456"
                maxLength={8}
                required
              />
              <button type="submit" style={{ marginTop: '12px' }}>
                Подтвердить вход
              </button>
            </form>

            <div style={{ marginTop: '20px', borderTop: '1px solid var(--line)', paddingTop: '16px' }}>
              <p className="muted" style={{ fontSize: '13px' }}>Ещё не настроили 2FA для этого аккаунта?</p>
              <button
                type="button"
                onClick={startTwoFaSetup}
                style={{ background: 'var(--surface)', color: 'var(--ink)' }}
              >
                Настроить приложение Authenticator
              </button>
            </div>
          </div>
        ) : (
          <div>
            <h4>Настройка TOTP Authenticator</h4>
            <p className="muted" style={{ fontSize: '13px' }}>
              Добавьте ключ в Google Authenticator, Яндекс.Ключ или 1Password:
            </p>
            <div style={{ background: 'var(--surface)', padding: '12px', borderRadius: '10px', wordBreak: 'break-all', fontFamily: 'monospace' }}>
              {twoFaSetup.secret}
            </div>

            <h5 style={{ marginTop: '14px' }}>Резервные коды восстановления (сохраните):</h5>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '12px', fontFamily: 'monospace' }}>
              {twoFaSetup.recovery_codes.map((c, i) => (
                <div key={i} style={{ background: 'var(--surface)', padding: '4px', textAlign: 'center' }}>{c}</div>
              ))}
            </div>

            <form onSubmit={handleVerifyTwoFa} style={{ marginTop: '16px' }}>
              <label htmlFor="confirm-code">Код проверки из приложения</label>
              <input
                id="confirm-code"
                value={twoFaCode}
                onChange={(e) => setTwoFaCode(e.target.value)}
                placeholder="123456"
                required
              />
              <button type="submit" style={{ marginTop: '10px' }}>
                Активировать 2FA и войти
              </button>
            </form>
          </div>
        )}
      </main>
    );
  }

  return (
    <div style={{ maxWidth: '900px', margin: 'auto', padding: '16px 20px 80px 20px' }}>
      {/* Header */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--line)', paddingBottom: '14px', marginBottom: '16px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '22px' }}>Контур · Модерация</h1>
          <small className="muted">Сотрудник: @{currentUser?.username || currentUser?.telegram_id} ({currentUser?.role})</small>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <span style={{ fontSize: '12px', background: 'var(--green, #276135)', color: '#fff', padding: '4px 8px', borderRadius: '8px', alignSelf: 'center' }}>
            2FA Активен
          </span>
        </div>
      </header>

      {toast && (
        <div style={{ background: 'var(--primary)', color: 'var(--on-primary)', padding: '10px 14px', borderRadius: '12px', margin: '12px 0' }}>
          {toast}
        </div>
      )}

      {/* Stats Cards */}
      {stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '10px', marginBottom: '20px' }}>
          <div style={{ background: 'var(--surface)', padding: '12px', borderRadius: '14px', textAlign: 'center' }}>
            <div style={{ fontSize: '22px', fontWeight: 800, color: 'var(--primary)' }}>{stats.pending_cases_count}</div>
            <small className="muted">На рассмотрении</small>
          </div>
          <div style={{ background: 'var(--surface)', padding: '12px', borderRadius: '14px', textAlign: 'center' }}>
            <div style={{ fontSize: '22px', fontWeight: 800, color: 'var(--amber, #d97706)' }}>{stats.pending_appeals_count}</div>
            <small className="muted">Апелляции</small>
          </div>
          <div style={{ background: 'var(--surface)', padding: '12px', borderRadius: '14px', textAlign: 'center' }}>
            <div style={{ fontSize: '22px', fontWeight: 800, color: 'var(--green, #276135)' }}>{stats.open_support_count}</div>
            <small className="muted">Поддержка</small>
          </div>
          <div style={{ background: 'var(--surface)', padding: '12px', borderRadius: '14px', textAlign: 'center' }}>
            <div style={{ fontSize: '22px', fontWeight: 800 }}>{stats.total_users_count}</div>
            <small className="muted">Пользователи</small>
          </div>
        </div>
      )}

      {/* Tabs */}
      <nav style={{ display: 'flex', gap: '6px', borderBottom: '1px solid var(--line)', paddingBottom: '10px', marginBottom: '16px', overflowX: 'auto' }}>
        {[
          { key: 'cases', label: `Обращения (${cases.length})` },
          { key: 'appeals', label: `Апелляции (${appeals.length})` },
          { key: 'support', label: `Поддержка (${supportTickets.length})` },
          { key: 'users', label: 'Пользователи' },
          { key: 'audit', label: 'Аудит' },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key as any)}
            style={{
              background: tab === t.key ? 'var(--primary)' : 'var(--surface)',
              color: tab === t.key ? 'var(--on-primary)' : 'var(--ink)',
              fontSize: '13px',
              padding: '8px 14px',
              minHeight: '36px',
              whiteSpace: 'nowrap',
            }}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {/* TAB: CASES QUEUE */}
      {tab === 'cases' && (
        <section>
          {cases.length === 0 ? (
            <p className="muted">Очередь обращений пуста. Все поступившие обращения рассмотрены.</p>
          ) : (
            cases.map((c) => (
              <article key={c.id} style={{ background: 'var(--surface)', padding: '16px', borderRadius: '16px', margin: '12px 0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <strong>Обращение #{c.id} · {c.experience_type === 'POSITIVE' ? '🟢 Положительный' : '🔴 Отрицательный'}</strong>
                  <span style={{ fontSize: '12px', background: 'var(--line)', padding: '3px 8px', borderRadius: '6px' }}>{c.status}</span>
                </div>
                <div style={{ fontSize: '13px', color: 'var(--muted)', margin: '6px 0' }}>
                  Контакт: @{c.target_username || 'не указан'} · Категория: {c.category} · Версия: v{c.current_version}
                </div>
                <p className="long-text" style={{ margin: '8px 0' }}>{c.description}</p>
                {c.agreed_terms && <p style={{ fontSize: '13px' }}><strong>Условия:</strong> {c.agreed_terms}</p>}
                {c.result_description && <p style={{ fontSize: '13px' }}><strong>Результат:</strong> {c.result_description}</p>}

                <div style={{ marginTop: '12px' }}>
                  <button
                    onClick={() => { setSelectedCase(c); setDecisionReason(''); }}
                    style={{ fontSize: '13px', padding: '6px 14px', minHeight: '34px' }}
                  >
                    Принять решение по обращению
                  </button>
                </div>
              </article>
            ))
          )}
        </section>
      )}

      {/* TAB: APPEALS */}
      {tab === 'appeals' && (
        <section>
          {appeals.length === 0 ? (
            <p className="muted">Нет открытых апелляций.</p>
          ) : (
            appeals.map((a) => (
              <article key={a.id} style={{ background: 'var(--surface)', padding: '16px', borderRadius: '16px', margin: '12px 0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <strong>Апелляция #{a.id} (Обращение #{a.case_id})</strong>
                  <span style={{ fontSize: '12px', background: 'var(--line)', padding: '3px 8px', borderRadius: '6px' }}>{a.status}</span>
                </div>
                <p style={{ margin: '8px 0' }}><strong>Основание заявителя:</strong> {a.reason}</p>
                {['SENIOR_MODERATOR', 'ADMIN', 'OWNER'].includes(currentUser?.role || '') && (
                  <button
                    onClick={() => { setSelectedAppeal(a); setAppealNote(''); }}
                    style={{ fontSize: '13px', padding: '6px 14px', minHeight: '34px' }}
                  >
                    Вынести решение по апелляции
                  </button>
                )}
              </article>
            ))
          )}
        </section>
      )}

      {/* TAB: SUPPORT */}
      {tab === 'support' && (
        <section>
          {supportTickets.length === 0 ? (
            <p className="muted">Нет открытых запросов поддержки.</p>
          ) : (
            supportTickets.map((t) => (
              <article key={t.id} style={{ background: 'var(--surface)', padding: '16px', borderRadius: '16px', margin: '12px 0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <strong>#{t.id} {t.subject}</strong>
                  <span style={{ fontSize: '12px', background: t.status === 'OPEN' ? 'var(--amber)' : 'var(--line)', padding: '3px 8px', borderRadius: '6px' }}>
                    {t.status}
                  </span>
                </div>
                <p style={{ margin: '8px 0' }}>{t.message}</p>
                {t.answer && (
                  <div style={{ background: 'var(--line)', padding: '8px 12px', borderRadius: '8px', margin: '8px 0', fontSize: '13px' }}>
                    <strong>Ответ модератора:</strong> {t.answer}
                  </div>
                )}
                <button
                  onClick={() => { setAnsweringTicket(t); setSupportAnswer(t.answer || ''); }}
                  style={{ fontSize: '13px', padding: '6px 14px', minHeight: '34px', marginTop: '6px' }}
                >
                  {t.answer ? 'Изменить ответ' : 'Ответить пользователю'}
                </button>
              </article>
            ))
          )}
        </section>
      )}

      {/* TAB: USERS & ROLES */}
      {tab === 'users' && (
        <section>
          <div style={{ display: 'flex', gap: '8px', marginBottom: '14px' }}>
            <input
              value={userSearch}
              onChange={(e) => setUserSearch(e.target.value)}
              placeholder="Поиск по username или ID"
            />
            <button onClick={() => loadTabData('users')} style={{ width: 'auto', whiteSpace: 'nowrap' }}>
              Найти
            </button>
          </div>

          {users.map((u) => (
            <article key={u.id} style={{ background: 'var(--surface)', padding: '12px 16px', borderRadius: '12px', margin: '8px 0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong>{u.username ? `@${u.username}` : `ID ${u.telegram_id}`}</strong>
                <span style={{ marginLeft: '10px', fontSize: '12px', background: 'var(--line)', padding: '2px 8px', borderRadius: '6px' }}>{u.role}</span>
              </div>
              {['ADMIN', 'OWNER'].includes(currentUser?.role || '') && u.role !== 'OWNER' && (
                <button
                  onClick={() => { setEditingUser(u); setNewRole(u.role); setRoleReason(''); }}
                  style={{ fontSize: '12px', padding: '4px 10px', minHeight: '30px' }}
                >
                  Изменить роль
                </button>
              )}
            </article>
          ))}
        </section>
      )}

      {/* TAB: AUDIT LOG */}
      {tab === 'audit' && (
        <section>
          {auditLogs.map((log) => (
            <article key={log.id} style={{ background: 'var(--surface)', padding: '10px 14px', borderRadius: '10px', margin: '6px 0', fontSize: '13px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <strong>{log.action} · {log.object_type} #{log.object_id}</strong>
                <small className="muted">{new Date(log.created_at).toLocaleString()}</small>
              </div>
              {log.details && <code style={{ display: 'block', margin: '4px 0', color: 'var(--muted)', fontSize: '12px' }}>{log.details}</code>}
            </article>
          ))}
        </section>
      )}

      {/* Modal: Case Decision */}
      {selectedCase && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'grid', placeItems: 'center', zIndex: 100, padding: '16px' }}>
          <article style={{ background: 'var(--surface)', maxWidth: '480px', width: '100%', borderRadius: '20px', padding: '20px' }}>
            <h3>Решение по обращению #{selectedCase.id}</h3>
            <form onSubmit={submitCaseDecision}>
              <label>Решение</label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '6px', margin: '6px 0 12px 0' }}>
                <button
                  type="button"
                  onClick={() => setDecisionType('APPROVE')}
                  style={{ background: decisionType === 'APPROVE' ? 'var(--green)' : 'var(--line)', color: decisionType === 'APPROVE' ? '#fff' : 'var(--ink)' }}
                >
                  Одобрить
                </button>
                <button
                  type="button"
                  onClick={() => setDecisionType('REJECT')}
                  style={{ background: decisionType === 'REJECT' ? 'var(--red)' : 'var(--line)', color: decisionType === 'REJECT' ? '#fff' : 'var(--ink)' }}
                >
                  Отклонить
                </button>
                <button
                  type="button"
                  onClick={() => setDecisionType('REQUEST_INFO')}
                  style={{ background: decisionType === 'REQUEST_INFO' ? 'var(--primary)' : 'var(--line)', color: decisionType === 'REQUEST_INFO' ? '#fff' : 'var(--ink)' }}
                >
                  Запросить
                </button>
              </div>

              <label htmlFor="reason">Обоснование решения (минимум 5 символов)</label>
              <textarea
                id="reason"
                value={decisionReason}
                onChange={(e) => setDecisionReason(e.target.value)}
                placeholder="Причина решения, ссылки на правила или запрос уточнений…"
                style={{ width: '100%', minHeight: '90px', borderRadius: '12px', border: '1px solid var(--line)', padding: '10px', background: 'var(--surface)', color: 'var(--ink)' }}
                required
                minLength={5}
              />

              <div style={{ display: 'flex', gap: '8px', marginTop: '14px' }}>
                <button type="button" onClick={() => setSelectedCase(null)} style={{ background: 'var(--line)', color: 'var(--ink)' }}>
                  Отмена
                </button>
                <button type="submit" disabled={decisionReason.trim().length < 5}>
                  Сохранить решение
                </button>
              </div>
            </form>
          </article>
        </div>
      )}

      {/* Modal: Appeal Decision */}
      {selectedAppeal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'grid', placeItems: 'center', zIndex: 100, padding: '16px' }}>
          <article style={{ background: 'var(--surface)', maxWidth: '480px', width: '100%', borderRadius: '20px', padding: '20px' }}>
            <h3>Решение по апелляции #{selectedAppeal.id}</h3>
            <form onSubmit={submitAppealDecision}>
              <label>Исход апелляции</label>
              <select value={appealDecisionStatus} onChange={(e) => setAppealDecisionStatus(e.target.value as any)}>
                <option value="UPHELD">Оставить в силе (UPHELD)</option>
                <option value="OVERTURNED">Отменить решение модератора (OVERTURNED)</option>
                <option value="REJECTED">Отклонить апелляцию (REJECTED)</option>
              </select>

              <label htmlFor="appeal-note" style={{ marginTop: '10px' }}>Обоснование старшего модератора</label>
              <textarea
                id="appeal-note"
                value={appealNote}
                onChange={(e) => setAppealNote(e.target.value)}
                placeholder="Основание решения по апелляции…"
                style={{ width: '100%', minHeight: '90px', borderRadius: '12px', border: '1px solid var(--line)', padding: '10px', background: 'var(--surface)', color: 'var(--ink)' }}
                required
                minLength={5}
              />

              <div style={{ display: 'flex', gap: '8px', marginTop: '14px' }}>
                <button type="button" onClick={() => setSelectedAppeal(null)} style={{ background: 'var(--line)', color: 'var(--ink)' }}>
                  Отмена
                </button>
                <button type="submit" disabled={appealNote.trim().length < 5}>
                  Вынести решение
                </button>
              </div>
            </form>
          </article>
        </div>
      )}

      {/* Modal: Support Answer */}
      {answeringTicket && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'grid', placeItems: 'center', zIndex: 100, padding: '16px' }}>
          <article style={{ background: 'var(--surface)', maxWidth: '480px', width: '100%', borderRadius: '20px', padding: '20px' }}>
            <h3>Ответ на обращение #{answeringTicket.id}</h3>
            <p className="muted">{answeringTicket.message}</p>
            <form onSubmit={submitSupportAnswer}>
              <label htmlFor="ans-text">Ответ сотрудника</label>
              <textarea
                id="ans-text"
                value={supportAnswer}
                onChange={(e) => setSupportAnswer(e.target.value)}
                placeholder="Текст ответа пользователю…"
                style={{ width: '100%', minHeight: '100px', borderRadius: '12px', border: '1px solid var(--line)', padding: '10px', background: 'var(--surface)', color: 'var(--ink)' }}
                required
                minLength={5}
              />
              <div style={{ display: 'flex', gap: '8px', marginTop: '14px' }}>
                <button type="button" onClick={() => setAnsweringTicket(null)} style={{ background: 'var(--line)', color: 'var(--ink)' }}>
                  Отмена
                </button>
                <button type="submit" disabled={supportAnswer.trim().length < 5}>
                  Отправить ответ
                </button>
              </div>
            </form>
          </article>
        </div>
      )}

      {/* Modal: Change User Role */}
      {editingUser && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'grid', placeItems: 'center', zIndex: 100, padding: '16px' }}>
          <article style={{ background: 'var(--surface)', maxWidth: '420px', width: '100%', borderRadius: '20px', padding: '20px' }}>
            <h3>Назначить роль: @{editingUser.username || editingUser.telegram_id}</h3>
            <form onSubmit={submitRoleChange}>
              <label>Новая роль</label>
              <select value={newRole} onChange={(e) => setNewRole(e.target.value)}>
                <option value="USER">USER</option>
                <option value="MODERATOR">MODERATOR</option>
                <option value="SENIOR_MODERATOR">SENIOR_MODERATOR</option>
                <option value="ADMIN">ADMIN</option>
              </select>

              <label htmlFor="role-reason" style={{ marginTop: '10px' }}>Причина изменения (в журнал аудита)</label>
              <input
                id="role-reason"
                value={roleReason}
                onChange={(e) => setRoleReason(e.target.value)}
                placeholder="Приказ / основание"
                required
                minLength={5}
              />

              <div style={{ display: 'flex', gap: '8px', marginTop: '14px' }}>
                <button type="button" onClick={() => setEditingUser(null)} style={{ background: 'var(--line)', color: 'var(--ink)' }}>
                  Отмена
                </button>
                <button type="submit" disabled={roleReason.trim().length < 5}>
                  Сохранить роль
                </button>
              </div>
            </form>
          </article>
        </div>
      )}
    </div>
  );
}
