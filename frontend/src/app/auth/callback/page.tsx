'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import * as api from '@/lib/api';

export default function AuthCallbackPage() {
  const router = useRouter();
  const [status, setStatus] = useState('Completing authentication...');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Exchange session and check if logged in
        const { data: { session }, error: sessionError } = await supabase.auth.getSession();
        
        if (sessionError) throw sessionError;
        
        if (!session || !session.user) {
          throw new Error('No active session found. Please try logging in again.');
        }

        setStatus('Syncing user profile with server...');
        
        const userMeta = session.user.user_metadata || {};
        const githubUsername = userMeta.preferred_username || userMeta.user_name || null;
        
        // Detect OAuth provider
        let provider = 'github';
        if (session.user.app_metadata.provider) {
          provider = session.user.app_metadata.provider;
        } else if (session.user.identities && session.user.identities.length > 0) {
          provider = session.user.identities[0].provider;
        }

        const oauthData = {
          name: userMeta.full_name || userMeta.name || session.user.email?.split('@')[0] || 'OAuth User',
          email: session.user.email || '',
          avatar_url: userMeta.avatar_url || null,
          provider: provider,
          github_username: githubUsername,
        };

        // Send to FastAPI backend
        const backendUrl = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
        const res = await fetch(`${backendUrl}/api/auth/supabase-login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(oauthData),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || 'Failed to sync OAuth session with backend');
        }

        const backendData = await res.json();
        
        // Save FastAPI token and user profile locally
        api.setToken(backendData.access_token);
        api.setStoredUser(backendData.user);

        // Sign out from supabase client to stick with backend JWT session
        await supabase.auth.signOut();

        setStatus('Redirecting to dashboard...');
        router.push('/dashboard');
      } catch (err: any) {
        console.error('[Esona Auth Callback] Error:', err);
        const errMsg = err instanceof Error ? err.message : 'Authentication failed';
        setError(errMsg);
        
        // Sign out from supabase client on error
        await supabase.auth.signOut().catch(() => {});
        
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
