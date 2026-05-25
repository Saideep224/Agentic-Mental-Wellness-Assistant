'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { User } from '@/types';
import { getToken, getStoredUser, clearAuth, getMe } from '@/lib/api';

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
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  const router = useRouter();
  const pathname = usePathname();

  // Load session from storage on mount
  useEffect(() => {
    const initAuth = async () => {
      const storedToken = getToken();
      const storedUser = getStoredUser();

      if (storedToken && storedUser) {
        setToken(storedToken);
        setUser(storedUser);
        
        try {
          const freshUser = await getMe(storedToken);
          setUser(freshUser);
          localStorage.setItem('esona_user', JSON.stringify(freshUser));
        } catch (err) {
          console.warn('[AuthProvider] Failed to refresh user, keeping local data:', err);
          // If token expired (Unauthorized), clear state
          if (err instanceof Error && (err.message.includes('401') || err.message.includes('expired') || err.message.includes('Unauthorized'))) {
            clearAuth();
            setToken(null);
            setUser(null);
            if (protectedRoutes.some(route => pathname.startsWith(route))) {
              router.push('/login');
            }
          }
        }
      } else {
        // If no credentials and we are on a protected route, redirect to login
        if (protectedRoutes.some(route => pathname.startsWith(route))) {
          router.push('/login');
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, [router, pathname]);

  // Route protection redirect checks when pathname changes
  useEffect(() => {
    if (!isLoading) {
      const storedToken = getToken();
      if (!storedToken && protectedRoutes.some(route => pathname.startsWith(route))) {
        router.push('/login');
      }
    }
  }, [pathname, isLoading, router]);

  const login = (newToken: string, newUser: User) => {
    localStorage.setItem('esona_token', newToken);
    localStorage.setItem('esona_user', JSON.stringify(newUser));
    setToken(newToken);
    setUser(newUser);
    router.push('/dashboard');
  };

  const logout = () => {
    clearAuth();
    setToken(null);
    setUser(null);
    router.push('/');
  };

  const refreshUser = async () => {
    const currentToken = token || getToken();
    if (!currentToken) return;
    try {
      const freshUser = await getMe(currentToken);
      setUser(freshUser);
      localStorage.setItem('esona_user', JSON.stringify(freshUser));
    } catch (err) {
      console.error('[AuthProvider] Failed to refresh user details:', err);
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
