'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Plus,
  MessageCircle,
  Sparkles,
  Edit2,
  Trash2,
  ChevronDown,
  ChevronUp,
  Terminal,
  Activity,
  Award,
  BookOpen,
  FileText,
  Heart,
  Brain,
  Loader2,
  UserCheck,
  ArrowRight,
  Music,
  Sliders,
} from 'lucide-react';
import Navbar from '@/components/layout/Navbar';
import EsonaLogo from '@/components/layout/EsonaLogo';
import ChatContainer from '@/components/chat/ChatContainer';
import MessageBubble from '@/components/chat/MessageBubble';
import FullPageTransition from '@/components/layout/FullPageTransition';
import ChatInput from '@/components/chat/ChatInput';
import TypingIndicator from '@/components/chat/TypingIndicator';
import MoodMusicPanel from '@/components/chat/MoodMusicPanel';
import { useChat } from '@/hooks/useChat';
import { Conversation } from '@/types';
import { getToken, getStoredUser } from '@/api';
import * as api from '@/api';
import { formatDate, truncateText } from '@/utils';
import { skipOnboarding } from '@/api/onboarding';
import { useAuth } from '@/providers/AuthProvider';

const agentSidebarConfig: Record<string, { emoji: string; name: string; role?: string; gradient: string; border: string }> = {
  buddy: { emoji: '💙', name: 'Buddy', gradient: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)', border: 'rgba(56, 189, 248, 0.3)' },
  lex: { emoji: '⚖️', name: 'Lex', role: 'Legal Support', gradient: 'linear-gradient(135deg, #d97706 0%, #b45309 100%)', border: 'rgba(245, 158, 11, 0.3)' },
  maya: { emoji: '👨‍⚕️', name: 'Dr. Maya', role: 'Health Support', gradient: 'linear-gradient(135deg, #059669 0%, #047857 100%)', border: 'rgba(16, 185, 129, 0.3)' },
  ray: { emoji: '👮', name: 'Officer Ray', role: 'Safety & Cyber Support', gradient: 'linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)', border: 'rgba(239, 68, 68, 0.3)' },
  techie: { emoji: '💻', name: 'Techie', role: 'Technical Support', gradient: 'linear-gradient(135deg, #4f46e5 0%, #4338ca 100%)', border: 'rgba(99, 102, 241, 0.3)' },
  mentor: { emoji: '📚', name: 'Mentor', role: 'Study Support', gradient: 'linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%)', border: 'rgba(139, 92, 246, 0.3)' },
  finance: { emoji: '💰', name: 'Finance Coach', gradient: 'linear-gradient(135deg, #db2777 0%, #be185d 100%)', border: 'rgba(236, 72, 153, 0.3)' },
  fitness: { emoji: '🏋️', name: 'Fitness Coach', gradient: 'linear-gradient(135deg, #0d9488 0%, #0f766e 100%)', border: 'rgba(20, 184, 166, 0.3)' },
  relationship: { emoji: '💜', name: 'Relationship Coach', role: 'Relationship Support', gradient: 'linear-gradient(135deg, #a855f7 0%, #7e22ce 100%)', border: 'rgba(168, 85, 247, 0.3)' },
};

interface BackgroundSettingsPanelProps {
  preferences: { enabled: boolean; blur: number; dim: number };
  onSave: (prefs: { enabled: boolean; blur: number; dim: number }) => void;
  containerRef: React.RefObject<HTMLDivElement | null>;
  isMobile: boolean;
  onClose: () => void;
}

