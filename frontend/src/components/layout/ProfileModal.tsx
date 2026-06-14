'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, User as UserIcon, Calendar, Shield, Mail, Key, Sparkles, LogOut, Edit } from 'lucide-react';
import { getToken, getStoredUser, clearAuth, getEmotionalProfile } from '@/api';
import { useAuth } from '@/providers/AuthProvider';
import UserAvatar from '@/components/layout/UserAvatar';

interface ProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
}
export default function ProfileModal({ isOpen, onClose }: ProfileModalProps) {
  const { logout } = useAuth();
  const [profile, setProfile] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  const user = getStoredUser();

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
    }
  }, [isOpen]);

  const handleLogout = async () => {
    await logout();
    onClose();
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
            className="relative w-full max-w-md h-full bg-[#0a0e1a]/95 border-l border-white/5 flex flex-col justify-between overflow-y-auto"
            style={{
              boxShadow: '-10px 0 30px rgba(0,0,0,0.5)',
            }}
          >
            {/* Header */}
            <div>
              <div className="p-6 border-b border-white/5 flex items-center justify-between">
                <h2 className="text-xl font-bold text-white flex items-center gap-2" style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}>
                  <UserIcon size={20} className="text-sky-400" />
                  Your Profile
                </h2>
                <button
                  onClick={onClose}
                  className="p-2 rounded-xl hover:bg-white/5 text-slate-400 hover:text-white transition-colors cursor-pointer"
                >
                  <X size={18} />
                </button>
              </div>

              {/* Body */}
              <div className="p-6 space-y-6">
                {/* User Avatar + Name Block */}
                <div className="flex flex-col items-center text-center pb-4 border-b border-white/5">
                  <div className="relative mb-3">
                    <UserAvatar
                      size={96}
                      avatarUrl={user?.avatarUrl}
                      name={user?.name}
                      glow={true}
                      enableHover={true}
                    />
                  </div>
                  <h3 className="text-lg font-semibold text-white">{user?.name || 'Anonymous User'}</h3>
                  <p className="text-xs text-sky-400 capitalize flex items-center gap-1.5 justify-center mt-1">
                    <Shield size={12} />
                    {profile?.personality_type?.type || 'Thoughtful Explorer'}
                  </p>
                </div>

                {/* Account Details */}
                <div className="space-y-4">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Account Details</h4>
                  
                  <div className="space-y-3">
                    <div className="flex items-center gap-3 text-sm text-slate-300">
                      <Mail size={16} className="text-slate-500" />
                      <div>
                        <p className="text-[10px] text-slate-500 leading-none mb-0.5">Email Address</p>
                        <p className="text-slate-300 font-medium">{user?.email || 'Not Available'}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 text-sm text-slate-300">
                      <Key size={16} className="text-slate-500" />
                      <div>
                        <p className="text-[10px] text-slate-500 leading-none mb-0.5">Authentication Provider</p>
                        <p className="text-slate-300 font-medium capitalize">{user?.provider || 'credentials'}</p>
                      </div>
                    </div>

                    {user?.provider === 'github' && (
                      <div className="flex items-center gap-3 text-sm text-slate-300">
                        <UserIcon size={16} className="text-slate-500" />
                        <div>
                          <p className="text-[10px] text-slate-500 leading-none mb-0.5">GitHub Username</p>
                          <p className="text-slate-300 font-medium">{user?.githubUsername || 'Not Available'}</p>
                        </div>
                      </div>
                    )}

                    <div className="flex items-center gap-3 text-sm text-slate-300">
                      <Calendar size={16} className="text-slate-500" />
                      <div>
                        <p className="text-[10px] text-slate-500 leading-none mb-0.5">Joined Esona</p>
                        <p className="text-slate-300 font-medium">{formatDate(user?.createdAt)}</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* AI Mindspace & Insights */}
                <div className="space-y-4 pt-2">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">AI Mindspace 🧠</h4>
                  
                  {isLoading ? (
                    <div className="flex items-center gap-2 py-2">
                      <div className="w-4 h-4 rounded-full border border-t-transparent animate-spin border-cyan-400" />
                      <span className="text-xs text-slate-400">Loading profile insights...</span>
                    </div>
                  ) : profile ? (
                    <div className="space-y-4">
                      {profile.personality_type?.summary && (
                        <div className="p-3.5 rounded-xl border border-white/5 bg-white/2">
                          <p className="text-xs font-semibold text-purple-400 mb-1 flex items-center gap-1">
                            <Sparkles size={12} />
                            Personality Summary
                          </p>
                          <p className="text-xs text-slate-300 leading-relaxed italic">
                            &ldquo;{profile.personality_type.summary}&rdquo;
                          </p>
                        </div>
                      )}

                      {profile.emotional_summary?.summary && (
                        <div className="p-3.5 rounded-xl border border-white/5 bg-white/2">
                          <p className="text-xs font-semibold text-emerald-400 mb-1 flex items-center gap-1">
                            🌱 Emotional Baseline
                          </p>
                          <p className="text-xs text-slate-300 leading-relaxed">
                            {profile.emotional_summary.summary}
                          </p>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-3.5 rounded-xl border border-dashed border-white/5 text-center">
                      <p className="text-xs text-slate-500">No AI profile insights loaded. Begin talking with Esona to build your profile.</p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Footer Buttons */}
            <div className="p-6 border-t border-white/5 space-y-3">
              <button
                disabled
                className="w-full py-3 px-4 rounded-xl border border-white/10 text-xs font-semibold text-slate-400 flex items-center justify-center gap-2 bg-white/2 cursor-not-allowed"
              >
                <Edit size={14} />
                Edit Profile (Coming Soon)
              </button>

              <button
                onClick={handleLogout}
                className="w-full py-3 px-4 rounded-xl text-xs font-bold text-white flex items-center justify-center gap-2 hover:bg-red-500/10 hover:text-red-400 border border-transparent hover:border-red-500/20 transition-all duration-300 cursor-pointer"
                style={{
                  background: 'rgba(239, 68, 68, 0.05)',
                }}
              >
                <LogOut size={14} />
                Logout Account
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
