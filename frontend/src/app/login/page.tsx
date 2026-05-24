'use client';

import { useState, useEffect, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Mail, Lock, User, ArrowRight, Eye, EyeOff, RefreshCw, Wifi, WifiOff } from 'lucide-react';
import Link from 'next/link';
import * as api from '@/lib/api';

type AuthMode = 'login' | 'register';

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<AuthMode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline' | 'idle'>('idle');

  // Check backend health on mount
  useEffect(() => {
    const checkHealth = async () => {
      setBackendStatus('checking');
      const healthy = await api.checkBackendHealth();
      setBackendStatus(healthy ? 'online' : 'offline');
    };
    checkHealth();
  }, []);

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
        const data = await api.register(name.trim(), email.trim(), password);
        api.setToken(data.access_token);
        api.setStoredUser(data.user);

        if (!data.user.onboardingCompleted) {
          router.push('/onboarding');
        } else {
          router.push('/chat');
        }
      } else {
        const data = await api.login(email.trim(), password);
        api.setToken(data.access_token);
        api.setStoredUser(data.user);

        if (!data.user.onboardingCompleted) {
          router.push('/onboarding');
        } else {
          router.push('/chat');
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Something went wrong';
      setError(message);
      // If it was a network error, refresh backend status
      if (message.includes('server') || message.includes('timed out') || message.includes('reach')) {
        setBackendStatus('offline');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen flex items-center justify-center px-4 py-20">
      <motion.div
        initial={{ opacity: 0, y: 30, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className="w-full max-w-md"
      >
        {/* Logo */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-block">
            <h1
              className="text-4xl font-bold glow-text mb-2"
              style={{ fontFamily: 'var(--font-outfit), sans-serif' }}
            >
              Esona
            </h1>
          </Link>
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
            {mode === 'login' ? 'Welcome back. We missed you.' : 'Begin your journey with Esona.'}
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
                background: 'rgba(34, 211, 238, 0.05)',
                border: '1px solid rgba(34, 211, 238, 0.1)',
                color: 'var(--accent-cyan)',
              }}
            >
              <div
                className="w-3 h-3 rounded-full border-2 animate-spin"
                style={{
                  borderColor: 'rgba(34, 211, 238, 0.3)',
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
              transition={{ exit: { delay: 2 } }}
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
          {/* Mode toggle */}
          <div
            className="flex rounded-xl p-1 mb-6"
            style={{ background: 'rgba(255, 255, 255, 0.03)' }}
          >
            {(['login', 'register'] as AuthMode[]).map((m) => (
              <button
                key={m}
                onClick={() => {
                  setMode(m);
                  setError('');
                }}
                className="flex-1 py-2 rounded-lg text-sm font-medium transition-all duration-300 capitalize cursor-pointer"
                style={{
                  background: mode === m ? 'rgba(34, 211, 238, 0.1)' : 'transparent',
                  color: mode === m ? 'var(--accent-cyan)' : 'var(--text-muted)',
                  border: mode === m ? '1px solid rgba(34, 211, 238, 0.2)' : '1px solid transparent',
                }}
              >
                {m === 'login' ? 'Sign In' : 'Sign Up'}
              </button>
            ))}
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
                        suppressHydrationWarning
                      />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Email */}
              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                  Email
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
