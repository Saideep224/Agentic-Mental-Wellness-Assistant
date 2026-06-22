'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/database/supabase';
import * as api from '@/api';

export default function AuthCallbackPage() {
  const router = useRouter();
  const [status, setStatus] = useState('Completing authentication...');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // 1. Check for error parameters in the URL first (e.g. access_denied, popup_closed)
        const searchParams = new URLSearchParams(window.location.search);
        const urlError = searchParams.get('error') || searchParams.get('error_description');
        if (urlError) {
          throw new Error(urlError);
        }

        const code = searchParams.get('code');
        let session = null;

        // 2. Exchange code for session if PKCE code is present
        if (code) {
          console.log('[Auth Callback] PKCE code found, exchanging for session...');
          const { data, error: exchangeError } = await supabase.auth.exchangeCodeForSession(code);
          if (exchangeError) throw exchangeError;
          session = data.session;
        } else {
          // Fallback to getting current session (implicit grant / hash fallback)
          console.log('[Auth Callback] No code parameter, checking existing session...');
          const { data: { session: currentSession }, error: sessionError } = await supabase.auth.getSession();
          if (sessionError) throw sessionError;
          session = currentSession;
        }

        if (!session || !session.user) {
          throw new Error('No active session found. Please try logging in again.');
        }

        setStatus('Syncing user profile with database...');
        
        const userMeta = session.user.user_metadata || {};
        
        // Detect OAuth provider
        let provider = 'github';
        if (session.user.app_metadata.provider) {
          provider = session.user.app_metadata.provider;
        } else if (session.user.identities && session.user.identities.length > 0) {
          provider = session.user.identities[0].provider;
        }

        // Check if user already exists to keep onboardingCompleted status
        const { data: profile } = await supabase
          .from("profiles")
          .select("onboarding_completed")
          .eq("id", session.user.id)
          .single();
          
        const onboardingCompleted = profile?.onboarding_completed ?? false;

        const avatarUrl = userMeta.avatar_url || userMeta.picture || null;
        const githubUsername = provider === 'github' ? (userMeta.user_name || null) : null;

        // Upsert profile in Supabase database
        await supabase.from("profiles").upsert({
          id: session.user.id,
          user_id: session.user.id,
          email: session.user.email,
          full_name: userMeta.full_name || userMeta.name || session.user.email?.split('@')[0] || 'OAuth User',
          provider: provider,
          avatar_url: avatarUrl,
          github_username: githubUsername,
          onboarding_completed: onboardingCompleted
        });
        console.log('[Auth Callback] Profile upserted with avatar in Supabase database.');

        // Sync and register in backend SQLite/Postgres DB using getMe JWT call
        const jwtToken = session.access_token;
        const freshUser = await api.getMe(jwtToken);
        
        api.setToken(jwtToken);
        api.setStoredUser(freshUser);
        console.log('[Auth Callback] Successfully synced session with FastAPI backend:', freshUser);

        if (!freshUser.onboardingCompleted) {
          setStatus('Redirecting to home page...');
          router.replace('/');
        } else {
          setStatus('Redirecting to chat...');
          router.replace('/chat');
        }
      } catch (err: any) {
        console.error('[Esona Auth Callback] Error:', err);
        const errMsg = err instanceof Error ? err.message : 'Authentication failed';
        setError(errMsg);
        
        // Redirect back to login with error query parameter
        router.push(`/login?error=${encodeURIComponent(errMsg)}`);
      }
    };

    handleCallback();
  }, [router]);

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4 py-20">
      <div className="glass-card p-8 max-w-sm w-full text-center space-y-4">
        {error ? (
          <>
            <div className="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/25 flex items-center justify-center mx-auto text-2xl">
              ❌
            </div>
            <h2 className="text-xl font-bold text-white">Authentication Failed</h2>
            <p className="text-sm text-slate-400">{error}</p>
            <p className="text-xs text-slate-500">Redirecting back to login...</p>
          </>
        ) : (
          <>
            <div className="w-12 h-12 rounded-full border-2 border-cyan-400 border-t-transparent animate-spin flex items-center justify-center mx-auto" />
            <h2 className="text-xl font-bold text-white">Connecting Session</h2>
            <p className="text-sm text-slate-300">{status}</p>
            <p className="text-xs text-slate-500">Please do not close this window</p>
          </>
        )}
      </div>
    </main>
  );
}
