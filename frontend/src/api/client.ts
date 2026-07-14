/**
 * Base API client — retry logic, HTTP helpers, token management.
 * 
 * This module provides the foundational infrastructure for all API calls:
 * - Configurable retry with exponential backoff (for Render cold starts)
 * - Typed HTTP methods (GET, POST, PATCH, DELETE)
 * - Automatic 401 handling with auth clearing
 * - localStorage-based token and user session management
 */

import { User } from '@/types';
import { supabase } from '@/database/supabase';

// ============================================
// API BASE URL
// ============================================

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';

// ============================================
// RETRY & TIMEOUT CONFIG (for Render cold starts)
// ============================================

const MAX_RETRIES = 2;
const INITIAL_TIMEOUT_MS = 30000; // 30s for Render free tier cold starts
const RETRY_DELAY_MS = 2000;

async function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isNetworkError(error: unknown): boolean {
  if (error instanceof TypeError && error.message === 'Failed to fetch') return true;
  if (error instanceof DOMException && error.name === 'AbortError') return true;
  return false;
}

function friendlyErrorMessage(error: unknown): string {
  if (error instanceof TypeError && error.message === 'Failed to fetch') {
    return 'Unable to reach the server. It may be starting up — please try again in a few seconds.';
  }
  if (error instanceof DOMException && error.name === 'AbortError') {
    return 'The request timed out. The server may be waking up — please try again.';
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'Something went wrong. Please try again.';
}

// ============================================
// TOKEN MANAGEMENT
// ============================================

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('esona_token');
}

export function setToken(token: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem('esona_token', token);
}

export function removeToken(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('esona_token');
}

export function getStoredUser(): User | null {
  if (typeof window === 'undefined') return null;
  const data = localStorage.getItem('esona_user');
  if (!data) return null;
  try {
    return JSON.parse(data);
  } catch {
    return null;
  }
}

export function setStoredUser(user: User): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem('esona_user', JSON.stringify(user));
}

export function removeStoredUser(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('esona_user');
}

export function clearAuth(): void {
  removeToken();
  removeStoredUser();
  if (typeof window !== 'undefined') {
    try {
      localStorage.clear();
      sessionStorage.clear();
      supabase.auth.signOut();
    } catch (err) {
      console.warn('[clearAuth] Supabase signOut error:', err);
    }
  }
}

// ============================================
// HTTP HELPERS (with retry + timeout)
// ============================================

async function parseError(response: Response, errorData: any): Promise<string> {
  let errorMessage = `Request failed with status ${response.status}`;
  if (errorData && errorData.detail) {
    if (typeof errorData.detail === 'string') {
      errorMessage = errorData.detail;
    } else if (Array.isArray(errorData.detail)) {
      errorMessage = errorData.detail
        .map((err: any) => {
          const field = err.loc && err.loc.length > 0 ? err.loc[err.loc.length - 1] : '';
          const msg = err.msg || 'Invalid value';
          return field ? `${field}: ${msg}` : msg;
        })
        .join(', ');
    }
  } else if (errorData && errorData.message) {
    errorMessage = errorData.message;
  }
  return errorMessage;
}

export async function fetchWithRetry(
  url: string,
  options: RequestInit,
  retries: number = MAX_RETRIES,
  timeoutMs: number = INITIAL_TIMEOUT_MS
): Promise<Response> {
  let lastError: unknown;

  for (let attempt = 0; attempt <= retries; attempt++) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      lastError = error;

      console.warn(
        `[Esona API] Request failed (attempt ${attempt + 1}/${retries + 1}):`,
        error instanceof Error ? error.message : error
      );

      // Only retry on network errors / timeouts, not on HTTP errors
      if (attempt < retries && isNetworkError(error)) {
        const delay = RETRY_DELAY_MS * Math.pow(2, attempt);
        console.info(`[Esona API] Retrying in ${delay}ms...`);
        await sleep(delay);
      } else {
        break;
      }
    }
  }

  throw lastError;
}

function getEndpointTimeout(endpoint: string, method: string): { timeoutMs: number; retries: number } {
  const url = endpoint.toLowerCase();
  
  // LONG endpoints (heavy LLM generations, start-fresh reset, analytical operations)
  if (
    url.includes('/chat/message') || 
    url.includes('/start-fresh') || 
    url.includes('/insights') ||
    url.includes('/first-message')
  ) {
    return { timeoutMs: 45000, retries: 0 };
  }
  
  // FAST endpoints (basic health checks and auth status checks)
  if (
    url.includes('/health') || 
    url.includes('/auth/me') || 
    url.includes('/me')
  ) {
    // 35s timeout gives Render free tier sufficient time to wake up, max 1 retry avoids storms
    return { timeoutMs: 35000, retries: 1 };
  }
  
  // NORMAL endpoints (conversations lists, questionnaire answers, profile reading/updating)
  const isRead = method === 'GET';
  return { 
    timeoutMs: 25000, 
    retries: isRead ? 2 : 0 // Allow retries for idempotent reads, block retries on writes
  };
}

