'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, X, Trash2, Loader2, ShieldOff } from 'lucide-react';
import { deleteAccount } from '@/api/auth';
import { clearAuth, getToken } from '@/api/client';
import { supabase } from '@/database/supabase';

const DANGER_ITEMS = [
  { icon: '👤', label: 'Profile & account details' },
  { icon: '💬', label: 'All chat history & conversations' },
  { icon: '🧠', label: 'Memories & emotional patterns' },
  { icon: '🕸️', label: 'Knowledge graph relationships' },
  { icon: '📊', label: 'Mood & emotion history' },
  { icon: '🎯', label: 'Preferences & onboarding answers' },
];

interface DeleteAccountModalProps {
  userEmail?: string;
  onClose: () => void;
}

export default function DeleteAccountModal({ userEmail, onClose }: DeleteAccountModalProps) {
  const [confirmText, setConfirmText] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleted, setDeleted] = useState(false);

  const isConfirmed = confirmText === 'DELETE';

  const handleDelete = async () => {
    if (!isConfirmed || isDeleting) return;
    setIsDeleting(true);
    setError(null);

    try {
      const token = getToken();
      if (!token) throw new Error('No auth token found. Please refresh and try again.');

      // ── SUPABASE DB CLEANUP (Wipes profiles and cascades related rows) ──
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        console.log('[DeleteAccountModal] Wiping user records from Supabase database...');
        const { error: profileError } = await supabase
          .from('profiles')
          .delete()
          .eq('user_id', user.id);
        if (profileError) {
          console.warn('[DeleteAccountModal] Supabase profiles deletion failed, attempting delete by id:', profileError);
          // Fallback delete by id
          await supabase.from('profiles').delete().eq('id', user.id);
        }
      }

      await deleteAccount(token);
      setDeleted(true);

      // Sign out from Supabase Auth immediately to clear stored local auth session
      try {
        await supabase.auth.signOut();
      } catch (supaErr) {
        console.warn('[DeleteAccountModal] Supabase signOut error:', supaErr);
      }

      // Clear all local auth state and other storage
      clearAuth();

      // Small delay so user can read the success message, then redirect
      setTimeout(() => {
        window.location.href = '/login';
      }, 2000);
    } catch (err: any) {
      console.error('[DeleteAccount] Failed:', err);
      setError(err instanceof Error ? err.message : 'Account deletion failed. Please try again.');
      setIsDeleting(false);
    }
  };

  return (
    <AnimatePresence>
      {/* Backdrop */}
      <motion.div
        key="backdrop"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        style={{ background: 'rgba(0, 0, 0, 0.75)', backdropFilter: 'blur(8px)' }}
        onClick={(e) => { if (e.target === e.currentTarget && !isDeleting && !deleted) onClose(); }}
      >
        <motion.div
          key="modal"
          initial={{ opacity: 0, scale: 0.92, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.92, y: 20 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className="relative w-full max-w-md rounded-2xl overflow-hidden"
          style={{
            background: 'rgba(10, 10, 18, 0.98)',
            border: '1px solid rgba(239, 68, 68, 0.25)',
            boxShadow: '0 0 60px rgba(239, 68, 68, 0.12), 0 25px 50px rgba(0,0,0,0.5)',
          }}
        >
          {/* Red accent bar at top */}
          <div
            className="h-1 w-full"
            style={{
              background: 'linear-gradient(90deg, transparent, rgba(239, 68, 68, 0.7), rgba(220, 38, 38, 0.9), rgba(239, 68, 68, 0.7), transparent)',
            }}
          />

          <div className="p-6">
            {deleted ? (
              /* ── Success State ── */
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="text-center py-6"
              >
                <div
                  className="w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center"
                  style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)' }}
                >
                  <ShieldOff size={28} className="text-red-400" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2" style={{ fontFamily: 'var(--font-outfit), sans-serif' }}>
                  Account Deleted
                </h3>
                <p className="text-sm text-slate-400">
                  All your data has been permanently removed. Redirecting to login...
                </p>
                <div className="mt-4 flex items-center justify-center gap-2 text-xs text-slate-500">
                  <Loader2 size={12} className="animate-spin" />
                  Redirecting...
                </div>
              </motion.div>
            ) : (
              <>
                {/* ── Header ── */}
                <div className="flex items-start justify-between mb-5">
                  <div className="flex items-center gap-3">
                    <div
                      className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                      style={{ background: 'rgba(239, 68, 68, 0.12)', border: '1px solid rgba(239, 68, 68, 0.2)' }}
                    >
                      <AlertTriangle size={18} className="text-red-400" />
                    </div>
                    <div>
                      <h2
                        className="text-lg font-bold text-white leading-tight"
                        style={{ fontFamily: 'var(--font-outfit), sans-serif' }}
                      >
                        Delete Account
                      </h2>
                      <p className="text-xs text-red-400/80 font-medium">This action is permanent and irreversible</p>
                    </div>
                  </div>
                  {!isDeleting && (
                    <button
                      onClick={onClose}
                      className="p-1.5 rounded-lg text-slate-500 hover:text-white hover:bg-white/5 transition-all cursor-pointer"
                    >
                      <X size={16} />
                    </button>
                  )}
                </div>

                {/* ── Warning description ── */}
                <p className="text-sm text-slate-300 mb-4 leading-relaxed">
                  {userEmail && (
                    <span className="block text-xs text-slate-500 mb-2 font-mono bg-white/3 px-2 py-1 rounded-lg border border-white/5 truncate">
                      {userEmail}
                    </span>
                  )}
                  This will permanently remove all of your data from Esona. There is no way to undo this.
                </p>

                {/* ── Data deletion list ── */}
                <div
                  className="rounded-xl p-4 mb-5 space-y-2"
                  style={{ background: 'rgba(239, 68, 68, 0.04)', border: '1px solid rgba(239, 68, 68, 0.12)' }}
                >
                  <p className="text-xs font-semibold text-red-400 mb-3 uppercase tracking-wide">
                    The following will be permanently deleted:
                  </p>
                  {DANGER_ITEMS.map((item, idx) => (
                    <div key={idx} className="flex items-center gap-2.5">
                      <span className="text-sm">{item.icon}</span>
                      <span className="text-xs text-slate-300">{item.label}</span>
                    </div>
                  ))}
                </div>

                {/* ── Confirmation input ── */}
                <div className="mb-5">
                  <label className="block text-xs font-semibold text-slate-400 mb-2">
                    Type <span className="text-red-400 font-mono font-bold">DELETE</span> to confirm:
                  </label>
                  <input
                    id="delete-confirm-input"
                    type="text"
                    value={confirmText}
                    onChange={(e) => setConfirmText(e.target.value)}
                    placeholder="Type DELETE here"
                    disabled={isDeleting}
                    autoComplete="off"
                    autoCorrect="off"
                    spellCheck={false}
                    className="w-full px-4 py-3 rounded-xl text-sm font-mono outline-none transition-all duration-200 disabled:opacity-50"
                    style={{
                      background: 'rgba(255, 255, 255, 0.03)',
                      border: `1px solid ${isConfirmed ? 'rgba(239, 68, 68, 0.5)' : 'rgba(255, 255, 255, 0.08)'}`,
                      color: isConfirmed ? 'rgb(248, 113, 113)' : 'var(--text-primary)',
                      boxShadow: isConfirmed ? '0 0 12px rgba(239, 68, 68, 0.15)' : 'none',
                    }}
                  />
                </div>

                {/* ── Error ── */}
                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -4 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-4 p-3 rounded-xl text-xs text-red-400 border"
                    style={{ background: 'rgba(239, 68, 68, 0.06)', borderColor: 'rgba(239, 68, 68, 0.2)' }}
                  >
                    ⚠️ {error}
                  </motion.div>
                )}

                {/* ── Actions ── */}
                <div className="flex items-center gap-3">
                  <button
                    onClick={onClose}
                    disabled={isDeleting}
                    className="flex-1 py-3 rounded-xl text-sm font-semibold text-slate-300 hover:text-white transition-all duration-200 disabled:opacity-50 cursor-pointer"
                    style={{
                      background: 'rgba(255, 255, 255, 0.05)',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                    }}
                  >
                    Cancel
                  </button>
                  <motion.button
                    id="delete-account-confirm-btn"
                    onClick={handleDelete}
                    disabled={!isConfirmed || isDeleting}
                    whileHover={isConfirmed && !isDeleting ? { scale: 1.02 } : {}}
                    whileTap={isConfirmed && !isDeleting ? { scale: 0.98 } : {}}
                    className="flex-1 py-3 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 transition-all duration-300 cursor-pointer disabled:cursor-not-allowed"
                    style={{
                      background: isConfirmed
                        ? 'linear-gradient(135deg, rgb(220, 38, 38), rgb(185, 28, 28))'
                        : 'rgba(239, 68, 68, 0.08)',
                      border: `1px solid ${isConfirmed ? 'rgba(239, 68, 68, 0.5)' : 'rgba(239, 68, 68, 0.15)'}`,
                      color: isConfirmed ? 'white' : 'rgba(239, 68, 68, 0.4)',
                      boxShadow: isConfirmed ? '0 4px 20px rgba(220, 38, 38, 0.35)' : 'none',
                      opacity: isDeleting ? 0.7 : 1,
                    }}
                  >
                    {isDeleting ? (
                      <>
                        <Loader2 size={14} className="animate-spin" />
                        Deleting...
                      </>
                    ) : (
                      <>
                        <Trash2 size={14} />
                        Delete My Account
                      </>
                    )}
                  </motion.button>
                </div>
              </>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