function BackgroundSettingsPanel({ preferences, onSave, containerRef, isMobile, onClose }: BackgroundSettingsPanelProps) {
  const [enabled, setEnabled] = useState(preferences.enabled);
  const [blur, setBlur] = useState(preferences.blur);
  const [dim, setDim] = useState(preferences.dim);

  // Sync state if preferences change from outside (e.g. preset selection or initial load)
  useEffect(() => {
    setEnabled(preferences.enabled);
    setBlur(preferences.blur);
    setDim(preferences.dim);
  }, [preferences]);

  const updateGlobalCSS = (b: number, d: number, e: boolean) => {
    if (containerRef.current) {
      if (e) {
        containerRef.current.style.setProperty('--chat-bg-blur', `${b}px`);
        containerRef.current.style.setProperty('--chat-bg-dim', `${d / 100}`);
        const bgLayer = containerRef.current.querySelector('.chat-bg-layer') as HTMLElement;
        if (bgLayer) {
          bgLayer.style.transform = b > 0 ? 'scale(1.03)' : 'scale(1)';
        }
      } else {
        containerRef.current.style.setProperty('--chat-bg-blur', '0px');
        containerRef.current.style.setProperty('--chat-bg-dim', '1');
      }
    }
  };

  const handleToggle = () => {
    const nextEnabled = !enabled;
    setEnabled(nextEnabled);
    updateGlobalCSS(blur, dim, nextEnabled);
    onSave({ enabled: nextEnabled, blur, dim });
  };

  const handleBlurChange = (val: number) => {
    setBlur(val);
    updateGlobalCSS(val, dim, enabled);
    onSave({ enabled, blur: val, dim });
  };

  const handleDimChange = (val: number) => {
    setDim(val);
    updateGlobalCSS(blur, val, enabled);
    onSave({ enabled, blur, dim: val });
  };

  const applyPreset = (presetBlur: number, presetDim: number) => {
    if (!enabled) return;
    setBlur(presetBlur);
    setDim(presetDim);
    updateGlobalCSS(presetBlur, presetDim, true);
    onSave({ enabled: true, blur: presetBlur, dim: presetDim });
  };

  // Determine current preset name if it matches exactly
  const getPresetName = () => {
    if (!enabled) return 'Off';
    if (blur === 0 && dim === 20) return 'Clear';
    if (blur === 5 && dim === 35) return 'Soft';
    if (blur === 10 && dim === 50) return 'Calm';
    if (blur === 20 && dim === 75) return 'Focus';
    return 'Custom';
  };

  const presetName = getPresetName();

  return (
    <div
      className={`p-4 bg-[#070913] border border-cyan-500/15 shadow-[0_0_15px_rgba(6,182,212,0.12)] space-y-4 select-none ${
        isMobile ? 'rounded-t-2xl pb-8 border-t border-x-0 border-b-0' : 'rounded-xl'
      }`}
      style={{
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.45)',
      }}
    >
      {/* Mobile drag handle indicator */}
      {isMobile && (
        <div 
          className="w-12 h-1 bg-white/10 rounded-full mx-auto mb-2 cursor-pointer" 
          onClick={onClose} 
        />
      )}

      {/* Header Info Hierarchy */}
      <div className="flex items-center justify-between border-b border-white/5 pb-2">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold tracking-widest text-slate-400 uppercase">
            BACKGROUND
          </span>
          {presetName === 'Custom' && (
            <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/25 uppercase tracking-wider">
              Custom
            </span>
          )}
          {presetName !== 'Custom' && presetName !== 'Off' && (
            <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/25 uppercase tracking-wider">
              {presetName}
            </span>
          )}
        </div>
        {isMobile && (
          <button 
            onClick={onClose} 
            className="text-slate-400 hover:text-white text-xs font-medium cursor-pointer"
          >
            Close
          </button>
        )}
      </div>

      {/* Main control toggle - Row 1 */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-300">
          Background
        </span>
        <button
          onClick={handleToggle}
          className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors duration-200 focus:outline-none cursor-pointer ${
            enabled ? 'bg-cyan-500' : 'bg-slate-800'
          }`}
        >
          <span
            className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform duration-200 ${
              enabled ? 'translate-x-4.5' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      {/* Quick Appearance Presets - Row 2 */}
      <div className={`space-y-2 border-t border-white/5 pt-3 transition-opacity duration-200 ${enabled ? 'opacity-100' : 'opacity-30 pointer-events-none'}`}>
        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
          Appearance
        </span>
        <div className="grid grid-cols-4 gap-2">
          {(['Clear', 'Soft', 'Calm', 'Focus'] as const).map((name) => {
            const isActive = presetName === name;
            const getPresetValues = (pName: string) => {
              if (pName === 'Clear') return { blur: 0, dim: 20 };
              if (pName === 'Soft') return { blur: 5, dim: 35 };
              if (pName === 'Calm') return { blur: 10, dim: 50 };
              return { blur: 20, dim: 75 };
            };
            const vals = getPresetValues(name);
            return (
              <button
                key={name}
                onClick={() => applyPreset(vals.blur, vals.dim)}
                disabled={!enabled}
                className={`px-2 py-1.5 text-[10px] font-medium rounded transition-all duration-200 cursor-pointer ${
                  isActive
                    ? 'bg-cyan-500/10 border border-cyan-500/40 text-cyan-400 font-semibold'
                    : 'bg-white/5 border border-white/5 text-slate-400 hover:bg-white/10 hover:text-white disabled:hover:text-slate-400'
                }`}
              >
                {name}
              </button>
            );
          })}
        </div>
      </div>

      {/* Sliders - Row 3 */}
      <div className={`space-y-4 pt-1 transition-opacity duration-200 ${enabled ? 'opacity-100' : 'opacity-30 pointer-events-none'}`}>
        {/* Blur slider */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs">
            <span className="text-slate-400">Blur</span>
            <span className="font-medium text-slate-200">{blur}px</span>
          </div>
          <input
            type="range"
            min="0"
            max="24"
            step="1"
            value={blur}
            disabled={!enabled}
            onChange={(e) => handleBlurChange(parseInt(e.target.value, 10))}
            className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-cyan-400"
          />
        </div>

        {/* Dim slider */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs">
            <span className="text-slate-400">Dim</span>
            <span className="font-medium text-slate-200">{dim}%</span>
          </div>
          <input
            type="range"
            min="0"
            max="90"
            step="5"
            value={dim}
            disabled={!enabled}
            onChange={(e) => handleDimChange(parseInt(e.target.value, 10))}
            className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-cyan-400"
          />
        </div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  const router = useRouter();
  const pathname = usePathname();
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [musicPlayerOpen, setMusicPlayerOpen] = useState(false);
  const [bgPanelOpen, setBgPanelOpen] = useState(false);
  const [debugOpen, setDebugOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [skipLoading, setSkipLoading] = useState(false);
  const [welcomeDismissed, setWelcomeDismissed] = useState(false);
  const [isLoadingPage, setIsLoadingPage] = useState(true);
  const [dismissedSuggestions, setDismissedSuggestions] = useState<string[]>([]);

  // Background preferences state
  const [bgPreferences, setBgPreferences] = useState({
    enabled: true,
    blur: 6,
    dim: 40,
  });
  const [videoSrc, setVideoSrc] = useState('/BG2.mp4');

  const [isMobile, setIsMobile] = useState(false);

  // Load preferences from localStorage and select background source
  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener('resize', checkMobile);

    try {
      const stored = localStorage.getItem('esona_chat_background_preferences');
      if (stored) {
        const parsed = JSON.parse(stored);
        if (
          parsed &&
          typeof parsed.enabled === 'boolean' &&
          typeof parsed.blur === 'number' &&
          typeof parsed.dim === 'number'
        ) {
          setBgPreferences(parsed);
        }
      }
    } catch (err) {
      console.warn('Failed to load background preferences:', err);
    }

    const hour = new Date().getHours();
    if (hour >= 18 || hour < 5) {
      setVideoSrc('/BG1.mp4');
    } else {
      setVideoSrc('/BG2.mp4');
    }

    return () => {
      window.removeEventListener('resize', checkMobile);
    };
  }, []);

  // Track accordion state for the Live Agent Debug Panel
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    reasoning: true,
    personality: true,
    emotion: true,
    behavior: true,
    growth: true,
    memories: true,
    strategy: true,
    prompt: true,
  });

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  const [agentInsights, setAgentInsights] = useState<{
    current_mood: string;
    emotion_trend: string;
    important_topics: string[];
    recent_stressors: string[];
  } | null>(null);
  const [isLoadingInsights, setIsLoadingInsights] = useState(false);

  const fetchAgentInsights = useCallback(async () => {
    try {
      setIsLoadingInsights(true);
      const token = getToken();
      if (!token) return;
      const data = await api.apiGet<{
        current_mood: string;
        emotion_trend: string;
        important_topics: string[];
        recent_stressors: string[];
      }>('/api/chat/agent-insights', token);
      setAgentInsights(data);
    } catch (err) {
      console.warn('Failed to fetch agent insights:', err);
    } finally {
      setIsLoadingInsights(false);
    }
  }, []);

  useEffect(() => {
    setMounted(true);
    
    if (typeof window !== 'undefined') {
      window.scrollTo(0, 0);
      const htmlStyle = document.documentElement.style;
      const bodyStyle = document.body.style;
      
      const origHtmlOverflow = htmlStyle.overflow;
      const origBodyOverflow = bodyStyle.overflow;
      
      htmlStyle.overflow = 'hidden';
      bodyStyle.overflow = 'hidden';
      
      return () => {
        htmlStyle.overflow = origHtmlOverflow;
        bodyStyle.overflow = origBodyOverflow;
      };
    }
  }, []);

  const { user, token, refreshUser } = useAuth();

  const [tempSystemEvent, setTempSystemEvent] = useState<{ text: string; id: string } | null>(null);
  const [staggerTypingAgentId, setStaggerTypingAgentId] = useState<string | null>(null);

  const activeConv = conversations.find((c) => c.id === activeConversationId);
  const activeAgentId = activeConv?.agent_id || 'buddy';

  const { messages, setMessages, isLoading, isStreaming, streamPlaceholder, typingAgentId, sendMessage } = useChat({
    conversationId: activeConversationId,
    onboardingCompleted: user?.onboardingCompleted || welcomeDismissed,
  });

  const latestEmotion = [...messages]
    .reverse()
    .find((msg) => msg.emotionDetected)?.emotionDetected || 
    agentInsights?.current_mood || 
    'Neutral';

  useEffect(() => {
    if (debugOpen && activeConversationId) {
      fetchAgentInsights();
    }
  }, [debugOpen, activeConversationId, messages.length, fetchAgentInsights]);

  // Helper: focus the chat input unless the user is actively editing another field
  const focusInput = useCallback(() => {
    if (typeof window === 'undefined') return;
    if (pathname !== '/chat') return;

    // Don't steal focus from title-edit inputs or modals
    const hasModal =
      !!document.querySelector('[role="dialog"]') ||
      !!document.querySelector('.modal');
    if (hasModal) return;

    const activeEl = document.activeElement;
    if (
      activeEl &&
      (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA') &&
      activeEl !== inputRef.current
    ) {
      return;
    }

    // Use rAF + tiny timeout to ensure DOM has settled after streaming
    requestAnimationFrame(() => {
      setTimeout(() => {
        inputRef.current?.focus();
      }, 50);
    });
  }, [pathname]);

  // Focus input once a bot response finishes (isLoading AND isStreaming both drop to false)
  useEffect(() => {
    if (!isLoading && !isStreaming) {
      focusInput();
    }
  }, [messages, isLoading, isStreaming, focusInput]);

  // Focus input whenever the active chat changes (chat switch or new chat)
  useEffect(() => {
    if (activeConversationId) {
      focusInput();
    }
  }, [activeConversationId, focusInput]);

  // Auth check
  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push('/login');
    }
  }, [router]);

  // Load conversations
  const loadConversations = useCallback(async () => {
    const token = getToken();
    if (!token) return;
    try {
      const convos = await api.getConversations(token);
      setConversations(convos);
      if (convos.length > 0) {
        if (!activeConversationId) {
          const buddyConv = convos.find((c) => c.agent_id === 'buddy' || !c.agent_id) || convos[0];
          setActiveConversationId(buddyConv.id);
        }
      }
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  }, [activeConversationId]);

  // Load conversations — hide page loader only after data arrives (min 1000ms)
  useEffect(() => {
    if (!mounted || !token) return;
    const t0 = Date.now();
    loadConversations().finally(() => {
      const elapsed = Date.now() - t0;
      const remaining = Math.max(0, 1000 - elapsed);
      setTimeout(() => setIsLoadingPage(false), remaining);
    });
    // Only run once when token becomes available — subsequent chat switches don't re-show the page loader
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mounted, token]);



  const handleSend = async (content: string) => {
    if (!activeConversationId) return;
    sendMessage(content);
  };

  const handleSkipOnboarding = async () => {
    console.log("SKIP CLICKED");
    const token = getToken();
    if (!token) return;
    setSkipLoading(true);
    try {
      await skipOnboarding(token);
      setWelcomeDismissed(true);
      
      // Load conversations (which automatically creates the Buddy conversation if missing)
      const convos = await api.getConversations(token);
      setConversations(convos);
      
      let conversationId = '';
      if (convos.length > 0) {
        const buddyConv = convos.find((c) => c.agent_id === 'buddy') || convos[0];
        conversationId = buddyConv.id;
        setActiveConversationId(conversationId);
      }
      
      console.log("CONVERSATION CREATED", conversationId);
      
      // Update local storage
      const currentUser = getStoredUser();
      if (currentUser) {
        api.setStoredUser({ ...currentUser, onboardingCompleted: true });
      }
      
      // Sync fresh state from the backend
      try {
        await refreshUser();
      } catch (err) {
        console.warn('Failed to refresh user auth state after skip:', err);
      }

      console.log("CHAT READY");
    } catch (err) {
      console.error('Failed to skip onboarding:', err);
    } finally {
      setSkipLoading(false);
    }
  };

  // Find the latest assistant message with agent analysis data for debug panel
  const lastAssistantMessage = [...messages]
    .reverse()
    .find((m) => m.role === 'assistant' && m.agentAnalysis);
  const debugInfo = lastAssistantMessage?.agentAnalysis;

  const renderProgressBar = (label: string, value: number, color: string) => {
    const percentage = Math.min(100, Math.max(0, value * 100));
    return (
      <div className="mb-3">
        <div className="flex justify-between text-xs mb-1">
          <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
          <span className="font-semibold" style={{ color }}>
            {Math.round(percentage)}%
          </span>
        </div>
        <div className="h-2 w-full rounded-full bg-black/45 overflow-hidden border border-white/5">
          <div
            className="h-full rounded-full transition-all duration-700 ease-out"
            style={{ width: `${percentage}%`, backgroundColor: color }}
          />
        </div>
      </div>
    );
  };

  if (!mounted || isLoadingPage) {
    return (
      <AnimatePresence>
        <FullPageTransition message="Loading your conversations..." />
      </AnimatePresence>
    );
  }

  return (
    <div
      ref={containerRef}
      className="h-screen flex flex-col relative overflow-hidden bg-[#040614]"
      style={{
        ['--chat-bg-blur' as any]: `${bgPreferences.enabled ? bgPreferences.blur : 0}px`,
        ['--chat-bg-dim' as any]: `${bgPreferences.enabled ? bgPreferences.dim / 100 : 1}`,
      }}
    >
      {/* ── Cinematic Background Video Layer ── */}
      {bgPreferences.enabled && (
        <div
          className="absolute inset-0 transition-transform duration-300 chat-bg-layer"
          style={{
            zIndex: 0,
            filter: 'blur(var(--chat-bg-blur))',
            transform: bgPreferences.blur > 0 ? 'scale(1.03)' : 'scale(1)',
            pointerEvents: 'none',
            overflow: 'hidden',
          }}
        >
          <video
            autoPlay
            loop
            muted
            playsInline
            poster="/background.png"
            className="w-full h-full object-cover animate-fade-in"
            style={{ opacity: 0.95 }}
          >
            <source src={videoSrc} type="video/mp4" />
          </video>
        </div>
      )}

      {/* ── Background Dim Overlay Layer ── */}
      <div
        className="absolute inset-0 pointer-events-none transition-colors duration-200"
        style={{
          zIndex: 1,
          backgroundColor: 'rgba(4, 6, 20, var(--chat-bg-dim))',
        }}
      />

      <Navbar />

      <div className="flex-1 flex pt-20 overflow-hidden relative" style={{ zIndex: 1 }}>


        {/* Main chat area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Chat header */}
          <div
            className="flex items-center justify-between px-4 py-3 border-b"
            style={{ borderColor: 'var(--glass-border)' }}
          >
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <EsonaLogo 
                size={36} 
                showParticles={false} 
                glowIntensity="low" 
                aiState={isStreaming ? 'speaking' : isLoading ? 'listening' : 'idle'}
              />
              <div className="min-w-0 flex flex-col">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold truncate" style={{ color: 'var(--text-primary)' }}>
                    Esona
                  </p>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-[var(--text-muted)] flex-shrink-0">
                    AI Wellness Companion
                  </span>
                </div>
                <p className="text-xs flex items-center gap-1" style={{ color: 'var(--accent-emerald)' }}>
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block animate-pulse"></span>
                  Online
                </p>
              </div>
            </div>

            {/* Premium Mood Popover in Header */}
            <div className="relative flex-shrink-0 flex items-center gap-3 mr-3">
              <div className="relative">
                <button
                  onClick={() => setMusicPlayerOpen(!musicPlayerOpen)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all duration-200 cursor-pointer ${
                    musicPlayerOpen 
                      ? 'bg-sky-500/10 border-sky-500/30 text-sky-400' 
                      : 'bg-white/5 border-white/10 text-white/80 hover:bg-white/10'
                  }`}
                >
                  <Music size={13} />
                  <span>Mood</span>
                </button>
                
                <AnimatePresence>
                  {musicPlayerOpen && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 10 }}
                      className="absolute right-0 mt-2 z-50 w-80"
                    >
                      <MoodMusicPanel latestEmotion={latestEmotion} />
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>

            {/* Background Settings Popover */}
            <div className="relative flex-shrink-0 flex items-center gap-3 mr-3">
              <div className="relative">
                <button
                  onClick={() => {
                    setBgPanelOpen(!bgPanelOpen);
                    setMusicPlayerOpen(false); // Close mood when opening bg settings
                  }}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all duration-200 cursor-pointer ${
                    bgPanelOpen 
                      ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400' 
                      : 'bg-white/5 border-white/10 text-white/80 hover:bg-white/10'
                  }`}
                >
                  <Sliders size={13} />
                  <span>Background</span>
                </button>
                
                <AnimatePresence>
                  {bgPanelOpen && !isMobile && (
                    <>
                      {/* Click outside backdrop for desktop */}
                      <div 
                        className="fixed inset-0 z-40 bg-transparent cursor-default" 
                        onClick={() => setBgPanelOpen(false)}
                      />
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 10 }}
                        className="absolute right-0 mt-2 z-50 w-72"
                      >
                        <BackgroundSettingsPanel
                          preferences={bgPreferences}
                          onSave={(prefs) => {
                            setBgPreferences(prefs);
                            localStorage.setItem('esona_chat_background_preferences', JSON.stringify(prefs));
                          }}
                          containerRef={containerRef}
                          isMobile={false}
                          onClose={() => setBgPanelOpen(false)}
                        />
                      </motion.div>
                    </>
                  )}
                </AnimatePresence>
              </div>
            </div>

            {/* Hidden Dev Insights Toggle */}
            <div className="ml-auto flex-shrink-0">
              <button
                onClick={() => setDebugOpen(!debugOpen)}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all duration-300 cursor-pointer"
                style={{
                  background: debugOpen
                    ? 'rgba(56, 189, 248, 0.15)'
                    : 'rgba(255, 255, 255, 0.05)',
                  border: debugOpen
                    ? '1px solid rgba(56, 189, 248, 0.3)'
                    : '1px solid rgba(255, 255, 255, 0.1)',
                  color: debugOpen ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                }}
              >
                <Sparkles size={12} className={debugOpen ? 'animate-pulse' : ''} />
                {debugOpen ? 'Close Insights' : 'Agent Insights'}
              </button>
            </div>
          </div>

          {/* Messages area */}
          <div className="flex-1 overflow-hidden">
            <ChatContainer>
              {!user?.onboardingCompleted && !welcomeDismissed && messages.length === 0 && !isLoading ? (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex flex-col items-center justify-center h-full text-center py-16 px-4"
                >
                  {/* Esona logo */}
                  <div className="mb-6">
                    <EsonaLogo size={64} showParticles glowIntensity="medium" aiState="idle" />
                  </div>

                  {/* Greeting */}
                  <h2
                    className="text-2xl font-bold mb-2 glow-text"
                    style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}
                  >
                    Hi{user?.name ? `, ${user.name}` : ''}! I'm Buddy 💙
                  </h2>
                  <p
                    className="text-base mb-1 max-w-sm"
                    style={{ color: 'var(--text-primary)' }}
                  >
                    How are you feeling today?
                  </p>
                  <p className="text-sm mb-8 max-w-xs" style={{ color: 'var(--text-secondary)' }}>
                    You can tell me anything — I'm here for you. No pressure.
                  </p>

                  {/* Action buttons */}
                  <div className="flex flex-col sm:flex-row gap-3">
                    <motion.button
                      whileHover={{ scale: 1.03 }}
                      whileTap={{ scale: 0.97 }}
                      onClick={() => router.push('/onboarding')}
                      className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-300 cursor-pointer"
                      style={{
                        background: 'linear-gradient(135deg, rgba(34,211,238,0.15), rgba(99,102,241,0.1))',
                        border: '1px solid rgba(34,211,238,0.25)',
                        color: 'var(--accent-cyan)',
                      }}
                    >
                      <UserCheck size={16} />
                      Tell me about yourself
                    </motion.button>

                    <motion.button
                      whileHover={{ scale: 1.03 }}
                      whileTap={{ scale: 0.97 }}
                      onClick={handleSkipOnboarding}
                      disabled={skipLoading}
                      className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-300 cursor-pointer"
                      style={{
                        background: 'rgba(255,255,255,0.04)',
                        border: '1px solid rgba(255,255,255,0.1)',
                        color: 'var(--text-secondary)',
                      }}
                    >
                      {skipLoading ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        <ArrowRight size={14} />
                      )}
                      {skipLoading ? 'Starting...' : 'Skip — just chat'}
                    </motion.button>
                  </div>

                  <p className="text-xs mt-8" style={{ color: 'var(--text-muted)' }}>
                    Everything here stays between us. 💙
                  </p>
                </motion.div>
              ) : (
                <>
                  {messages.map((message) => {
                    return (
                      <div key={message.id} className="space-y-3">
                        <MessageBubble message={message} />
                      </div>
                    );
                  })}
                  <AnimatePresence>
                    {tempSystemEvent && (
                      <motion.div
                        initial={{ opacity: 0, y: 10, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        className="flex justify-center my-4"
                      >
                        <span className="px-4 py-1.5 rounded-full text-xs font-medium bg-white/5 border border-white/10 text-[var(--text-secondary)] shadow-sm backdrop-blur-md">
                          {tempSystemEvent.text}
                        </span>
                      </motion.div>
                    )}
                    {((isLoading && !isStreaming) || streamPlaceholder) && (
                      <TypingIndicator agentId={typingAgentId || activeAgentId} />
                    )}
                    {staggerTypingAgentId && (
                      <TypingIndicator agentId={staggerTypingAgentId} />
                    )}
                  </AnimatePresence>
                </>
              )}
            </ChatContainer>
          </div>

          {/* Input */}
          <ChatInput ref={inputRef} onSend={handleSend} disabled={isLoading} />
        </div>

        {/* Live Agent Debug Panel */}
        <AnimatePresence>
          {debugOpen && (
            <motion.aside
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 380, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.3, ease: 'easeInOut' }}
              className="h-full overflow-hidden flex-shrink-0 border-l"
              style={{
                borderColor: 'var(--glass-border)',
                background: 'rgba(10, 16, 32, 0.75)',
                backdropFilter: 'blur(16px)',
              }}
            >
              <div className="h-full flex flex-col p-4 w-[380px] overflow-y-auto space-y-4 animate-fadeIn">
                <div className="flex items-center gap-2 pb-2 border-b border-white/10">
                  <Terminal size={16} className="text-sky-400" />
                  <h3 className="text-sm font-semibold tracking-wide uppercase text-sky-400">
                    Agent Insights & Diagnostics
                  </h3>
                </div>

                {/* Premium Overview Card */}
                {isLoadingInsights && !agentInsights ? (
                  <div className="flex flex-col items-center justify-center py-6 text-center">
                    <Loader2 size={24} className="animate-spin text-sky-400 mb-2" />
                    <p className="text-xs text-slate-400">Compiling premium insights...</p>
                  </div>
                ) : (
                  <div
                    className="rounded-2xl p-5 border relative overflow-hidden transition-all duration-500 hover:shadow-[0_8px_32px_rgba(56,189,248,0.15)]"
                    style={{
                      background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.6) 0%, rgba(30, 41, 59, 0.4) 100%)',
                      borderColor: 'rgba(56, 189, 248, 0.2)',
                      backdropFilter: 'blur(12px)',
                    }}
                  >
                    {/* Glow effect */}
                    <div className="absolute -right-12 -top-12 w-24 h-24 rounded-full bg-sky-500/10 blur-2xl pointer-events-none" />
                    <div className="absolute -left-12 -bottom-12 w-24 h-24 rounded-full bg-violet-500/10 blur-2xl pointer-events-none" />

                    <h4 className="text-xs font-semibold tracking-wider text-sky-400 uppercase mb-4 flex items-center gap-1.5">
                      <Sparkles size={12} className="text-sky-400 animate-pulse" />
                      Wellness Overview
                    </h4>

                    <div className="space-y-4">
                      {/* Current Mood & Trend */}
                      <div className="grid grid-cols-2 gap-3">
                        <div className="bg-white/5 rounded-xl p-3 border border-white/5">
                          <span className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1">Current Mood</span>
                          <span className="text-sm font-bold text-white flex items-center gap-1.5">
                            {(() => {
                              const mood = agentInsights?.current_mood || 'Neutral';
                              let emoji = '😐';
                              let colorClass = 'text-slate-300';
                              if (mood.toLowerCase().includes('sad')) { emoji = '😢'; colorClass = 'text-blue-400'; }
                              else if (mood.toLowerCase().includes('anger') || mood.toLowerCase().includes('angry')) { emoji = '😠'; colorClass = 'text-red-400'; }
                              else if (mood.toLowerCase().includes('fear') || mood.toLowerCase().includes('anxi')) { emoji = '😰'; colorClass = 'text-amber-400'; }
                              else if (mood.toLowerCase().includes('happ') || mood.toLowerCase().includes('joy')) { emoji = '😊'; colorClass = 'text-emerald-400'; }
                              else if (mood.toLowerCase().includes('excit')) { emoji = '🥳'; colorClass = 'text-pink-400'; }
                              else if (mood.toLowerCase().includes('frust')) { emoji = '😤'; colorClass = 'text-orange-400'; }
                              else if (mood.toLowerCase().includes('lone')) { emoji = '🥺'; colorClass = 'text-violet-400'; }
                              return (
                                <>
                                  <span>{emoji}</span>
                                  <span className={colorClass}>{mood}</span>
                                </>
                              );
                            })()}
                          </span>
                        </div>

                        <div className="bg-white/5 rounded-xl p-3 border border-white/5">
                          <span className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1">Emotion Trend</span>
                          <span className="text-sm font-bold text-white flex items-center gap-1.5">
                            <span className="text-sky-400">✨</span>
                            <span className="text-slate-200">{agentInsights?.emotion_trend || 'Stable'}</span>
                          </span>
                        </div>
                      </div>

                      {/* Important Topics */}
                      <div>
                        <span className="text-[10px] text-slate-400 uppercase tracking-wider block mb-2">Important Topics</span>
                        <div className="flex flex-wrap gap-1.5">
                          {agentInsights?.important_topics && agentInsights.important_topics.length > 0 ? (
                            agentInsights.important_topics.map((topic, i) => (
                              <span
                                key={i}
                                className="text-[10px] px-2.5 py-1 rounded-full border bg-sky-950/20 text-sky-300 border-sky-500/20 font-medium"
                              >
                                {topic}
                              </span>
                            ))
                          ) : (
                            <span className="text-[10px] text-slate-500 italic">None identified yet</span>
                          )}
                        </div>
                      </div>

                      {/* Recent Stressors */}
                      <div>
                        <span className="text-[10px] text-slate-400 uppercase tracking-wider block mb-2">Recent Stressors</span>
                        <div className="flex flex-wrap gap-1.5">
                          {agentInsights?.recent_stressors && agentInsights.recent_stressors.length > 0 && agentInsights.recent_stressors[0] !== 'None Identified Yet' ? (
                            agentInsights.recent_stressors.map((stressor, i) => (
                              <span
                                key={i}
                                className="text-[10px] px-2.5 py-1 rounded-full border bg-rose-950/20 text-rose-300 border-rose-500/20 font-medium"
                              >
                                ⚠️ {stressor}
                              </span>
                            ))
                          ) : (
                            <span className="text-[10px] px-2.5 py-1 rounded-full border bg-emerald-950/20 text-emerald-300 border-emerald-500/20 font-medium">
                              ✅ All Clear
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div className="pt-2 pb-1 border-b border-white/5">
                  <h4 className="text-[10px] font-bold tracking-wider text-slate-500 uppercase">
                    Developer Multi-Agent Logs
                  </h4>
                </div>

                {!debugInfo ? (
                  <div className="py-12 text-center">
                    <Brain size={32} className="mx-auto mb-3 text-slate-500 animate-pulse" />
                    <p className="text-xs text-slate-400 max-w-[280px] mx-auto leading-relaxed">
                      No active multi-agent insights loaded.
                      <br />
                      Send a message or select a chat thread to view analysis.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-3 pb-8">
                    {/* 0. Hidden Reasoning */}
                    {debugInfo.hidden_reasoning && (
                      <div className="rounded-xl border border-white/10 bg-white/5 overflow-hidden">
                        <button
                          onClick={() => toggleSection('reasoning')}
                          className="w-full flex items-center justify-between p-3 text-xs font-semibold text-white/90 hover:bg-white/5 transition-colors"
                        >
                          <div className="flex items-center gap-2">
                            <Terminal size={14} className="text-amber-400" />
                            <span>0. Humanizer - Hidden Reasoning</span>
                          </div>
                          {expandedSections.reasoning ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        </button>
                        <AnimatePresence>
                          {expandedSections.reasoning && (
                            <motion.div
                              initial={{ height: 0 }}
                              animate={{ height: 'auto' }}
                              exit={{ height: 0 }}
                              className="overflow-hidden bg-black/25 text-[11px] p-3 border-t border-white/5 text-slate-300"
                            >
                              <pre className="font-mono text-amber-300 bg-black/45 p-2 rounded border border-white/5 whitespace-pre-wrap leading-relaxed max-h-[220px] overflow-y-auto">
                                {debugInfo.hidden_reasoning}
                              </pre>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    )}

                    {/* 1. Personality Agent */}
                    <div className="rounded-xl border border-white/10 bg-white/5 overflow-hidden">
                      <button
                        onClick={() => toggleSection('personality')}
                        className="w-full flex items-center justify-between p-3 text-xs font-semibold text-white/90 hover:bg-white/5 transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <Brain size={14} className="text-sky-400" />
                          <span>1. Personality Agent</span>
                        </div>
                        {expandedSections.personality ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </button>
                      <AnimatePresence>
                        {expandedSections.personality && (
                          <motion.div
                            initial={{ height: 0 }}
                            animate={{ height: 'auto' }}
                            exit={{ height: 0 }}
                            className="overflow-hidden bg-black/25 text-[11px] p-3 space-y-2 border-t border-white/5 text-slate-300"
                          >
                            <div>
                              <span className="font-semibold text-slate-400">Confidence Level:</span>
                              <p className="mt-0.5">{debugInfo.personality_agent?.confidence_level || 'N/A'}</p>
                            </div>
                            <div>
                              <span className="font-semibold text-slate-400">Communication Style:</span>
                              <p className="mt-0.5">{debugInfo.personality_agent?.communication_style || 'N/A'}</p>
                            </div>
                            <div>
                              <span className="font-semibold text-slate-400">Emotional Openness:</span>
                              <p className="mt-0.5">{debugInfo.personality_agent?.emotional_openness || 'N/A'}</p>
                            </div>
                            <div>
                              <span className="font-semibold text-slate-400">Introvert/Extrovert:</span>
                              <p className="mt-0.5">{debugInfo.personality_agent?.introvert_extrovert_tendencies || 'N/A'}</p>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>

                    {/* 2. Emotion Agent */}
                    <div className="rounded-xl border border-white/10 bg-white/5 overflow-hidden">
                      <button
                        onClick={() => toggleSection('emotion')}
                        className="w-full flex items-center justify-between p-3 text-xs font-semibold text-white/90 hover:bg-white/5 transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <Heart size={14} className="text-rose-400" />
                          <span>2. Emotion Agent</span>
                        </div>
                        {expandedSections.emotion ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </button>
                      <AnimatePresence>
                        {expandedSections.emotion && (
                          <motion.div
                            initial={{ height: 0 }}
                            animate={{ height: 'auto' }}
                            exit={{ height: 0 }}
                            className="overflow-hidden bg-black/25 text-[11px] p-3 border-t border-white/5 text-slate-300"
                          >
                            <div className="mb-3">
                              <span className="font-semibold text-slate-400">Primary Emotion: </span>
                              <span className="text-rose-400 font-semibold uppercase">
                                {debugInfo.emotion_agent?.primary_emotion || 'N/A'}
                              </span>
                            </div>
                            {renderProgressBar('Stress', debugInfo.emotion_agent?.stress || 0, '#f87171')}
                            {renderProgressBar('Anxiety', debugInfo.emotion_agent?.anxiety || 0, '#fbbf24')}
                            {renderProgressBar('Sadness', debugInfo.emotion_agent?.sadness || 0, '#60a5fa')}
                            {renderProgressBar('Burnout', debugInfo.emotion_agent?.burnout || 0, '#a78bfa')}
                            <div className="mt-2 pt-2 border-t border-white/5 flex justify-between">
                              <span className="font-semibold text-slate-400">Emotional Intensity:</span>
                              <span className="font-bold text-rose-400">
                                {debugInfo.emotion_agent?.emotional_intensity || 0} / 10
                              </span>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>

                    {/* 3. Behavior Agent */}
                    <div className="rounded-xl border border-white/10 bg-white/5 overflow-hidden">
                      <button
                        onClick={() => toggleSection('behavior')}
                        className="w-full flex items-center justify-between p-3 text-xs font-semibold text-white/90 hover:bg-white/5 transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <Activity size={14} className="text-emerald-400" />
                          <span>3. Behavior Agent</span>
                        </div>
                        {expandedSections.behavior ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </button>
                      <AnimatePresence>
                        {expandedSections.behavior && (
                          <motion.div
                            initial={{ height: 0 }}
                            animate={{ height: 'auto' }}
                            exit={{ height: 0 }}
                            className="overflow-hidden bg-black/25 text-[11px] p-3 space-y-2 border-t border-white/5 text-slate-300"
                          >
                            <div>
                              <span className="font-semibold text-slate-400">Productivity Patterns:</span>
                              <p className="mt-0.5">{debugInfo.behavior_agent?.productivity_patterns || 'N/A'}</p>
                            </div>
                            <div>
                              <span className="font-semibold text-slate-400">Sleep Issues:</span>
                              <p className="mt-0.5">{debugInfo.behavior_agent?.sleep_issues || 'N/A'}</p>
                            </div>
                            <div>
                              <span className="font-semibold text-slate-400">Procrastination:</span>
                              <span className="ml-1.5 px-2 py-0.5 rounded bg-white/10 text-emerald-400 font-semibold uppercase text-[9px]">
                                {debugInfo.behavior_agent?.procrastination || 'N/A'}
                              </span>
                            </div>
                            <div>
                              <span className="font-semibold text-slate-400">Routine Consistency:</span>
                              <p className="mt-0.5">{debugInfo.behavior_agent?.routine_consistency || 'N/A'}</p>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>

                    {/* 4. Growth Agent */}
                    <div className="rounded-xl border border-white/10 bg-white/5 overflow-hidden">
                      <button
                        onClick={() => toggleSection('growth')}
                        className="w-full flex items-center justify-between p-3 text-xs font-semibold text-white/90 hover:bg-white/5 transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <Award size={14} className="text-amber-400" />
                          <span>4. Growth Agent</span>
                        </div>
                        {expandedSections.growth ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </button>
                      <AnimatePresence>
                        {expandedSections.growth && (
                          <motion.div
                            initial={{ height: 0 }}
                            animate={{ height: 'auto' }}
                            exit={{ height: 0 }}
                            className="overflow-hidden bg-black/25 text-[11px] p-3 space-y-2 border-t border-white/5 text-slate-300"
                          >
                            <div>
                              <span className="font-semibold text-slate-400">Emotional Improvement:</span>
                              <p className="mt-0.5">{debugInfo.growth_agent?.emotional_improvement || 'N/A'}</p>
                            </div>
                            <div>
                              <span className="font-semibold text-slate-400">Motivation Status:</span>
                              <p className="mt-0.5">{debugInfo.growth_agent?.motivation || 'N/A'}</p>
                            </div>
                            <div>
                              <span className="font-semibold text-slate-400">Self-Awareness Level:</span>
                              <p className="mt-0.5">{debugInfo.growth_agent?.self_awareness || 'N/A'}</p>
                            </div>
                            <div>
                              <span className="font-semibold text-slate-400">Mental Growth Markers:</span>
                              <p className="mt-0.5">{debugInfo.growth_agent?.mental_growth || 'N/A'}</p>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>

                    {/* 5. Retrieved Memories */}
                    <div className="rounded-xl border border-white/10 bg-white/5 overflow-hidden">
                      <button
                        onClick={() => toggleSection('memories')}
                        className="w-full flex items-center justify-between p-3 text-xs font-semibold text-white/90 hover:bg-white/5 transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <BookOpen size={14} className="text-purple-400" />
                          <span>5. Retrieved Memories ({debugInfo.retrieved_memories?.length || 0})</span>
                        </div>
                        {expandedSections.memories ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </button>
                      <AnimatePresence>
                        {expandedSections.memories && (
                          <motion.div
                            initial={{ height: 0 }}
                            animate={{ height: 'auto' }}
                            exit={{ height: 0 }}
                            className="overflow-hidden bg-black/25 text-[11px] p-3 border-t border-white/5 text-slate-300 space-y-2"
                          >
                            {!debugInfo.retrieved_memories || debugInfo.retrieved_memories.length === 0 ? (
                              <p className="text-slate-400 italic">No memories recalled for this query.</p>
                            ) : (
                              debugInfo.retrieved_memories.map((mem: any, i: number) => (
                                <div key={i} className="p-2 rounded bg-white/5 border border-white/5 leading-normal">
                                  <p className="text-white/90 font-medium">"{mem.content}"</p>
                                  {mem.metadata && (
                                    <div className="flex gap-1.5 mt-1 text-[9px] text-slate-400 flex-wrap">
                                      {mem.metadata.emotion && <span>Emotion: {mem.metadata.emotion}</span>}
                                      {mem.metadata.stress_level && <span>Stress: {mem.metadata.stress_level}/10</span>}
                                      {mem.metadata.trigger && <span>Trigger: {mem.metadata.trigger}</span>}
                                    </div>
                                  )}
                                </div>
                              ))
                            )}
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>

                    {/* 6. Response Strategy */}
                    <div className="rounded-xl border border-white/10 bg-white/5 overflow-hidden">
                      <button
                        onClick={() => toggleSection('strategy')}
                        className="w-full flex items-center justify-between p-3 text-xs font-semibold text-white/90 hover:bg-white/5 transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <Activity size={14} className="text-cyan-400" />
                          <span>6. Final Response Strategy</span>
                        </div>
                        {expandedSections.strategy ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </button>
                      <AnimatePresence>
                        {expandedSections.strategy && (
                          <motion.div
                            initial={{ height: 0 }}
                            animate={{ height: 'auto' }}
                            exit={{ height: 0 }}
                            className="overflow-hidden bg-black/25 text-[11px] p-3 border-t border-white/5 text-slate-300 space-y-2"
                          >
                            <div>
                              <span className="font-semibold text-slate-400">Target Tone:</span>
                              <span className="ml-2 px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-400 font-bold uppercase text-[10px] tracking-wider">
                                {debugInfo.response_strategy?.tone || 'N/A'}
                              </span>
                            </div>
                            <div>
                              <span className="font-semibold text-slate-400">Support Strategy:</span>
                              <p className="mt-1 leading-relaxed text-slate-200">
                                {debugInfo.response_strategy?.strategy || 'N/A'}
                              </p>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>

                    {/* 7. Orchestrated Prompt Summary */}
                    <div className="rounded-xl border border-white/10 bg-white/5 overflow-hidden">
                      <button
                        onClick={() => toggleSection('prompt')}
                        className="w-full flex items-center justify-between p-3 text-xs font-semibold text-white/90 hover:bg-white/5 transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <FileText size={14} className="text-slate-400" />
                          <span>7. Orchestrated Prompt Summary</span>
                        </div>
                        {expandedSections.prompt ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </button>
                      <AnimatePresence>
                        {expandedSections.prompt && (
                          <motion.div
                            initial={{ height: 0 }}
                            animate={{ height: 'auto' }}
                            exit={{ height: 0 }}
                            className="overflow-hidden bg-black/25 text-[10px] p-3 border-t border-white/5 text-slate-300"
                          >
                            <pre className="font-mono text-sky-300 bg-black/45 p-2 rounded border border-white/5 whitespace-pre-wrap leading-relaxed max-h-[220px] overflow-y-auto">
                              {debugInfo.orchestrated_prompt_summary || 'N/A'}
                            </pre>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </div>
                )}
              </div>
            </motion.aside>
          )}
        </AnimatePresence>
      </div>

      {/* Mobile Background Settings Bottom Sheet */}
      <AnimatePresence>
        {bgPanelOpen && isMobile && (
          <>
            {/* Click-outside backdrop for mobile */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.5 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/60"
              onClick={() => setBgPanelOpen(false)}
            />
            <motion.div
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 350 }}
              className="fixed bottom-0 left-0 right-0 w-full z-50"
            >
              <BackgroundSettingsPanel
                preferences={bgPreferences}
                onSave={(prefs) => {
                  setBgPreferences(prefs);
                  localStorage.setItem('esona_chat_background_preferences', JSON.stringify(prefs));
                }}
                containerRef={containerRef}
                isMobile={true}
                onClose={() => setBgPanelOpen(false)}
              />
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}


