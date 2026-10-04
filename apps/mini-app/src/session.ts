import { createContext, useContext } from 'react';
import type { CurrentUser } from './api';
export const AuthContext = createContext<{ user: CurrentUser; logout: () => Promise<void> } | null>(null);
export function useAuth() { const value = useContext(AuthContext); if (!value) throw new Error('No session'); return value; }
