'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { User } from '@/types';
import { getToken, getStoredUser, clearAuth, getMe, checkBackendHealth } from '@/api';
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

  const handleInvalidSession = async () => {
    console.log('[AuthProvider] Clearing invalid or deleted session...');
    localStorage.removeItem('esona_token');
    localStorage.removeItem('esona_user');
    setTokenState(null);
    setUser(null);
    try {
      await supabase.auth.signOut();
    } catch (err) {
      console.warn('[AuthProvider] Supabase signOut error on invalid session:', err);
    }
  };

  // Warmup Backend Mount Ping and 4-minute heartbeat to keep connection pool active and prevent Render cold starts
  useEffect(() => {
    const runPing = async () => {
      console.log('[AuthProvider] Sending backend warmup ping...');
      try {
        const healthy = await checkBackendHealth();
        console.log('[AuthProvider] Backend warmup ping status:', healthy ? 'SUCCESS' : 'FAILED');
      } catch (err) {
        console.warn('[AuthProvider] Backend warmup ping failed:', err);
      }
    };

    // Run immediately on mount
    runPing();

    // Set interval for every 4 minutes (4 * 60 * 1000 ms)
    const intervalId = setInterval(runPing, 4 * 60 * 1000);

    return () => clearInterval(intervalId);
  }, []);

  // Load and listen to Supabase Auth State changes
  useEffect(() => {
    const initAuth = async () => {
      try {
        console.log('[AuthProvider] Restoring Supabase session...');
        const { data: { session } } = await supabase.auth.getSession();
        
        if (session) {
          const jwtToken = session.access_token;
          setTokenState(jwtToken);
          localStorage.setItem('esona_token', jwtToken);
          
          const freshUser = await getMe(jwtToken);
          setUser(freshUser);
          localStorage.setItem('esona_user', JSON.stringify(freshUser));
          console.log('[AuthProvider] Session restored successfully for:', freshUser.email);
        } else {
          // Clear if no session
          setTokenState(null);
          setUser(null);
        }
      } catch (err) {
        console.warn('[AuthProvider] Session restoration error:', err);
        await handleInvalidSession();
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();

    // Set up auth state change listener
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      console.log('[AuthProvider] onAuthStateChange event:', event);
      if (session) {
        const jwtToken = session.access_token;
        setTokenState(jwtToken);
        localStorage.setItem('esona_token', jwtToken);
        
        try {
          const freshUser = await getMe(jwtToken);
          setUser(freshUser);
          localStorage.setItem('esona_user', JSON.stringify(freshUser));
        } catch (err) {
          console.error('[AuthProvider] Failed to sync profile on event:', err);
          await handleInvalidSession();
        }
      } else {
        setTokenState(null);
        setUser(null);
        localStorage.removeItem('esona_token');
        localStorage.removeItem('esona_user');
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  // Route protection redirect checks
  useEffect(() => {
    if (!isLoading) {
      const storedToken = localStorage.getItem('esona_token') || token;
      const storedUser = getStoredUser() || user;

      if (!storedToken || !storedUser) {
        if (protectedRoutes.some(route => pathname.startsWith(route)) && pathname !== '/login') {
          router.push('/login');
        }
      } else {
        const hasCompletedOnboarding = storedUser.onboardingCompleted ?? false;
        
        if (pathname === '/' || pathname === '/login') {
          if (!hasCompletedOnboarding) {
            router.push('/onboarding');
          } else {
            router.push('/chat');
          }
        } else if (!hasCompletedOnboarding && (pathname.startsWith('/chat') || pathname.startsWith('/dashboard'))) {
          console.log('[AuthProvider] Redirecting to onboarding...');
          router.push('/onboarding');
        } else if (hasCompletedOnboarding && pathname === '/onboarding') {
          router.push('/chat');
        }
      }
    }
  }, [pathname, isLoading, router, user, token]);

  const login = (newToken: string, newUser: User) => {
    localStorage.setItem('esona_token', newToken);
    localStorage.setItem('esona_user', JSON.stringify(newUser));
    setTokenState(newToken);
    setUser(newUser);
    
    if (!newUser.onboardingCompleted) {
      router.push('/onboarding');
    } else {
      router.push('/chat');
    }
  };

  const logout = async () => {
    try {
      await supabase.auth.signOut();
    } catch (e) {
      console.warn('[AuthProvider] Signout error:', e);
    }
    
    // Clear all storage
    localStorage.clear();
    sessionStorage.clear();
    
    // Clear document cookies manually to prevent any stale state
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

  const refreshUser = async () => {
    const currentToken = token || localStorage.getItem('esona_token');
    if (!currentToken) return;
    try {
      const freshUser = await getMe(currentToken);
      setUser(freshUser);
      localStorage.setItem('esona_user', JSON.stringify(freshUser));
    } catch (err) {
      console.error('[AuthProvider] Failed to refresh user:', err);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token,
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
