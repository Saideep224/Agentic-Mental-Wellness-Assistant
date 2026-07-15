'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, User as UserIcon, Calendar, Mail, LogOut, Trash2, AlertTriangle } from 'lucide-react';
import { getToken, getEmotionalProfile, startFresh } from '@/api';
import { useAuth } from '@/providers/AuthProvider';
import UserAvatar from '@/components/layout/UserAvatar';

interface ProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function ProfileModal({ isOpen, onClose }: ProfileModalProps) {
  const { user, logout, refreshUser } = useAuth();
  const [profile, setProfile] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  // Start Fresh confirmation modal state
  const [showConfirmReset, setShowConfirmReset] = useState(false);
  const [isResetChecked, setIsResetChecked] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [resetError, setResetError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      const fetchProfile = async () => {
        const token = getToken();
        if (!token) return;
        setIsLoading(true);
        try {
          const p = await getEmotionalProfile(token);
          setProfile(p);
        } catch (e) {
          console.warn('[ProfileModal] Failed to load user profile details:', e);
        } finally {
          setIsLoading(false);
        }
      };
      fetchProfile();
      // Reset confirmation states on open
      setShowConfirmReset(false);
      setIsResetChecked(false);
      setResetError(null);
    }
  }, [isOpen]);

  const handleLogout = async () => {
    await logout();
    onClose();
  };

  const handleStartFresh = async () => {
    if (!isResetChecked || isResetting) return;
    const token = getToken();
    if (!token) return;

    setIsResetting(true);
    setResetError(null);

    try {
      // 1. Call backend reset endpoint
      await startFresh(token);
      
      // 2. Clear frontend Esona-specific storage
      localStorage.removeItem('esona_chat_background_preferences');
      localStorage.removeItem('esona_onboarding_index');
      localStorage.removeItem('esona_onboarding_responses');
      sessionStorage.removeItem('esona_loaded');
      
      // 3. Refresh user state in auth context
      await refreshUser();
      
      // 4. Force reload and redirect to first-time flow
      window.location.replace('/onboarding');
    } catch (e: any) {
      console.error('[ProfileModal] Start Fresh failed:', e);
      setResetError('Unable to reset. Please check your connection and try again.');
      setIsResetting(false);
    }
  };

  const formatDate = (isoString?: string) => {
    if (!isoString) return 'May 2026';
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString('en-IN', {
        timeZone: 'Asia/Kolkata',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    } catch {
      return 'May 2026';
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-end">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
          />

          {/* Modal Content Drawer */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="relative w-full max-w-md h-full bg-[#05070f]/95 border-l border-white/5 flex flex-col justify-between overflow-y-auto"
            style={{
              boxShadow: '-10px 0 30px rgba(0,0,0,0.5)',
            }}
          >
            {/* Header */}
            <div>
              <div className="p-6 border-b border-white/5 flex items-center justify-between">
                <h2 className="text-lg font-bold text-white flex items-center gap-2" style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}>
                  <UserIcon size={18} className="text-cyan-400" />
                  Your Profile
                </h2>
                <button
                  onClick={onClose}
                  className="p-2 rounded-xl hover:bg-white/5 text-slate-400 hover:text-white transition-colors cursor-pointer"
                >
                  <X size={16} />
                </button>
              </div>

              {/* Body */}
              <div className="p-6 space-y-6">
                {/* User Avatar + Name Block */}
                <div className="flex flex-col items-center text-center pb-5 border-b border-white/5">
                  <div className="relative mb-3">
                    <UserAvatar
                      size={80}
                      avatarUrl={user?.avatarUrl}
                      name={user?.name}
                      glow={true}
                      enableHover={true}
                    />
                  </div>
                  <h3 className="text-base font-semibold text-white">{user?.name || 'Anonymous User'}</h3>
                  <p className="text-xs text-cyan-400 font-medium mt-1">
                    {profile?.completion_status === 'READY' ? 'Profile Calibrated 💙' : 'Calibration Pending'}
                  </p>
                </div>

                {/* Profile Analysis Section */}
                {profile?.completion_status !== 'READY' && (!profile?.traits || profile.traits.length === 0) ? (
                  <div className="p-5 rounded-2xl border border-dashed border-white/10 bg-white/2 text-center space-y-4">
                    <p className="text-xs text-slate-400 leading-relaxed">
                      Esona is still getting to know you. Complete Knowing Me or continue chatting to help Esona understand your communication style.
                    </p>
                    <div className="flex flex-col gap-2 pt-1">
                      <button
                        onClick={() => {
                          onClose();
                          window.location.href = '/knowing-me';
                        }}
                        className="py-2 px-4 rounded-xl text-xs font-semibold text-white bg-cyan-600 hover:bg-cyan-700 transition-colors cursor-pointer"
                      >
                        Complete Knowing Me
                      </button>
                      <button
                        onClick={onClose}
                        className="py-2 px-4 rounded-xl text-xs font-semibold text-slate-400 hover:text-white bg-white/5 hover:bg-white/10 transition-colors cursor-pointer"
                      >
                        Continue Chatting
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    {/* About You Section */}
                    <div className="space-y-2">
                      <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-500">About You</h4>
                      <div className="p-4 rounded-2xl border border-white/5 bg-white/2">
                        {isLoading ? (
                          <div className="flex items-center gap-2 py-1">
                            <div className="w-3.5 h-3.5 rounded-full border border-t-transparent animate-spin border-cyan-400" />
                            <span className="text-xs text-slate-400">Loading summary...</span>
                          </div>
                        ) : (
                          <p className="text-xs text-slate-300 leading-relaxed font-medium">
                            {profile?.about_you_summary}
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Esona Understands You As Section */}
                    <div className="space-y-3">
                      <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Esona Understands You As</h4>
                      {isLoading ? (
                        <div className="flex items-center gap-2 py-1">
                          <div className="w-3.5 h-3.5 rounded-full border border-t-transparent animate-spin border-cyan-400" />
                          <span className="text-xs text-slate-400">Loading trait signals...</span>
                        </div>
                      ) : profile?.traits && profile.traits.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                          {profile.traits.map((trait: string, idx: number) => (
                            <span
                              key={idx}
                              className="px-3 py-1.5 text-xs font-semibold rounded-xl bg-cyan-500/5 border border-cyan-500/15 text-cyan-400"
                            >
                              {trait}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <div className="p-3.5 rounded-2xl border border-dashed border-white/5 text-center">
                          <p className="text-xs text-slate-500">No conversational traits determined yet.</p>
                        </div>
                      )}
                    </div>
                  </>
                )}

                {/* Account Section */}
                <div className="space-y-3 pt-2">
                  <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Account</h4>
                  <div className="space-y-3">
                    <div className="flex items-center gap-3 text-xs text-slate-300">
                      <Mail size={15} className="text-slate-500" />
                      <div>
                        <p className="text-[9px] text-slate-500 leading-none mb-0.5">Email Address</p>
                        <p className="text-slate-300 font-medium">{user?.email || 'Not Available'}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 text-xs text-slate-300">
                      <Calendar size={15} className="text-slate-500" />
                      <div>
                        <p className="text-[9px] text-slate-500 leading-none mb-0.5">Joined Esona</p>
                        <p className="text-slate-300 font-medium">{formatDate(user?.createdAt)}</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Start Fresh Section */}
                <div className="pt-4 border-t border-white/5 space-y-3">
                  <div className="space-y-1">
                    <h4 className="text-[10px] font-bold uppercase tracking-wider text-amber-500/80">Danger Zone</h4>
                    <p className="text-[11px] text-slate-500 leading-relaxed">
                      Erase what Esona has learned and start questionnaire again.
                    </p>
                  </div>
                  <button
                    onClick={() => setShowConfirmReset(true)}
                    className="w-full py-2.5 px-4 rounded-xl text-xs font-semibold text-amber-400 bg-amber-500/5 hover:bg-amber-500/10 border border-amber-500/15 hover:border-amber-500/30 transition-all duration-300 cursor-pointer"
                  >
                    Start Fresh
                  </button>
                </div>
              </div>
            </div>

            {/* Footer buttons */}
            <div className="p-6 border-t border-white/5">
              <button
                onClick={handleLogout}
                className="w-full py-3 px-4 rounded-xl text-xs font-bold text-white flex items-center justify-center gap-2 hover:bg-red-500/10 hover:text-red-400 border border-transparent hover:border-red-500/20 transition-all duration-300 cursor-pointer"
                style={{
                  background: 'rgba(239, 68, 68, 0.05)',
                }}
              >
                <LogOut size={13} />
                Logout Account
              </button>
            </div>
          </motion.div>
        </div>
      )}

      {/* Start Fresh Confirmation Dialog Overlay */}
      {showConfirmReset && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            onClick={() => { if (!isResetting) setShowConfirmReset(false); }}
            className="absolute inset-0 bg-black/80 backdrop-blur-md"
          />

          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="relative w-full max-w-sm rounded-3xl bg-[#090b14]/95 border border-white/10 p-6 space-y-5 shadow-2xl"
          >
            <div className="flex items-center gap-2.5 text-amber-400">
              <AlertTriangle size={22} />
              <h3 className="text-base font-bold text-white" style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}>
                Start fresh with Esona?
              </h3>
            </div>

            <div className="space-y-2 text-xs leading-relaxed text-slate-400">
              <p>
                This will erase your chats, Knowing Me answers, memories, emotional history, and everything Esona has learned about you.
              </p>
              <p className="font-semibold text-slate-300">
                Your login account will stay active.
              </p>
              <p className="text-red-400 font-bold flex items-center gap-1.5 mt-2">
                <AlertTriangle size={12} />
                This can't be undone.
              </p>
            </div>

            <label className="flex items-start gap-2.5 text-xs text-slate-300 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={isResetChecked}
                onChange={(e) => setIsResetChecked(e.target.checked)}
                disabled={isResetting}
                className="mt-0.5 rounded border-white/10 bg-white/5 text-cyan-500 focus:ring-cyan-500 focus:ring-offset-0 cursor-pointer"
              />
              <span>I understand that my Esona history will be erased.</span>
            </label>

            {resetError && (
              <p className="text-xs text-red-400 font-semibold">{resetError}</p>
            )}

            <div className="flex gap-3 pt-2">
              <button
                onClick={() => setShowConfirmReset(false)}
                disabled={isResetting}
                className="flex-1 py-2.5 rounded-xl border border-white/5 text-xs font-semibold text-slate-400 hover:text-white hover:bg-white/5 transition-all cursor-pointer disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleStartFresh}
                disabled={!isResetChecked || isResetting}
                className={`flex-1 py-2.5 rounded-xl text-xs font-bold text-white transition-all cursor-pointer flex items-center justify-center gap-1.5 ${
                  isResetChecked && !isResetting
                    ? 'bg-amber-500 hover:bg-amber-600'
                    : 'bg-amber-500/20 text-slate-500 cursor-not-allowed border border-amber-500/10'
                }`}
              >
                {isResetting ? (
                  <>
                    <span className="w-3 h-3 rounded-full border border-t-transparent animate-spin border-white" />
                    Starting fresh...
                  </>
                ) : (
                  <>
                    <Trash2 size={12} />
                    Start Fresh
                  </>
                )}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
