import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { request } from '../api';
import type { SubjectSearchResponse, SubjectSearchItem, SubjectCardDetailed, SavedContact } from '../api';

export default function Check() {
  const [input, setInput] = useState('');
  const [query, setQuery] = useState('');
  const [selectedSubjectId, setSelectedSubjectId] = useState<number | null>(null);
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [saveNote, setSaveNote] = useState('');
  const [saveName, setSaveName] = useState('');
  const [toastMsg, setToastMsg] = useState('');

  const cache = useQueryClient();

  // Search subjects
  const searchResult = useQuery({
    queryKey: ['subjects-search', query],
    queryFn: ({ signal }) =>
      request<SubjectSearchResponse>(`/subjects/search?q=${encodeURIComponent(query)}`, { signal }),
    enabled: Boolean(query),
    retry: false,
  });

  // Detailed subject card
  const cardResult = useQuery({
    queryKey: ['subject-card', selectedSubjectId],
    queryFn: ({ signal }) =>
      request<SubjectCardDetailed>(`/subjects/${selectedSubjectId}/card`, { signal }),
    enabled: selectedSubjectId !== null,
    retry: false,
  });

  // Subscribe / Unsubscribe
  const toggleSubscribe = useMutation({
    mutationFn: async ({ id, isSubscribed }: { id: number; isSubscribed: boolean }) => {
      if (isSubscribed) {
        await request(`/subjects/${id}/subscribe`, { method: 'DELETE' });
      } else {
        await request(`/subjects/${id}/subscribe`, { method: 'POST' });
      }
    },
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ['subject-card', selectedSubjectId] });
      setToastMsg('Подписка обновлена');
      setTimeout(() => setToastMsg(''), 3000);
    },
  });

  // F01: Save contact privately
  const saveContact = useMutation({
    mutationFn: () =>
      request<SavedContact>('/contacts', {
        method: 'POST',
        body: JSON.stringify({
          raw_input: query || input,
          display_name: saveName.trim() || undefined,
          note: saveNote.trim() || undefined,
        }),
      }),
    onSuccess: () => {
      setSaveModalOpen(false);
      setSaveNote('');
      setSaveName('');
      setToastMsg('Контакт сохранён в личный список');
      setTimeout(() => setToastMsg(''), 3000);
      void cache.invalidateQueries({ queryKey: ['saved-contacts'] });
    },
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = input.trim();
    if (clean) {
      setSelectedSubjectId(null);
      setQuery(clean);
    }
  };

  return (
    <section>
      <div className="hero">
        <h2>Проверка контакта</h2>
        <p className="muted">
          Найдите контакт, проверьте опубликованную историю взаимодействий или сохраните приватную заметку.
        </p>
      </div>

      <form onSubmit={handleSearch}>
        <label htmlFor="search-input">Username, ссылка или ID в Telegram</label>
        <div style={{ display: 'flex', gap: '8px' }}>
          <input
            id="search-input"
            value={input}
            maxLength={256}
            onChange={(e) => setInput(e.target.value)}
            placeholder="@username или https://t.me/username"
          />
          <button type="submit" disabled={!input.trim() || searchResult.isFetching} style={{ width: 'auto', whiteSpace: 'nowrap' }}>
            Проверить
          </button>
        </div>
      </form>

      {toastMsg && <div role="status" style={{ background: 'var(--primary)', color: 'var(--on-primary)', padding: '10px 14px', borderRadius: '12px', margin: '12px 0' }}>{toastMsg}</div>}

      {/* Search results */}
      {searchResult.isFetching && <p role="status">Поиск…</p>}
      {searchResult.error && <p role="alert">{(searchResult.error as any).message}</p>}

      {searchResult.data && (
        <div style={{ marginTop: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3>Найдено записей: {searchResult.data.total}</h3>
            {/* F01: Add unknown contact button */}
            <button
              onClick={() => {
                setSaveName(input.replace(/^@/, ''));
                setSaveModalOpen(true);
              }}
              style={{ fontSize: '13px', padding: '6px 12px', minHeight: '36px' }}
            >
              + Сохранить для себя
            </button>
          </div>

          {searchResult.data.items.length === 0 && (
            <article style={{ textAlign: 'center', padding: '24px 16px' }}>
              <p>По запросу «{query}» совпадений среди публичных профилей не найдено.</p>
              <p className="muted">
                Вы можете сохранить этот контакт в личный список и добавить собственную заметку.
              </p>
            </article>
          )}

          {searchResult.data.items.map((item: SubjectSearchItem) => (
            <article
              key={item.id}
              className="catalog-card"
              style={{ cursor: 'pointer', border: selectedSubjectId === item.id ? '2px solid var(--primary)' : '1px solid var(--line)' }}
              onClick={() => setSelectedSubjectId(item.id)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <strong>{item.first_name || item.username || `ID ${item.id}`}</strong>
                  {item.is_verified && <span style={{ marginLeft: '6px', color: 'var(--primary)' }}>✓ Проверен</span>}
                  <small>{item.username ? `@${item.username}` : 'Username скрыт'}</small>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ color: 'var(--green, #276135)', fontWeight: 650 }}>+{item.reputation.positive_count}</span>
                  {' / '}
                  <span style={{ color: 'var(--red, #922b4e)', fontWeight: 650 }}>−{item.reputation.negative_count}</span>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      {/* Selected Subject Detailed Card */}
      {selectedSubjectId !== null && cardResult.data && (
        <article style={{ marginTop: '20px', border: '2px solid var(--primary)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <h3>
                {cardResult.data.first_name || cardResult.data.username || `Субъект #${cardResult.data.id}`}
                {cardResult.data.is_verified && <span style={{ color: 'var(--primary)', marginLeft: '6px' }}>✓</span>}
              </h3>
              <p className="muted">{cardResult.data.username ? `@${cardResult.data.username}` : 'Username не привязан'}</p>
            </div>
            <button
              onClick={() =>
                toggleSubscribe.mutate({
                  id: cardResult.data.id,
                  isSubscribed: cardResult.data.is_subscribed,
                })
              }
              style={{ width: 'auto', fontSize: '13px', padding: '6px 12px', minHeight: '36px' }}
            >
              {cardResult.data.is_subscribed ? '🔔 Вы подписаны' : '🔕 Подписаться'}
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', margin: '14px 0' }}>
            <div style={{ background: 'var(--surface)', padding: '12px', borderRadius: '12px', textAlign: 'center' }}>
              <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--green, #276135)' }}>
                +{cardResult.data.reputation.positive_count}
              </div>
              <small>Положительный опыт</small>
            </div>
            <div style={{ background: 'var(--surface)', padding: '12px', borderRadius: '12px', textAlign: 'center' }}>
              <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--red, #922b4e)' }}>
                −{cardResult.data.reputation.negative_count}
              </div>
              <small>Отрицательный опыт</small>
            </div>
          </div>

          {/* Observations history */}
          {cardResult.data.observations.length > 0 && (
            <div style={{ margin: '14px 0' }}>
              <h4>История наблюдений username</h4>
              {cardResult.data.observations.map((obs) => (
                <div key={obs.id} style={{ fontSize: '13px', color: 'var(--muted)', margin: '4px 0' }}>
                  @{obs.raw_username} · {new Date(obs.observed_at).toLocaleDateString()}
                </div>
              ))}
            </div>
          )}

          {/* Published reviews */}
          <div style={{ margin: '14px 0' }}>
            <h4>Опубликованный опыт ({cardResult.data.published_reviews.length})</h4>
            {cardResult.data.published_reviews.length === 0 ? (
              <p className="muted">Нет опубликованных отзывов.</p>
            ) : (
              cardResult.data.published_reviews.map((rev) => (
                <div key={rev.id} style={{ borderTop: '1px solid var(--line)', paddingTop: '10px', marginTop: '10px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontWeight: 650, color: rev.score_type === 'POSITIVE' ? 'var(--green)' : 'var(--red)' }}>
                      {rev.score_type === 'POSITIVE' ? '+ Положительный' : '− Отрицательный'}
                    </span>
                    <small className="muted">{new Date(rev.created_at).toLocaleDateString()}</small>
                  </div>
                  <p style={{ margin: '6px 0' }}>{rev.result_description || rev.outcome_note || 'Без описания'}</p>
                  <small className="muted">Категория: {rev.category} · Автор: {rev.author_pseudonym}</small>
                </div>
              ))
            )}
          </div>

          {/* Private user note */}
          {cardResult.data.private_note && (
            <div style={{ background: 'var(--surface)', padding: '10px', borderRadius: '8px', marginTop: '12px' }}>
              <strong>Ваша личная заметка:</strong>
              <p style={{ margin: '4px 0' }}>{cardResult.data.private_note}</p>
            </div>
          )}

          <button onClick={() => setSelectedSubjectId(null)} style={{ marginTop: '12px' }}>
            Скрыть карточку
          </button>
        </article>
      )}

      {/* Modal: Save contact privately (F01) */}
      {saveModalOpen && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'grid', placeItems: 'center', zIndex: 100, padding: '16px' }}>
          <article style={{ background: 'var(--surface)', maxWidth: '420px', width: '100%', borderRadius: '20px', padding: '20px' }}>
            <h3>Сохранить контакт</h3>
            <p className="muted">Запись будет видна только вам в разделе «Каталоги».</p>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                saveContact.mutate();
              }}
            >
              <label htmlFor="save-name">Отображаемое имя (необязательно)</label>
              <input id="save-name" value={saveName} onChange={(e) => setSaveName(e.target.value)} placeholder="Например: Иван Дизайнер" />

              <label htmlFor="save-note">Личная заметка</label>
              <textarea
                id="save-note"
                value={saveNote}
                onChange={(e) => setSaveNote(e.target.value)}
                placeholder="Условия, договорённости, сроки…"
                style={{ width: '100%', minHeight: '80px', borderRadius: '12px', border: '1px solid var(--line)', padding: '10px', background: 'var(--surface)', color: 'var(--ink)' }}
              />

              <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                <button type="button" onClick={() => setSaveModalOpen(false)} style={{ background: 'var(--line)', color: 'var(--ink)' }}>
                  Отмена
                </button>
                <button type="submit" disabled={saveContact.isPending}>
                  {saveContact.isPending ? 'Сохранение…' : 'Сохранить'}
                </button>
              </div>
            </form>
          </article>
        </div>
      )}
    </section>
  );
}
