'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { User } from '@/types';
import { getToken, getStoredUser, clearAuth, getMe, checkBackendHealth, mapUser } from '@/api';
import { supabase } from '@/database/supabase';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const protectedRoutes = ['/chat', '/dashboard', '/onboarding', '/knowing-me'];

export default function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setTokenState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const router = useRouter();
  const pathname = usePathname();

  // ─── Hard logout: only called for explicit/confirmed auth errors ───────────
  const handleInvalidSession = async () => {
    console.log('[AuthProvider] Clearing confirmed-invalid session...');
    if (typeof window !== 'undefined') {
      try {
        localStorage.removeItem('esona_token');
        localStorage.removeItem('esona_user');
      } catch (err) {
        console.warn('[AuthProvider] Storage clear error:', err);
      }
    }
    setTokenState(null);
    setUser(null);
    try {
      await supabase.auth.signOut();
    } catch (err) {
      console.warn('[AuthProvider] Supabase signOut error:', err);
    }
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  };

  // ─── Backend warmup ping + heartbeat ──────────────────────────────────────
  useEffect(() => {
    const runPing = async () => {
      try {
        const healthy = await checkBackendHealth();
        console.log('[AuthProvider] Backend ping:', healthy ? 'OK' : 'FAILED');
      } catch (err) {
        console.warn('[AuthProvider] Backend ping error:', err);
      }
    };
    runPing();
    const intervalId = setInterval(runPing, 4 * 60 * 1000);
    return () => clearInterval(intervalId);
  }, []);

  // ─── Core auth initialisation + Supabase listener ─────────────────────────
  useEffect(() => {
    const initAuth = async () => {
      try {
        console.log('[AuthProvider] Restoring Supabase session...');
        const { data: { session } } = await supabase.auth.getSession();

        if (session) {
          const jwtToken = session.access_token;
          // Optimistically set token + a basic user from Supabase metadata
          // so route guard never sees a null user during getMe() round-trip.
          const supabaseUser: User = mapUser({
            id: session.user.id,
            email: session.user.email ?? '',
            name: session.user.user_metadata?.full_name || session.user.email?.split('@')[0] || 'User',
            onboarding_completed: false,
            avatar_url: session.user.user_metadata?.avatar_url ?? null,
            provider: session.user.app_metadata?.provider ?? 'credentials',
          });

          // Check localStorage first for full user (has onboardingCompleted)
          const cached = getStoredUser();
          const initialUser = cached?.id === session.user.id ? cached : supabaseUser;

          setTokenState(jwtToken);
          setUser(initialUser);
          localStorage.setItem('esona_token', jwtToken);

          console.log('[AuthProvider] Session found. User:', initialUser.email, '| onboardingCompleted:', initialUser.onboardingCompleted);

          // Try to refresh user from backend — but DON'T clear session on failure
          try {
            const freshUser = await getMe(jwtToken);
            setUser(freshUser);
            localStorage.setItem('esona_user', JSON.stringify(freshUser));
            console.log('[AuthProvider] getMe OK:', freshUser.email, '| onboardingCompleted:', freshUser.onboardingCompleted);
          } catch (getMeErr: any) {
            // Backend may be cold-starting or returning a transient error.
            // Do NOT wipe the session — Supabase session is valid.
            // We'll use the cached/supabase-derived user until backend warms up.
            const status = (getMeErr as any)?.status;
            console.warn('[AuthProvider] getMe failed (non-fatal, keeping session). Status:', status, 'Error:', getMeErr?.message);
            // Only hard-logout if Supabase itself says the token is invalid (403 sub mismatch)
            // Don't logout on 401 — Render cold starts return 401 transiently.
            if (status === 403 || getMeErr?.message?.includes('sub claim')) {
              console.warn('[AuthProvider] Confirmed invalid sub claim. Clearing session.');
              await handleInvalidSession();
            }
            // else: keep the session alive, user stays logged in
          }
        } else {
          console.log('[AuthProvider] No Supabase session found.');
          setTokenState(null);
          setUser(null);
          localStorage.removeItem('esona_token');
          localStorage.removeItem('esona_user');
        }
      } catch (err: any) {
        // This is a Supabase SDK error (network issue etc.) — not an auth error.
        // Retain any existing local session.
        console.warn('[AuthProvider] initAuth Supabase error (non-fatal):', err?.message);
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();

    // ─── Supabase auth state change listener ──────────────────────────────
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      console.log('[AuthProvider] onAuthStateChange:', event, '| hasSession:', !!session);

      if (event === 'SIGNED_OUT') {
        setTokenState(null);
        setUser(null);
        localStorage.removeItem('esona_token');
        localStorage.removeItem('esona_user');
        return;
      }

      if (session) {
        const jwtToken = session.access_token;
        setTokenState(jwtToken);
        localStorage.setItem('esona_token', jwtToken);

        // Try to sync with backend — non-fatal on failure
        try {
          const freshUser = await getMe(jwtToken);
          console.log('[AuthProvider] onAuthStateChange getMe OK:', freshUser.email);
          setUser(freshUser);
          localStorage.setItem('esona_user', JSON.stringify(freshUser));
        } catch (err: any) {
          const status = (err as any)?.status;
          console.warn('[AuthProvider] onAuthStateChange getMe failed. Status:', status, '| Keeping session.');
          // Only invalidate on confirmed invalid sub claim, not on 401 (Render cold start)
          if (status === 403 || err?.message?.includes('sub claim')) {
            await handleInvalidSession();
          }
          // Otherwise keep the optimistic user state
        }
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  // ─── Route protection ─────────────────────────────────────────────────────
  useEffect(() => {
    if (isLoading) return; // Wait for auth to initialise before making any routing decisions

    const storedToken = token || localStorage.getItem('esona_token');
    const storedUser = user || getStoredUser();

    const isAuthed = !!(storedToken && storedUser);
    const isOnProtectedRoute = protectedRoutes.some(route => pathname.startsWith(route));
    const isOnLoginPage = pathname === '/login';

    console.log('[AuthProvider] Route check | path:', pathname, '| authed:', isAuthed, '| onboardingCompleted:', storedUser?.onboardingCompleted);

    if (!isAuthed && isOnProtectedRoute) {
      // Not logged in, trying to access protected page → login
      console.log('[AuthProvider] → Redirecting to /login (not authenticated)');
      router.push('/login');
      return;
    }

    if (isAuthed && isOnLoginPage) {
      // Already logged in, on login page → send to correct destination
      if (!storedUser!.onboardingCompleted) {
        console.log('[AuthProvider] → Redirecting to /onboarding');
        router.replace('/onboarding');
      } else {
        console.log('[AuthProvider] → Redirecting to /chat');
        router.replace('/chat');
      }
      return;
    }

    if (isAuthed && storedUser!.onboardingCompleted && pathname === '/onboarding') {
      // Onboarding already done, back on onboarding page → send to chat
      console.log('[AuthProvider] → Redirecting to /chat (onboarding already complete)');
      router.replace('/chat');
    }
  }, [pathname, isLoading, user, token, router]);

  // ─── login() — called from login page after successful Supabase auth ───────
  const login = (newToken: string, newUser: User) => {
    console.log('[AuthProvider] login() called for:', newUser.email, '| onboardingCompleted:', newUser.onboardingCompleted);
    localStorage.setItem('esona_token', newToken);
    localStorage.setItem('esona_user', JSON.stringify(newUser));
    setTokenState(newToken);
    setUser(newUser);

    if (!newUser.onboardingCompleted) {
      router.replace('/onboarding');
    } else {
      router.replace('/chat');
    }
  };

  // ─── logout() ─────────────────────────────────────────────────────────────
  const logout = async () => {
    try {
      await supabase.auth.signOut();
    } catch (e) {
      console.warn('[AuthProvider] Signout error:', e);
    }

    localStorage.clear();
    sessionStorage.clear();

    if (typeof document !== 'undefined') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i];
        const eqPos = cookie.indexOf('=');
        const name = eqPos > -1 ? cookie.substring(0, eqPos).trim() : cookie.trim();
        document.cookie = name + '=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/';
        document.cookie = name + '=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/;domain=' + window.location.hostname;
      }
    }

    setTokenState(null);
    setUser(null);
    window.location.href = '/login';
  };

  // ─── refreshUser() ────────────────────────────────────────────────────────
  const refreshUser = async () => {
    const currentToken = token || localStorage.getItem('esona_token');
    if (!currentToken) return;
    try {
      const freshUser = await getMe(currentToken);
      console.log('[AuthProvider] refreshUser OK:', freshUser.email, '| onboardingCompleted:', freshUser.onboardingCompleted);
      setUser(freshUser);
      localStorage.setItem('esona_user', JSON.stringify(freshUser));
    } catch (err) {
      console.error('[AuthProvider] refreshUser failed:', err);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!(token && user),
        isLoading,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
