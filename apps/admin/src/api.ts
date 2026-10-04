let accessToken = '';

export interface CurrentUser {
  id: number;
  telegram_id: string;
  username?: string | null;
  role: string;
  is_2fa_enabled: boolean;
}

export interface AdminDashboardStats {
  pending_cases_count: number;
  pending_appeals_count: number;
  open_support_count: number;
  quarantined_evidence_count: number;
  total_users_count: number;
  total_subjects_count: number;
}

export interface AdminCase {
  id: number;
  creator_id: number;
  subject_id: number | null;
  target_username: string | null;
  experience_type: string;
  category: string;
  description: string;
  agreed_terms: string | null;
  author_actions: string | null;
  result_description: string | null;
  amount: string | null;
  currency: string | null;
  status: string;
  visibility: string;
  current_version: number;
  created_at: string;
}

export interface AdminAppeal {
  id: number;
  case_id: number;
  appellant_id: number;
  reviewer_id: number | null;
  reason: string;
  status: string;
  decision_note: string | null;
  created_at: string;
}

export interface AdminSupportTicket {
  id: number;
  user_id: number;
  subject: string;
  message: string;
  status: string;
  answer: string | null;
  answered_by: number | null;
  created_at: string;
}

export interface AdminUserItem {
  id: number;
  telegram_id: string;
  username: string | null;
  role: string;
}

export interface AdminAuditLog {
  id: number;
  actor_id: number | null;
  action: string;
  object_type: string;
  object_id: string;
  details: string | null;
  ip_address: string | null;
  created_at: string;
}

export interface TwoFactorSetup {
  secret: string;
  provisioning_uri: string;
  recovery_codes: string[];
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
}

export function getAccessToken(): string {
  return accessToken;
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    cache: 'no-store',
    headers: {
      'Content-Type': 'application/json',
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...init.headers,
    },
  });

  if (!response.ok) {
    let detail = '';
    try {
      const body = await response.json();
      detail = body.detail || '';
    } catch {
      // not json
    }

    const message =
      detail ||
      (response.status === 401
        ? 'Сессия недействительна. Откройте приложение заново через Telegram.'
        : response.status === 403
        ? 'Недостаточно прав. Требуется роль сотрудника.'
        : response.status === 503
        ? 'Требуется подтверждение второго фактора (2FA).'
        : response.status === 422
        ? 'Проверьте введённые данные.'
        : response.status === 404
        ? 'Запись не найдена.'
        : 'Не удалось выполнить запрос.');
    throw new ApiError(response.status, message);
  }

  return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>);
}
