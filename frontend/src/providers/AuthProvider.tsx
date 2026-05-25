'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { User } from '@/types';
import { getToken, getStoredUser, clearAuth, getMe } from '@/lib/api';
import { supabase } from '@/lib/supabase';

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

const protectedRoutes = ['/chat', '/dashboard', '/onboarding'];

export default function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setTokenState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  const router = useRouter();
  const pathname = usePathname();

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
      const storedToken = localStorage.getItem('esona_token');
      const storedUser = getStoredUser();

      if (!storedToken) {
        if (protectedRoutes.some(route => pathname.startsWith(route)) && pathname !== '/login') {
          router.push('/login');
        }
      } else {
        const hasCompletedOnboarding = user?.onboardingCompleted ?? storedUser?.onboardingCompleted ?? false;
        
        if (pathname === '/login') {
          if (!hasCompletedOnboarding) {
            router.push('/onboarding');
          } else {
            router.push('/dashboard');
          }
        } else if (!hasCompletedOnboarding && (pathname.startsWith('/chat') || pathname.startsWith('/dashboard'))) {
          console.log('[AuthProvider] Redirecting to onboarding...');
          router.push('/onboarding');
        } else if (hasCompletedOnboarding && pathname === '/onboarding') {
          router.push('/dashboard');
        }
      }
    }
  }, [pathname, isLoading, router, user]);

  const login = (newToken: string, newUser: User) => {
    localStorage.setItem('esona_token', newToken);
    localStorage.setItem('esona_user', JSON.stringify(newUser));
    setTokenState(newToken);
    setUser(newUser);
    
    if (!newUser.onboardingCompleted) {
      router.push('/onboarding');
    } else {
      router.push('/dashboard');
    }
  };

  const logout = async () => {
    try {
      await supabase.auth.signOut();
    } catch (e) {
      console.warn('[AuthProvider] Signout error:', e);
    }
    localStorage.removeItem('esona_token');
    localStorage.removeItem('esona_user');
    setTokenState(null);
    setUser(null);
    router.push('/login');
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
