/**
 * Auth API — login, register, profile fetch, account deletion.
 */

import { LoginResponse, RegisterResponse, User } from '@/types';
import { apiPost, apiGet, apiDelete, mapUser } from './client';

export async function register(name: string, email: string, password: string): Promise<RegisterResponse> {
  const data = await apiPost<any>('/api/auth/register', { name, email, password });
  return {
    access_token: data.access_token,
    user: mapUser(data.user),
  };
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const data = await apiPost<any>('/api/auth/login', { email, password });
  return {
    access_token: data.access_token,
    token_type: data.token_type,
    user: mapUser(data.user),
  };
}

export async function getMe(token: string): Promise<User> {
  const data = await apiGet<any>('/api/auth/me', token);
  return mapUser(data);
}

/**
 * Permanently delete the authenticated user's account and ALL associated data.
 * Requires a valid Bearer token. On success, clears localStorage and redirects to /login.
 */
export async function deleteAccount(token: string): Promise<{ deleted: boolean; user_id: string; email: string }> {
  return apiDelete<{ deleted: boolean; user_id: string; email: string }>('/api/auth/account', token);
}
