import { ApiResponse, LoginResponse, RegisterResponse, User, Message, Conversation, MoodDataPoint, EmotionalProfile, StressPattern, PersonalityInsight } from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';

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

async function fetchWithRetry(
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

async function apiGet<T>(endpoint: string, token?: string | null): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetchWithRetry(`${API_BASE}${endpoint}`, {
      method: 'GET',
      headers,
    });
  } catch (error) {
    throw new Error(friendlyErrorMessage(error));
  }

  if (!response.ok) {
    if (response.status === 401) {
      clearAuth();
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    }
    const errorData = await response.json().catch(() => ({}));
    const message = await parseError(response, errorData);
    throw new Error(message);
  }

  return response.json();
}

async function apiPost<T>(endpoint: string, body?: unknown, token?: string | null): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetchWithRetry(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (error) {
    throw new Error(friendlyErrorMessage(error));
  }

  if (!response.ok) {
    if (response.status === 401) {
      clearAuth();
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    }
    const errorData = await response.json().catch(() => ({}));
    const message = await parseError(response, errorData);
    throw new Error(message);
  }

  return response.json();
}

async function apiPatch<T>(endpoint: string, body?: unknown, token?: string | null): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetchWithRetry(`${API_BASE}${endpoint}`, {
      method: 'PATCH',
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (error) {
    throw new Error(friendlyErrorMessage(error));
  }

  if (!response.ok) {
    if (response.status === 401) {
      clearAuth();
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    }
    const errorData = await response.json().catch(() => ({}));
    const message = await parseError(response, errorData);
    throw new Error(message);
  }

  return response.json();
}

async function apiDelete(endpoint: string, token?: string | null): Promise<void> {
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetchWithRetry(`${API_BASE}${endpoint}`, {
      method: 'DELETE',
      headers,
    });
  } catch (error) {
    throw new Error(friendlyErrorMessage(error));
  }

  if (!response.ok) {
    if (response.status === 401) {
      clearAuth();
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    }
    const errorData = await response.json().catch(() => ({}));
    const message = await parseError(response, errorData);
    throw new Error(message);
  }
}

// ============================================
// HEALTH CHECK
// ============================================

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);
    const response = await fetch(`${API_BASE}/health`, {
      method: 'GET',
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response.ok;
  } catch {
    return false;
  }
}

// ============================================
// AUTH ENDPOINTS
// ============================================

function mapUser(backendUser: any): User {
  if (!backendUser) return backendUser;
  return {
    id: backendUser.id,
    name: backendUser.name,
    email: backendUser.email,
    onboardingCompleted: backendUser.onboarding_completed ?? backendUser.onboardingCompleted ?? false,
  };
}

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

// ============================================
// ONBOARDING ENDPOINTS
// ============================================

export async function submitOnboarding(
  responses: Array<{ questionId: number; category: string; selectedOption: string; customText?: string }>,
  token: string
): Promise<ApiResponse> {
  const answers = responses.map((r) => ({
    question_id: r.questionId,
    category: r.category,
    selected_option: r.selectedOption,
    custom_text: r.customText || null,
  }));
  return apiPost<ApiResponse>('/api/onboarding/submit', { answers }, token);
}

export async function getOnboardingStatus(token: string): Promise<{ completed: boolean }> {
  const data = await apiGet<any>('/api/onboarding/status', token);
  return {
    completed: data.onboarding_completed ?? data.completed ?? false,
  };
}

// ============================================
// CHAT ENDPOINTS
// ============================================

export function sendMessageSSE(
  conversationId: string,
  message: string,
  token: string
): EventSource {
  const url = `${API_BASE}/api/chat/${conversationId}/stream?message=${encodeURIComponent(message)}&token=${encodeURIComponent(token)}`;
  return new EventSource(url);
}

export async function sendMessage(
  conversationId: string,
  message: string,
  token: string
): Promise<{ response: string; emotionDetected?: string; moodScore?: number }> {
  return apiPost('/api/chat/message', { message, conversation_id: conversationId }, token);
}

export async function getConversations(token: string): Promise<Conversation[]> {
  const data = await apiGet<any[]>('/api/chat/conversations', token);
  return data.map((c) => ({
    id: c.id,
    title: c.title,
    createdAt: c.created_at ? new Date(c.created_at) : new Date(),
    lastMessage: c.last_message,
  }));
}

export async function getConversationMessages(conversationId: string, token: string): Promise<Message[]> {
  const data = await apiGet<any[]>(`/api/chat/conversations/${conversationId}/messages`, token);
  return data.map((m) => ({
    id: m.id,
    role: m.role,
    content: m.content,
    timestamp: m.created_at ? new Date(m.created_at) : new Date(),
    emotionDetected: m.emotion_detected ?? m.emotionDetected,
    moodScore: m.mood_score ?? m.moodScore,
  }));
}

export async function createConversation(token: string): Promise<Conversation> {
  const data = await apiPost<any>('/api/chat/conversations', {}, token);
  return {
    id: data.id,
    title: data.title,
    createdAt: data.created_at ? new Date(data.created_at) : new Date(),
    lastMessage: data.last_message,
  };
}

export async function updateConversation(
  conversationId: string,
  title: string,
  token: string
): Promise<Conversation> {
  const data = await apiPatch<any>(`/api/chat/conversations/${conversationId}`, { title }, token);
  return {
    id: data.id,
    title: data.title,
    createdAt: data.created_at ? new Date(data.created_at) : new Date(),
    lastMessage: data.last_message,
  };
}

export async function deleteConversation(conversationId: string, token: string): Promise<void> {
  await apiDelete(`/api/chat/conversations/${conversationId}`, token);
}

// ============================================
// DASHBOARD ENDPOINTS
// ============================================

export async function getMoodTrends(token: string): Promise<MoodDataPoint[]> {
  return apiGet<MoodDataPoint[]>('/api/dashboard/mood-trends', token);
}

export async function getEmotionalProfile(token: string): Promise<EmotionalProfile> {
  return apiGet<EmotionalProfile>('/api/dashboard/emotional-profile', token);
}

export async function getStressPatterns(token: string): Promise<StressPattern[]> {
  return apiGet<StressPattern[]>('/api/dashboard/stress-patterns', token);
}

export async function getInsights(token: string): Promise<PersonalityInsight[]> {
  return apiGet<PersonalityInsight[]>('/api/dashboard/insights', token);
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
}
