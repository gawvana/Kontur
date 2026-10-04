import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { request } from '../api';
import type { Case } from '../api';

export default function Cases() {
  const [offset, setOffset] = useState(0);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [formStep, setFormStep] = useState(1);
  const [targetUsername, setTargetUsername] = useState('');
  const [experienceType, setExperienceType] = useState<'POSITIVE' | 'NEGATIVE'>('NEGATIVE');
  const [category, setCategory] = useState('SERVICE');
  const [description, setDescription] = useState('');
  const [agreedTerms, setAgreedTerms] = useState('');
  const [authorActions, setAuthorActions] = useState('');
  const [resultDescription, setResultDescription] = useState('');
  const [amount, setAmount] = useState('');
  const [currency, setCurrency] = useState('RUB');
  const [toast, setToast] = useState('');

  // Appeal modal state
  const [appealCaseId, setAppealCaseId] = useState<number | null>(null);
  const [appealReason, setAppealReason] = useState('');

  const cache = useQueryClient();

  const casesQuery = useQuery({
    queryKey: ['my-cases', offset],
    queryFn: ({ signal }) => request<Case[]>(`/cases/my?limit=50&offset=${offset}`, { signal }),
    retry: false,
  });

  // F02: Multi-step case submission
  const submitCase = useMutation({
    mutationFn: () => {
      const idempotencyKey = crypto.randomUUID();
      return request<Case>('/cases', {
        method: 'POST',
        headers: { 'Idempotency-Key': idempotencyKey },
        body: JSON.stringify({
          target_username: targetUsername.replace(/^@/, '').trim() || undefined,
          experience_type: experienceType,
          category,
          description: description.trim(),
          agreed_terms: agreedTerms.trim() || undefined,
          author_actions: authorActions.trim() || undefined,
          result_description: resultDescription.trim() || undefined,
          amount: amount.trim() || undefined,
          currency: currency.trim() || undefined,
        }),
      });
    },
    onSuccess: () => {
      setIsFormOpen(false);
      resetForm();
      void cache.invalidateQueries({ queryKey: ['my-cases'] });
      setToast('Обращение успешно создано и отправлено на рассмотрение');
      setTimeout(() => setToast(''), 4000);
    },
  });

  // Withdraw case
  const withdrawCase = useMutation({
    mutationFn: (caseId: number) => request(`/cases/${caseId}/withdraw`, { method: 'POST' }),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ['my-cases'] });
      setToast('Обращение отозвано');
      setTimeout(() => setToast(''), 3000);
    },
  });

  // Submit appeal
  const submitAppeal = useMutation({
    mutationFn: (caseId: number) =>
      request(`/cases/${caseId}/appeal`, {
        method: 'POST',
        body: JSON.stringify({ reason: appealReason.trim() }),
      }),
    onSuccess: () => {
      setAppealCaseId(null);
      setAppealReason('');
      void cache.invalidateQueries({ queryKey: ['my-cases'] });
      setToast('Апелляция подана и передана старшему модератору');
      setTimeout(() => setToast(''), 4000);
    },
  });

  const resetForm = () => {
    setFormStep(1);
    setTargetUsername('');
    setExperienceType('NEGATIVE');
    setCategory('SERVICE');
    setDescription('');
    setAgreedTerms('');
    setAuthorActions('');
    setResultDescription('');
    setAmount('');
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'APPROVED':
        return <span style={{ color: 'var(--green)', fontWeight: 650 }}>✓ Одобрено</span>;
      case 'REJECTED':
        return <span style={{ color: 'var(--red)', fontWeight: 650 }}>✕ Отклонено</span>;
      case 'SUBMITTED':
      case 'PENDING':
      case 'IN_REVIEW':
        return <span style={{ color: 'var(--amber, #d97706)', fontWeight: 650 }}>⏳ На рассмотрении</span>;
      case 'NEEDS_INFO':
        return <span style={{ color: 'var(--primary)', fontWeight: 650 }}>ℹ️ Требуются сведения</span>;
      case 'WITHDRAWN':
        return <span style={{ color: 'var(--muted)', fontWeight: 650 }}>Отзыв заявителем</span>;
      default:
        return <span>{status}</span>;
    }
  };

  return (
    <section>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>Мои обращения</h2>
        {!isFormOpen && (
          <button
            onClick={() => setIsFormOpen(true)}
            style={{ width: 'auto', padding: '8px 16px', minHeight: '38px' }}
          >
            + Описать опыт
          </button>
        )}
      </div>

      <p className="muted">
        Прозрачное рассмотрение опыта. Опубликованный опыт, ответы и решения отображаются отдельно.
      </p>

      {toast && (
        <div style={{ background: 'var(--primary)', color: 'var(--on-primary)', padding: '10px 14px', borderRadius: '12px', margin: '12px 0' }}>
          {toast}
        </div>
      )}

      {/* F02: Multi-step Case Creation Form */}
      {isFormOpen && (
        <article style={{ background: 'var(--surface)', borderRadius: '20px', padding: '20px', margin: '16px 0', border: '2px solid var(--primary)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3>Новое обращение (Шаг {formStep} из 3)</h3>
            <button
              onClick={() => setIsFormOpen(false)}
              style={{ background: 'none', border: 'none', color: 'var(--muted)', fontSize: '18px', minHeight: 'auto', cursor: 'pointer' }}
            >
              ✕
            </button>
          </div>

          {/* Stepper bar */}
          <div style={{ display: 'flex', gap: '6px', margin: '12px 0 16px 0' }}>
            <div style={{ flex: 1, height: '4px', borderRadius: '2px', background: formStep >= 1 ? 'var(--primary)' : 'var(--line)' }} />
            <div style={{ flex: 1, height: '4px', borderRadius: '2px', background: formStep >= 2 ? 'var(--primary)' : 'var(--line)' }} />
            <div style={{ flex: 1, height: '4px', borderRadius: '2px', background: formStep >= 3 ? 'var(--primary)' : 'var(--line)' }} />
          </div>

          {formStep === 1 && (
            <div>
              <label htmlFor="target-user">Username контакта в Telegram</label>
              <input
                id="target-user"
                value={targetUsername}
                onChange={(e) => setTargetUsername(e.target.value)}
                placeholder="@username контакта"
                required
              />

              <label>Тип опыта</label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', margin: '8px 0 12px 0' }}>
                <button
                  type="button"
                  onClick={() => setExperienceType('POSITIVE')}
                  style={{
                    background: experienceType === 'POSITIVE' ? 'var(--green, #276135)' : 'var(--surface)',
                    color: experienceType === 'POSITIVE' ? '#fff' : 'var(--ink)',
                  }}
                >
                  + Положительный
                </button>
                <button
                  type="button"
                  onClick={() => setExperienceType('NEGATIVE')}
                  style={{
                    background: experienceType === 'NEGATIVE' ? 'var(--red, #922b4e)' : 'var(--surface)',
                    color: experienceType === 'NEGATIVE' ? '#fff' : 'var(--ink)',
                  }}
                >
                  − Отрицательный
                </button>
              </div>

              <label htmlFor="case-category">Категория</label>
              <select id="case-category" value={category} onChange={(e) => setCategory(e.target.value)}>
                <option value="SERVICE">Услуги и разработка</option>
                <option value="GOODS">Товары</option>
                <option value="DIGITAL">Цифровые товары</option>
                <option value="EXCHANGE">Обмен</option>
                <option value="OTHER">Другое</option>
              </select>

              <label htmlFor="case-desc">Что произошло? (минимум 20 символов)</label>
              <textarea
                id="case-desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Опишите факт взаимодействия, дату и основные обстоятельства…"
                style={{ width: '100%', minHeight: '100px', borderRadius: '12px', border: '1px solid var(--line)', padding: '10px', background: 'var(--surface)', color: 'var(--ink)' }}
                required
              />

              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '14px' }}>
                <button
                  type="button"
                  disabled={description.trim().length < 20}
                  onClick={() => setFormStep(2)}
                >
                  Далее: Детали взаимодействия →
                </button>
              </div>
            </div>
          )}

          {formStep === 2 && (
            <div>
              <label htmlFor="terms">Что согласовали?</label>
              <textarea
                id="terms"
                value={agreedTerms}
                onChange={(e) => setAgreedTerms(e.target.value)}
                placeholder="Сроки, стоимость, техническое задание…"
                style={{ width: '100%', minHeight: '70px', borderRadius: '12px', border: '1px solid var(--line)', padding: '10px', background: 'var(--surface)', color: 'var(--ink)' }}
              />

              <label htmlFor="actions">Ваши действия</label>
              <textarea
                id="actions"
                value={authorActions}
                onChange={(e) => setAuthorActions(e.target.value)}
                placeholder="Внесена предоплата, переданы исходники…"
                style={{ width: '100%', minHeight: '70px', borderRadius: '12px', border: '1px solid var(--line)', padding: '10px', background: 'var(--surface)', color: 'var(--ink)' }}
              />

              <label htmlFor="result-desc">Фактический результат</label>
              <textarea
                id="result-desc"
                value={resultDescription}
                onChange={(e) => setResultDescription(e.target.value)}
                placeholder="Что было получено или что пошло не так…"
                style={{ width: '100%', minHeight: '70px', borderRadius: '12px', border: '1px solid var(--line)', padding: '10px', background: 'var(--surface)', color: 'var(--ink)' }}
              />

              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '8px' }}>
                <div>
                  <label htmlFor="amount">Сумма сделки (необязательно)</label>
                  <input id="amount" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="5000" />
                </div>
                <div>
                  <label htmlFor="currency">Валюта</label>
                  <select id="currency" value={currency} onChange={(e) => setCurrency(e.target.value)}>
                    <option value="RUB">RUB</option>
                    <option value="USDT">USDT</option>
                    <option value="TON">TON</option>
                    <option value="USD">USD</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '14px' }}>
                <button type="button" onClick={() => setFormStep(1)} style={{ background: 'var(--line)', color: 'var(--ink)' }}>
                  ← Назад
                </button>
                <button type="button" onClick={() => setFormStep(3)}>
                  Далее: Проверка и отправка →
                </button>
              </div>
            </div>
          )}

          {formStep === 3 && (
            <div>
              <h4>Сводка обращения</h4>
              <p><strong>Контакт:</strong> {targetUsername || 'Не указан'}</p>
              <p><strong>Тип:</strong> {experienceType === 'POSITIVE' ? 'Положительный опыт' : 'Отрицательный опыт'}</p>
              <p><strong>Описание:</strong> {description}</p>
              {agreedTerms && <p><strong>Условия:</strong> {agreedTerms}</p>}
              {resultDescription && <p><strong>Результат:</strong> {resultDescription}</p>}
              {amount && <p><strong>Сумма:</strong> {amount} {currency}</p>}

              <p className="muted" style={{ fontSize: '13px' }}>
                После отправки обращение поступит на модерацию. При необходимости вы сможете дополнить его или отозвать.
              </p>

              {submitCase.error && <p role="alert">{(submitCase.error as any).message}</p>}

              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '16px' }}>
                <button type="button" onClick={() => setFormStep(2)} style={{ background: 'var(--line)', color: 'var(--ink)' }}>
                  ← Назад
                </button>
                <button
                  type="button"
                  disabled={submitCase.isPending}
                  onClick={() => submitCase.mutate()}
                >
                  {submitCase.isPending ? 'Отправка…' : 'Отправить обращение'}
                </button>
              </div>
            </div>
          )}
        </article>
      )}

      {/* Cases List */}
      {casesQuery.isLoading && <p role="status">Загрузка…</p>}
      {casesQuery.error && <p role="alert">{(casesQuery.error as any).message}</p>}

      {casesQuery.data?.length === 0 && !casesQuery.isLoading && (
        <article style={{ textAlign: 'center', padding: '24px' }}>
          <p>У вас пока нет поданных обращений.</p>
        </article>
      )}

      {casesQuery.data?.map((c) => (
        <article key={c.id}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3>Обращение #{c.id}</h3>
            {getStatusBadge(c.status)}
          </div>
          <p className="long-text" style={{ margin: '10px 0' }}>{c.description}</p>
          {c.outcome_note && (
            <div style={{ background: 'var(--surface)', padding: '10px', borderRadius: '10px', margin: '8px 0' }}>
              <strong>Решение:</strong> {c.outcome_note}
            </div>
          )}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px' }}>
            <small className="muted">{new Date(c.created_at).toLocaleDateString()}</small>
            <div style={{ display: 'flex', gap: '8px' }}>
              {/* Withdraw button for pending cases */}
              {['PENDING', 'SUBMITTED', 'DRAFT'].includes(c.status) && (
                <button
                  onClick={() => withdrawCase.mutate(c.id)}
                  style={{ fontSize: '12px', padding: '4px 10px', minHeight: '30px', background: 'var(--line)', color: 'var(--ink)' }}
                >
                  Отозвать
                </button>
              )}
              {/* Appeal button for decided cases */}
              {['APPROVED', 'REJECTED', 'RESOLVED'].includes(c.status) && (
                <button
                  onClick={() => setAppealCaseId(c.id)}
                  style={{ fontSize: '12px', padding: '4px 10px', minHeight: '30px' }}
                >
                  Подать апелляцию
                </button>
              )}
            </div>
          </div>
        </article>
      ))}

      {/* Pagination */}
      <div className="pagination">
        <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 50))}>
          ← Назад
        </button>
        <button disabled={casesQuery.data?.length !== 50} onClick={() => setOffset(offset + 50)}>
          Далее →
        </button>
      </div>

      {/* Appeal Modal */}
      {appealCaseId !== null && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'grid', placeItems: 'center', zIndex: 100, padding: '16px' }}>
          <article style={{ background: 'var(--surface)', maxWidth: '420px', width: '100%', borderRadius: '20px', padding: '20px' }}>
            <h3>Апелляция по обращению #{appealCaseId}</h3>
            <p className="muted">Опишите, с чем вы не согласны в решении модератора (минимум 20 символов).</p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                submitAppeal.mutate(appealCaseId);
              }}
            >
              <textarea
                value={appealReason}
                onChange={(e) => setAppealReason(e.target.value)}
                placeholder="Основания для пересмотра решения…"
                style={{ width: '100%', minHeight: '120px', borderRadius: '12px', border: '1px solid var(--line)', padding: '10px', background: 'var(--surface)', color: 'var(--ink)' }}
                required
              />
              <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                <button type="button" onClick={() => setAppealCaseId(null)} style={{ background: 'var(--line)', color: 'var(--ink)' }}>
                  Отмена
                </button>
                <button type="submit" disabled={appealReason.trim().length < 20 || submitAppeal.isPending}>
                  {submitAppeal.isPending ? 'Подача…' : 'Отправить апелляцию'}
                </button>
              </div>
            </form>
          </article>
        </div>
      )}
    </section>
  );
}
