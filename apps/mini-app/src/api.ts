let accessToken = sessionStorage.getItem('kontur_token') || '';

export interface CurrentUser {
  id: number;
  telegram_id: string;
  username?: string | null;
  first_name?: string | null;
  role: string;
}

export interface SubjectReputationSummary {
  positive_count: number;
  negative_count: number;
  total_cases: number;
  last_observed_at: string | null;
}

export interface ObservationResponse {
  id: number;
  raw_username: string;
  normalized_username: string;
  source: string;
  observed_at: string;
  is_verified: boolean;
}

export interface PublishedReviewItem {
  id: number;
  case_id: number;
  author_pseudonym: string;
  score_type: 'POSITIVE' | 'NEGATIVE';
  category: string;
  deal_date: string | null;
  result_description: string | null;
  outcome_note: string | null;
  created_at: string;
  has_response: boolean;
}

export interface SubjectCardDetailed {
  id: number;
  telegram_id: string | null;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  is_verified: boolean;
  reputation: SubjectReputationSummary;
  observations: ObservationResponse[];
  published_reviews: PublishedReviewItem[];
  private_note: string | null;
  is_subscribed: boolean;
}

export interface SubjectSearchItem {
  id: number;
  telegram_id: string | null;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  is_verified: boolean;
  reputation: SubjectReputationSummary;
}

export interface SubjectSearchResponse {
  items: SubjectSearchItem[];
  total: number;
}

export interface Catalog {
  id: number;
  name: string;
  description: string | null;
  is_private: boolean;
  contact_count: number;
  role: string;
  created_at: string;
}

export interface SavedContact {
  id: number;
  user_id: number;
  catalog_id: number | null;
  raw_input: string;
  normalized_username: string | null;
  display_name: string | null;
  note: string | null;
  tags: string | null;
  is_favorite: boolean;
  is_pinned: boolean;
  personal_rating: string | null;
  subject_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface SavedContactListResponse {
  items: SavedContact[];
  total: number;
  limit: number;
  offset: number;
}

export interface Case {
  id: number;
  creator_id: number;
  subject_id: number | null;
  target_username: string | null;
  experience_type: 'POSITIVE' | 'NEGATIVE';
  category: string;
  deal_date: string | null;
  agreed_terms: string | null;
  author_actions: string | null;
  result_description: string | null;
  amount: string | null;
  currency: string | null;
  violation_details: string | null;
  status: string;
  visibility: string;
  description: string;
  current_version: number;
  outcome_note: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface NotificationItem {
  id: number;
  user_id: number;
  event_type: string;
  title: string;
  message: string;
  object_type: string | null;
  object_id: number | null;
  is_read: boolean;
  created_at: string;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function setAccessToken(token: string) {
  accessToken = token;
  if (token) {
    sessionStorage.setItem('kontur_token', token);
  } else {
    sessionStorage.removeItem('kontur_token');
  }
}

export function getAccessToken(): string {
  return accessToken;
}

export async function refreshSession(): Promise<boolean> {
  if (!accessToken) return false;
  try {
    const res = await fetch('/api/v1/auth/refresh', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
    });
    if (res.ok) {
      const data = await res.json();
      setAccessToken(data.access_token);
      return true;
    }
  } catch {
    // network failure
  }
  return false;
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response = await fetch(`/api/v1${path}`, {
    ...init,
    cache: 'no-store',
    headers: {
      'Content-Type': 'application/json',
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...init.headers,
    },
  });

  // F04: Auto-refresh session on 401 if we have a token
  if (response.status === 401 && accessToken && !path.startsWith('/auth/refresh')) {
    const refreshed = await refreshSession();
    if (refreshed) {
      response = await fetch(`/api/v1${path}`, {
        ...init,
        cache: 'no-store',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
          ...init.headers,
        },
      });
    }
  }

  if (!response.ok) {
    const message =
      response.status === 401
        ? 'Сессия недействительна. Откройте приложение заново через Telegram.'
        : response.status === 403
        ? 'Нет доступа.'
        : response.status === 409
        ? 'Конфликт данных или повторная отправка.'
        : response.status === 429
        ? 'Слишком много запросов. Пожалуйста, подождите минуту.'
        : response.status === 503
        ? 'Функция недоступна: сервис на обслуживании.'
        : response.status === 422
        ? 'Проверьте введённые данные.'
        : response.status === 404
        ? 'Запись недоступна.'
        : 'Не удалось выполнить запрос. Попробуйте ещё раз.';
    throw new ApiError(response.status, message);
  }

  return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>);
}