export async function apiGet<T>(endpoint: string, token?: string | null): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    const { timeoutMs, retries } = getEndpointTimeout(endpoint, 'GET');
    response = await fetchWithRetry(`${API_BASE}${endpoint}`, {
      method: 'GET',
      headers,
    }, retries, timeoutMs);
  } catch (error) {
    throw new Error(friendlyErrorMessage(error));
  }

  if (!response.ok) {
    // DO NOT auto-redirect on 401/403 here — the AuthProvider handles session
    // invalidation with proper context. Auto-redirecting here causes the login loop:
    // backend cold start 401 → wipes fresh session → redirects back to /login.
    const errorData = await response.json().catch(() => ({}));
    const message = await parseError(response, errorData);
    const err = new Error(message);
    (err as any).status = response.status;
    throw err;
  }

  return response.json();
}

export async function apiPost<T>(endpoint: string, body?: unknown, token?: string | null): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    const { timeoutMs, retries } = getEndpointTimeout(endpoint, 'POST');
    response = await fetchWithRetry(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers,
      body: body ? JSON.stringify(body) : undefined,
    }, retries, timeoutMs);
  } catch (error) {
    throw new Error(friendlyErrorMessage(error));
  }

  if (!response.ok) {
    // DO NOT auto-redirect on 401/403 here — see apiGet comment above.
    const errorData = await response.json().catch(() => ({}));
    const message = await parseError(response, errorData);
    const err = new Error(message);
    (err as any).status = response.status;
    throw err;
  }

  return response.json();
}

export async function apiPatch<T>(endpoint: string, body?: unknown, token?: string | null): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    const { timeoutMs, retries } = getEndpointTimeout(endpoint, 'PATCH');
    response = await fetchWithRetry(`${API_BASE}${endpoint}`, {
      method: 'PATCH',
      headers,
      body: body ? JSON.stringify(body) : undefined,
    }, retries, timeoutMs);
  } catch (error) {
    throw new Error(friendlyErrorMessage(error));
  }

  if (!response.ok) {
    // DO NOT auto-redirect on 401/403 here — see apiGet comment above.
    const errorData = await response.json().catch(() => ({}));
    const message = await parseError(response, errorData);
    const err = new Error(message);
    (err as any).status = response.status;
    throw err;
  }

  return response.json();
}

export async function apiDelete<T = void>(endpoint: string, token?: string | null): Promise<T> {
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    const { timeoutMs, retries } = getEndpointTimeout(endpoint, 'DELETE');
    response = await fetchWithRetry(`${API_BASE}${endpoint}`, {
      method: 'DELETE',
      headers,
    }, retries, timeoutMs);
  } catch (error) {
    throw new Error(friendlyErrorMessage(error));
  }

  if (!response.ok) {
    // DO NOT auto-redirect on 401/403 here — see apiGet comment above.
    const errorData = await response.json().catch(() => ({}));
    const message = await parseError(response, errorData);
    const err = new Error(message);
    (err as any).status = response.status;
    throw err;
  }

  // Return parsed JSON if content exists, otherwise undefined
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return response.json() as Promise<T>;
  }
  return undefined as unknown as T;
}

// ============================================
// HEALTH CHECK
// ============================================

let backendHealthPromise: Promise<boolean> | null = null;
let backendHealthCheckedAt: number = 0;
const HEALTH_CACHE_COOLDOWN_MS = 15000;

export async function checkBackendHealth(): Promise<boolean> {
  const now = Date.now();
  if (now - backendHealthCheckedAt < HEALTH_CACHE_COOLDOWN_MS) {
    return true;
  }
  if (backendHealthPromise) {
    return backendHealthPromise;
  }

  backendHealthPromise = (async () => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      try {
        controller.abort("request_timeout");
      } catch {
        controller.abort();
      }
    }, 5000); // 5s short timeout for ping

    try {
      const response = await fetch(`${API_BASE}/health`, {
        method: 'GET',
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      const isHealthy = response.ok;
      if (isHealthy) {
        backendHealthCheckedAt = Date.now();
      }
      return isHealthy;
    } catch (err) {
      clearTimeout(timeoutId);
      console.warn('[checkBackendHealth] Ping failed:', err);
      return false;
    } finally {
      backendHealthPromise = null;
    }
  })();

  return backendHealthPromise;
}

// ============================================
// USER MAPPER — converts backend snake_case to frontend camelCase
// ============================================

export function mapUser(backendUser: any): User {
  if (!backendUser) return backendUser;
  return {
    id: backendUser.id,
    name: backendUser.name ?? backendUser.full_name ?? '',
    email: backendUser.email,
    onboardingCompleted: backendUser.onboarding_completed ?? backendUser.onboardingCompleted ?? false,
    avatarUrl: backendUser.avatar_url ?? backendUser.avatarUrl ?? null,
    provider: backendUser.provider || 'credentials',
    githubUsername: backendUser.github_username ?? backendUser.githubUsername ?? null,
    createdAt: backendUser.created_at ?? backendUser.createdAt ?? '',
  };
}
