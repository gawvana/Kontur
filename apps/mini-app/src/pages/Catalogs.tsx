import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { request } from '../api';
import type { Catalog, SavedContact, SavedContactListResponse } from '../api';

export default function Catalogs() {
  const requestKey = useRef(crypto.randomUUID());
  const [name, setName] = useState('');
  const [submittedName, setSubmittedName] = useState('');
  const [selectedCatalogId, setSelectedCatalogId] = useState<number | null>(null);
  const [catalogOffset, setCatalogOffset] = useState(0);
  const [contactsOffset, setContactsOffset] = useState(0);
  const [editingContact, setEditingContact] = useState<SavedContact | null>(null);
  const [newContactInput, setNewContactInput] = useState('');
  const [newContactNote, setNewContactNote] = useState('');
  const [toast, setToast] = useState('');

  const cache = useQueryClient();

  // Catalogs query
  const catalogsQuery = useQuery({
    queryKey: ['catalogs', catalogOffset],
    queryFn: ({ signal }) =>
      request<Catalog[]>(`/catalogs?limit=50&offset=${catalogOffset}`, { signal }),
    retry: false,
  });

  // Saved contacts query (F01 & F06: private contacts with full pagination)
  const contactsQuery = useQuery({
    queryKey: ['contacts', selectedCatalogId, contactsOffset],
    queryFn: ({ signal }) => {
      const url = `/contacts?limit=50&offset=${contactsOffset}`;
      return request<SavedContactListResponse>(url, { signal });
    },
    retry: false,
  });

  // F05: Create catalog without losing typed text
  const createCatalog = useMutation({
    mutationFn: (nameToSubmit: string) =>
      request<Catalog>('/catalogs', {
        method: 'POST',
        headers: { 'Idempotency-Key': requestKey.current },
        body: JSON.stringify({ name: nameToSubmit, is_private: true }),
      }),
    onSuccess: () => {
      // F05: Only clear if user didn't type a new name while waiting
      if (name === submittedName) {
        setName('');
      }
      requestKey.current = crypto.randomUUID();
      setCatalogOffset(0);
      void cache.invalidateQueries({ queryKey: ['catalogs'] });
      setToast('Каталог создан');
      setTimeout(() => setToast(''), 3000);
    },
  });

  // F01: Add new contact directly to user's contacts
  const addContact = useMutation({
    mutationFn: () =>
      request<SavedContact>('/contacts', {
        method: 'POST',
        body: JSON.stringify({
          raw_input: newContactInput.trim(),
          note: newContactNote.trim() || undefined,
          catalog_id: selectedCatalogId || undefined,
        }),
      }),
    onSuccess: () => {
      setNewContactInput('');
      setNewContactNote('');
      setContactsOffset(0);
      void cache.invalidateQueries({ queryKey: ['contacts'] });
      setToast('Контакт добавлен');
      setTimeout(() => setToast(''), 3000);
    },
  });

  // Update existing contact note
  const updateContact = useMutation({
    mutationFn: (c: { id: number; note: string; display_name?: string }) =>
      request<SavedContact>(`/contacts/${c.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ note: c.note, display_name: c.display_name }),
      }),
    onSuccess: () => {
      setEditingContact(null);
      void cache.invalidateQueries({ queryKey: ['contacts'] });
      setToast('Заметка сохранена');
      setTimeout(() => setToast(''), 3000);
    },
  });

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = name.trim();
    if (!clean) return;
    setSubmittedName(clean);
    createCatalog.mutate(clean);
  };

  const contactsList = contactsQuery.data?.items || [];
  const contactsTotal = contactsQuery.data?.total || 0;

  return (
    <section>
      <h2>Личные каталоги и контакты</h2>
      <p className="muted">
        Контакты и заметки хранятся приватно. Они принадлежат вам и не публикуются без оснований.
      </p>

      {toast && (
        <div style={{ background: 'var(--primary)', color: 'var(--on-primary)', padding: '10px 14px', borderRadius: '12px', margin: '12px 0' }}>
          {toast}
        </div>
      )}

      {/* Form: Create catalog (with F05 fix) */}
      <form onSubmit={handleCreateSubmit} style={{ marginTop: '16px' }}>
        <label htmlFor="catalog-name">Создать новый каталог</label>
        <div style={{ display: 'flex', gap: '8px' }}>
          <input
            id="catalog-name"
            value={name}
            maxLength={128}
            onChange={(e) => {
              requestKey.current = crypto.randomUUID();
              setName(e.target.value);
            }}
            placeholder="Название каталога"
          />
          <button type="submit" disabled={!name.trim() || createCatalog.isPending} style={{ width: 'auto', whiteSpace: 'nowrap' }}>
            {createCatalog.isPending ? 'Создание…' : 'Создать'}
          </button>
        </div>
      </form>

      {createCatalog.error && <p role="alert">{(createCatalog.error as any).message}</p>}

      {/* Catalog chips / cards */}
      <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', padding: '12px 0' }}>
        <button
          onClick={() => { setSelectedCatalogId(null); setContactsOffset(0); }}
          style={{
            background: selectedCatalogId === null ? 'var(--primary)' : 'var(--surface)',
            color: selectedCatalogId === null ? 'var(--on-primary)' : 'var(--ink)',
            whiteSpace: 'nowrap',
            fontSize: '13px',
            minHeight: '36px',
            padding: '6px 14px',
          }}
        >
          Все контакты
        </button>
        {catalogsQuery.data?.map((cat) => (
          <button
            key={cat.id}
            onClick={() => { setSelectedCatalogId(cat.id); setContactsOffset(0); }}
            style={{
              background: selectedCatalogId === cat.id ? 'var(--primary)' : 'var(--surface)',
              color: selectedCatalogId === cat.id ? 'var(--on-primary)' : 'var(--ink)',
              whiteSpace: 'nowrap',
              fontSize: '13px',
              minHeight: '36px',
              padding: '6px 14px',
            }}
          >
            📁 {cat.name}
          </button>
        ))}
      </div>

      {/* F01: Add contact independently of Subject */}
      <article style={{ background: 'var(--surface)', borderRadius: '16px', padding: '16px', margin: '16px 0' }}>
        <h3 style={{ margin: '0 0 10px 0' }}>Добавить контакт</h3>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (newContactInput.trim()) addContact.mutate();
          }}
        >
          <input
            value={newContactInput}
            onChange={(e) => setNewContactInput(e.target.value)}
            placeholder="@username или ссылка Telegram"
            required
          />
          <textarea
            value={newContactNote}
            onChange={(e) => setNewContactNote(e.target.value)}
            placeholder="Личная заметка к этому контакту…"
            style={{ width: '100%', minHeight: '60px', borderRadius: '12px', border: '1px solid var(--line)', padding: '10px', background: 'var(--surface)', color: 'var(--ink)' }}
          />
          <button type="submit" disabled={!newContactInput.trim() || addContact.isPending}>
            {addContact.isPending ? 'Добавление…' : '+ Добавить контакт'}
          </button>
        </form>
      </article>

      {/* Contacts List with F06 pagination */}
      <h3>Контакты ({contactsTotal})</h3>
      {contactsQuery.isLoading && <p role="status">Загрузка контактов…</p>}
      {contactsQuery.error && <p role="alert">{(contactsQuery.error as any).message}</p>}

      {contactsList.length === 0 && !contactsQuery.isLoading && (
        <p className="muted">В этом разделе пока нет контактов. Добавьте первый выше.</p>
      )}

      {contactsList.map((contact) => (
        <article key={contact.id} className="catalog-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <strong>{contact.display_name || contact.raw_input}</strong>
              {contact.normalized_username && <small>@{contact.normalized_username}</small>}
            </div>
            <button
              onClick={() => setEditingContact(contact)}
              style={{ fontSize: '12px', padding: '4px 8px', minHeight: '30px' }}
            >
              Редактировать
            </button>
          </div>
          <p className="long-text" style={{ marginTop: '8px', color: 'var(--muted)', fontSize: '14px' }}>
            {contact.note || 'Без заметки'}
          </p>
        </article>
      ))}

      {/* F06: Pagination for 51+ contacts */}
      {contactsTotal > 50 && (
        <div className="pagination">
          <button
            disabled={contactsOffset === 0}
            onClick={() => setContactsOffset(Math.max(0, contactsOffset - 50))}
          >
            ← Предыдущие 50
          </button>
          <span style={{ alignSelf: 'center', fontSize: '13px', color: 'var(--muted)' }}>
            {contactsOffset + 1}–{Math.min(contactsOffset + 50, contactsTotal)} из {contactsTotal}
          </span>
          <button
            disabled={contactsOffset + 50 >= contactsTotal}
            onClick={() => setContactsOffset(contactsOffset + 50)}
          >
            Следующие 50 →
          </button>
        </div>
      )}

      {/* Edit Note Modal */}
      {editingContact && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'grid', placeItems: 'center', zIndex: 100, padding: '16px' }}>
          <article style={{ background: 'var(--surface)', maxWidth: '420px', width: '100%', borderRadius: '20px', padding: '20px' }}>
            <h3>Редактировать контакт</h3>
            <p className="muted">{editingContact.raw_input}</p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const noteVal = (e.currentTarget.elements.namedItem('note') as HTMLTextAreaElement).value;
                const nameVal = (e.currentTarget.elements.namedItem('displayName') as HTMLInputElement).value;
                updateContact.mutate({ id: editingContact.id, note: noteVal, display_name: nameVal });
              }}
            >
              <label htmlFor="edit-name">Отображаемое имя</label>
              <input id="edit-name" name="displayName" defaultValue={editingContact.display_name || ''} />
              <label htmlFor="edit-note">Заметка</label>
              <textarea
                id="edit-note"
                name="note"
                defaultValue={editingContact.note || ''}
                style={{ width: '100%', minHeight: '100px', borderRadius: '12px', border: '1px solid var(--line)', padding: '10px', background: 'var(--surface)', color: 'var(--ink)' }}
              />
              <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                <button type="button" onClick={() => setEditingContact(null)} style={{ background: 'var(--line)', color: 'var(--ink)' }}>
                  Отмена
                </button>
                <button type="submit" disabled={updateContact.isPending}>
                  {updateContact.isPending ? 'Сохранение…' : 'Сохранить'}
                </button>
              </div>
            </form>
          </article>
        </div>
      )}
    </section>
  );
}
