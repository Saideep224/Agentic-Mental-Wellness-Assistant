'use client';

import { useState, useEffect, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Mail, Lock, User, ArrowRight, Eye, EyeOff, RefreshCw, Wifi, WifiOff } from 'lucide-react';
import Link from 'next/link';
import EsonaLogo from '@/components/layout/EsonaLogo';
import FullPageTransition from '@/components/layout/FullPageTransition';
import * as api from '@/api';
import { supabase } from '@/database/supabase';
import { useAuth } from '@/providers/AuthProvider';

type AuthMode = 'login' | 'register';

export default function LoginPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading, login: authLogin } = useAuth();
  const [mode, setMode] = useState<AuthMode>('register');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline' | 'idle'>('idle');

  // AuthProvider's route guard handles redirecting authenticated users away from /login.
  // No need to duplicate the logic here — it causes double-redirect races.

  // Check backend health and URL error parameters on mount
  useEffect(() => {
    const checkHealth = async () => {
      setBackendStatus('checking');
      const healthy = await api.checkBackendHealth();
      setBackendStatus(healthy ? 'online' : 'offline');
    };
    checkHealth();

    if (typeof window !== 'undefined') {
      const searchParams = new URLSearchParams(window.location.search);
      const urlError = searchParams.get('error');
      if (urlError) {
        try {
          setError(decodeURIComponent(urlError));
        } catch (e) {
          setError(urlError);
        }
      }
    }
  }, []);

  // Session check on mount removed in favor of central AuthProvider route protection checks

  const handleGithubLogin = async () => {
    try {
      setError('');
      setIsLoading(true);
      const redirectTo = `${window.location.origin}/auth/callback`;
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'github',
        options: {
          redirectTo,
        },
      });
      if (error) throw error;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'GitHub Authentication failed');
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    try {
      setError('');
      setIsLoading(true);
      const redirectTo = `${window.location.origin}/auth/callback`;
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo,
        },
      });
      if (error) throw error;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Google Authentication failed');
      setIsLoading(false);
    }
  };

  const retryHealthCheck = async () => {
    setBackendStatus('checking');
    setError('');
    const healthy = await api.checkBackendHealth();
    setBackendStatus(healthy ? 'online' : 'offline');
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      if (mode === 'register') {
        if (!name.trim()) {
          setError('Please enter your name');
          setIsLoading(false);
          return;
        }
        if (password.length < 8) {
          setError('Password must be at least 8 characters');
          setIsLoading(false);
          return;
        }

        console.log('[Auth] Registering user via Supabase Auth...');
        const { data, error: signUpError } = await supabase.auth.signUp({
          email: email.trim(),
          password,
          options: {
            data: {
              full_name: name.trim(),
            },
          },
        });

        if (signUpError) throw signUpError;
        if (!data.user) throw new Error('No user returned from Supabase Auth');
        console.log('[Auth] Signup success:', data.user.email);



        const session = data.session;
        if (!session) {
          setIsLoading(false);
          setError('Registration successful! Please check your email to confirm your account.');
          return;
        }

        const jwtToken = session.access_token;
        const freshUser = await api.getMe(jwtToken);
        api.setToken(jwtToken);
        api.setStoredUser(freshUser);
        console.log('[Auth] Register getMe success. onboardingCompleted:', freshUser.onboardingCompleted);

        // Use authLogin() to set AuthProvider state before navigating
        authLogin(jwtToken, freshUser);
      } else {
        console.log('[Auth] Logging in via Supabase Auth...');
        const { data, error: signInError } = await supabase.auth.signInWithPassword({
          email: email.trim(),
          password,
        });

        if (signInError) throw signInError;
        if (!data.user) throw new Error('No user returned from Supabase Auth');
        console.log('[Auth] Login success:', data.user.email);



        const session = data.session;
        if (!session) throw new Error('No active session found.');

        const jwtToken = session.access_token;
        const freshUser = await api.getMe(jwtToken);
        api.setToken(jwtToken);
        api.setStoredUser(freshUser);
        console.log('[Auth] Login getMe success. onboardingCompleted:', freshUser.onboardingCompleted);

        // Use authLogin() to set AuthProvider state before navigating
        authLogin(jwtToken, freshUser);
      }
    } catch (err: any) {
      console.error('[Auth] Submit failed:', err);
      const message = err instanceof Error ? err.message : 'Something went wrong';
      setError(message);
      if (message.toLowerCase().includes('duplicate') || message.toLowerCase().includes('already registered') || message.toLowerCase().includes('already exists')) {
        setError('An account with this email address already exists.');
      } else if (message.toLowerCase().includes('invalid login credentials') || message.toLowerCase().includes('invalid credentials')) {
        setError('Invalid email or password.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Visual guard: show loader while auth is being determined (prevents login form flash)
  if (authLoading) {
    return (
      <AnimatePresence>
        <FullPageTransition message="Checking your session..." />
      </AnimatePresence>
    );
  }

  // Visual guard: if already authenticated, show redirect loader instead of login form
  if (isAuthenticated) {
    const dest = user?.onboardingCompleted ? 'chat...' : 'onboarding...';
    return (
      <AnimatePresence>
        <FullPageTransition message={`Taking you to ${dest}`} />
      </AnimatePresence>
    );
  }

  return (
    <main className="min-h-screen flex items-center justify-center px-4 py-20">
      <motion.div
        initial={{ opacity: 0, y: 30, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className="w-full max-w-md animate-glow"
      >
        {/* Logo */}
        <div className="text-center mb-6 flex flex-col items-center">
          <Link href="/" className="inline-flex flex-col items-center">
            <EsonaLogo
              size={85}
              showParticles={true}
              glowIntensity="high"
              className="mb-3 logo-float"
            />
          </Link>
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
            {mode === 'login' ? 'Welcome back. We missed you. ✨' : 'Begin your journey with Esona. 🌙'}
          </p>
        </div>

        {/* Backend status indicator */}
        <AnimatePresence>
          {backendStatus === 'offline' && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mb-4 px-4 py-3 rounded-xl text-sm flex items-center justify-between"
              style={{
                background: 'rgba(251, 191, 36, 0.1)',
                border: '1px solid rgba(251, 191, 36, 0.2)',
                color: '#fbbf24',
              }}
            >
              <div className="flex items-center gap-2">
                <WifiOff size={14} />
                <span>Server is waking up... This may take 30-60 seconds.</span>
              </div>
              <button
                onClick={retryHealthCheck}
                className="p-1 rounded-lg hover:bg-white/5 transition-colors cursor-pointer"
                title="Retry connection"
              >
                <RefreshCw size={14} />
              </button>
            </motion.div>
          )}
          {backendStatus === 'checking' && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mb-4 px-4 py-3 rounded-xl text-sm flex items-center gap-2"
              style={{
                background: 'rgba(56, 189, 248, 0.05)',
                border: '1px solid rgba(56, 189, 248, 0.1)',
                color: 'var(--accent-cyan)',
              }}
            >
              <div
                className="w-3 h-3 rounded-full border-2 animate-spin"
                style={{
                  borderColor: 'rgba(56, 189, 248, 0.3)',
                  borderTopColor: 'var(--accent-cyan)',
                }}
              />
              <span>Connecting to server...</span>
            </motion.div>
          )}
          {backendStatus === 'online' && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="mb-4 px-4 py-2 rounded-xl text-sm flex items-center gap-2"
              style={{
                background: 'rgba(52, 211, 153, 0.08)',
                border: '1px solid rgba(52, 211, 153, 0.15)',
                color: '#34d399',
              }}
            >
              <Wifi size={14} />
              <span>Server connected</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Auth card */}
        <div className="glass-card p-8">
          {/* Mode Toggle Header */}
          <div className="text-center mb-6">
            <h2 className="text-xl font-bold text-white mb-2" style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}>
              {mode === 'login' ? 'Log in to your account' : 'Create your account'}
            </h2>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              {mode === 'login' ? (
                <>
                  Don't have an account?{' '}
                  <button
                    type="button"
                    onClick={() => { setMode('register'); setError(''); }}
                    className="text-sky-400 hover:text-sky-300 font-semibold underline cursor-pointer bg-transparent border-0 p-0 text-xs"
                  >
                    Sign Up
                  </button>
                </>
              ) : (
                <>
                  Already have an account?{' '}
                  <button
                    type="button"
                    onClick={() => { setMode('login'); setError(''); }}
                    className="text-sky-400 hover:text-sky-300 font-semibold underline cursor-pointer bg-transparent border-0 p-0 text-xs"
                  >
                    Sign In
                  </button>
                </>
              )}
            </p>
          </div>

          {/* OAuth Buttons Section at the Top */}
          <div className="space-y-3 mb-6">
            <motion.button
              type="button"
              onClick={handleGoogleLogin}
              disabled={isLoading}
              whileHover={{ scale: 1.01, boxShadow: 'var(--glow-cyan)', borderColor: 'rgba(56, 189, 248, 0.4)' }}
              whileTap={{ scale: 0.99 }}
              style={{
                border: '1px solid var(--glass-border)',
                background: 'var(--surface-glass)',
              }}
              className="w-full py-3 rounded-xl text-sm font-medium flex items-center justify-center gap-3 cursor-pointer transition-all duration-300 text-white disabled:opacity-50"
            >
              <svg className="w-4 h-4 mr-1" viewBox="0 0 24 24">
                <path
                  fill="#EA4335"
                  d="M5.266 9.765A7.077 7.077 0 0 1 12 4.909c1.69 0 3.218.6 4.418 1.582l3.51-3.51C17.642 1.09 14.973 0 12 0 7.354 0 3.307 2.68 1.347 6.58l3.919 3.185Z"
                />
                <path
                  fill="#4285F4"
                  d="M24 12c0-.86-.073-1.68-.21-2.482H12v4.69H18.74A5.766 5.766 0 0 1 16.25 18l3.866 3a11.96 11.96 0 0 0 3.884-9Z"
                />
                <path
                  fill="#FBBC05"
                  d="M1.347 6.58A12.012 12.012 0 0 0 0 12c0 1.96.47 3.82 1.306 5.48l3.96-3.07a7.039 7.039 0 0 1-.03-4.83l-3.89-3Z"
                />
                <path
                  fill="#34A853"
                  d="M5.237 14.41A7.054 7.054 0 0 1 12 19.091c1.618 0 3.09-.54 4.273-1.455l3.866 3C17.964 22.82 15.118 24 12 24 7.354 24 3.307 21.32 1.306 17.42l3.93-3.01Z"
                />
              </svg>
              <span>{isLoading ? 'Connecting...' : 'Continue with Google'}</span>
            </motion.button>

            <motion.button
              type="button"
              onClick={handleGithubLogin}
              disabled={isLoading}
              whileHover={{ scale: 1.01, boxShadow: 'var(--glow-purple)', borderColor: 'rgba(167, 139, 250, 0.4)' }}
              whileTap={{ scale: 0.99 }}
              style={{
                border: '1px solid var(--glass-border)',
                background: 'var(--surface-glass)',
              }}
              className="w-full py-3 rounded-xl text-sm font-medium flex items-center justify-center gap-3 cursor-pointer transition-all duration-300 text-white disabled:opacity-50"
            >
              <svg className="w-4 h-4 mr-1 fill-current" viewBox="0 0 24 24">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.11.82-.26.82-.577v-2.234c-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22v3.293c0 .319.22.694.825.576C20.565 21.795 24 17.3 24 12c0-6.63-5.37-12-12-12z" />
              </svg>
              <span>{isLoading ? 'Connecting...' : 'Continue with GitHub'}</span>
            </motion.button>
          </div>

          <div className="relative mb-6 flex items-center justify-center">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-white/10"></div>
            </div>
            <span className="relative px-3 text-xs uppercase" style={{ color: 'var(--text-muted)', background: 'rgba(10,14,26,0.95)' }}>
              Or with email and password
            </span>
          </div>

          {/* Form */}
          <AnimatePresence mode="wait">
            <motion.form
              key={mode}
              initial={{ opacity: 0, x: mode === 'login' ? -20 : 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: mode === 'login' ? 20 : -20 }}
              transition={{ duration: 0.25 }}
              onSubmit={handleSubmit}
              className="space-y-4"
            >
              {/* Name field (register only) */}
              <AnimatePresence>
                {mode === 'register' && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.25 }}
                  >
                    <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                      Name
                    </label>
                    <div className="relative">
                      <User
                        size={16}
                        className="absolute left-3 top-1/2 -translate-y-1/2"
                        style={{ color: 'var(--text-muted)' }}
                      />
                      <input
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="What should we call you?"
                        className="w-full pl-10 pr-4 py-3 glass-input text-sm"
                        required={mode === 'register'}
                        disabled={isLoading}
                        suppressHydrationWarning
                      />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Email */}
              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                  Email Address
                </label>
                <div className="relative">
                  <Mail
                    size={16}
                    className="absolute left-3 top-1/2 -translate-y-1/2"
                    style={{ color: 'var(--text-muted)' }}
                  />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    className="w-full pl-10 pr-4 py-3 glass-input text-sm"
                    required
                    disabled={isLoading}
                    suppressHydrationWarning
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                  Password
                </label>
                <div className="relative">
                  <Lock
                    size={16}
                    className="absolute left-3 top-1/2 -translate-y-1/2"
                    style={{ color: 'var(--text-muted)' }}
                  />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-10 pr-12 py-3 glass-input text-sm"
                    required
                    minLength={8}
                    disabled={isLoading}
                    suppressHydrationWarning
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 cursor-pointer"
                    style={{ color: 'var(--text-muted)' }}
                    suppressHydrationWarning
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {/* Error message */}
              <AnimatePresence>
                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -5 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -5 }}
                    className="px-4 py-3 rounded-xl text-sm flex items-start gap-2"
                    style={{
                      background: 'rgba(244, 114, 182, 0.1)',
                      border: '1px solid rgba(244, 114, 182, 0.2)',
                      color: 'var(--accent-pink)',
                    }}
                  >
                    <span className="flex-1">{error}</span>
                    {(error.includes('server') || error.includes('timed out') || error.includes('reach')) && (
                      <button
                        type="button"
                        onClick={retryHealthCheck}
                        className="p-1 rounded hover:bg-white/5 transition-colors cursor-pointer shrink-0"
                        title="Retry connection"
                      >
                        <RefreshCw size={14} />
                      </button>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Submit button */}
              <motion.button
                type="submit"
                disabled={isLoading}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                className="w-full py-3 gradient-btn text-sm rounded-xl flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                suppressHydrationWarning
              >
                {isLoading ? (
                  <div className="flex items-center gap-2">
                    <div
                      className="w-4 h-4 rounded-full border-2 animate-spin"
                      style={{
                        borderColor: 'rgba(10, 14, 26, 0.3)',
                        borderTopColor: 'var(--bg-primary)',
                      }}
                    />
                    <span>{mode === 'login' ? 'Signing in...' : 'Creating account...'}</span>
                  </div>
                ) : (
                  <>
                    <span>{mode === 'login' ? 'Sign In' : 'Create Account'}</span>
                    <ArrowRight size={16} />
                  </>
                )}
              </motion.button>
            </motion.form>
          </AnimatePresence>
        </div>

        {/* Bottom text */}
        <p className="text-center mt-6 text-xs" style={{ color: 'var(--text-muted)' }}>
          Your data is encrypted and never shared. 🔒
        </p>
      </motion.div>
    </main>
  );
}
