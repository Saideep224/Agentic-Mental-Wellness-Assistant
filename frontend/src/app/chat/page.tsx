'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Plus,
  MessageCircle,
  PanelLeftClose,
  PanelLeftOpen,
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
} from 'lucide-react';
import Navbar from '@/components/layout/Navbar';
import EsonaLogo from '@/components/layout/EsonaLogo';
import ChatContainer from '@/components/chat/ChatContainer';
import MessageBubble from '@/components/chat/MessageBubble';
import FullPageTransition from '@/components/layout/FullPageTransition';
import ChatInput from '@/components/chat/ChatInput';
import TypingIndicator from '@/components/chat/TypingIndicator';
import { useChat } from '@/hooks/useChat';
import { Conversation } from '@/types';
import { getToken, getStoredUser } from '@/api';
import * as api from '@/api';
import { formatDate, truncateText } from '@/utils';
import { skipOnboarding } from '@/api/onboarding';

const agentSidebarConfig: Record<string, { emoji: string; name: string; role?: string; gradient: string; border: string }> = {
  buddy: { emoji: '💙', name: 'Esona', gradient: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)', border: 'rgba(56, 189, 248, 0.3)' },
  lex: { emoji: '⚖️', name: 'Lex', role: 'Legal Support', gradient: 'linear-gradient(135deg, #d97706 0%, #b45309 100%)', border: 'rgba(245, 158, 11, 0.3)' },
  maya: { emoji: '👨‍⚕️', name: 'Dr. Maya', role: 'Health Support', gradient: 'linear-gradient(135deg, #059669 0%, #047857 100%)', border: 'rgba(16, 185, 129, 0.3)' },
  ray: { emoji: '👮', name: 'Officer Ray', role: 'Safety & Cyber Support', gradient: 'linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)', border: 'rgba(239, 68, 68, 0.3)' },
  techie: { emoji: '💻', name: 'Techie', role: 'Technical Support', gradient: 'linear-gradient(135deg, #4f46e5 0%, #4338ca 100%)', border: 'rgba(99, 102, 241, 0.3)' },
  mentor: { emoji: '📚', name: 'Mentor', role: 'Study Support', gradient: 'linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%)', border: 'rgba(139, 92, 246, 0.3)' },
  finance: { emoji: '💰', name: 'Finance Coach', gradient: 'linear-gradient(135deg, #db2777 0%, #be185d 100%)', border: 'rgba(236, 72, 153, 0.3)' },
  fitness: { emoji: '🏋️', name: 'Fitness Coach', gradient: 'linear-gradient(135deg, #0d9488 0%, #0f766e 100%)', border: 'rgba(20, 184, 166, 0.3)' },
  relationship: { emoji: '💜', name: 'Relationship Coach', role: 'Relationship Support', gradient: 'linear-gradient(135deg, #a855f7 0%, #7e22ce 100%)', border: 'rgba(168, 85, 247, 0.3)' },
};

export default function ChatPage() {
  const router = useRouter();
  const pathname = usePathname();
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(
    typeof window !== 'undefined' ? window.innerWidth > 768 : true
  );
  const [debugOpen, setDebugOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [skipLoading, setSkipLoading] = useState(false);
  const [isLoadingPage, setIsLoadingPage] = useState(true);
  const [dismissedSuggestions, setDismissedSuggestions] = useState<string[]>([]);

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
  }, []);

  const user = mounted ? getStoredUser() : null;

  const [connectingSpecialistId, setConnectingSpecialistId] = useState<string | null>(null);
  const [removingSpecialistId, setRemovingSpecialistId] = useState<string | null>(null);
  const [tempSystemEvent, setTempSystemEvent] = useState<{ text: string; id: string } | null>(null);
  const [staggerTypingAgentId, setStaggerTypingAgentId] = useState<string | null>(null);

  const activeConv = conversations.find((c) => c.id === activeConversationId);
  const activeAgentId = activeConv?.agent_id || 'buddy';
  const activeSpecialistId = activeConv?.active_specialists?.[0] || null;

  const { messages, setMessages, isLoading, isStreaming, streamPlaceholder, typingAgentId, sendMessage } = useChat({
    conversationId: activeConversationId,
    activeSpecialistId,
    onSpecialistAction: (action, specialistId) => {
      if (!activeConversationId) return;
      setConversations((prev) =>
        prev.map((conv) => {
          if (conv.id !== activeConversationId) return conv;
          const current: string[] = (conv as any).active_specialists || [];
          let updated: string[];
          if (action === 'invited') {
            updated = current.includes(specialistId) ? current : [...current, specialistId];
          } else {
            updated = current.filter((s) => s !== specialistId);
          }
          return { ...conv, active_specialists: updated } as any;
        })
      );
    },
  });

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
          const buddyConv = convos.find((c) => c.agent_id === 'buddy') || convos[0];
          setActiveConversationId(buddyConv.id);
        }
      }
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  }, [activeConversationId]);

  // Load conversations — hide page loader only after data arrives (min 1000ms)
  useEffect(() => {
    if (!mounted) return;
    const t0 = Date.now();
    loadConversations().finally(() => {
      const elapsed = Date.now() - t0;
      const remaining = Math.max(0, 1000 - elapsed);
      setTimeout(() => setIsLoadingPage(false), remaining);
    });
    // Only run once on mount — subsequent chat switches don't re-show the page loader
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mounted]);

  const handleConnectSpecialist = async (specialistId: string) => {
    const token = api.getToken();
    if (!token) return;

    setConnectingSpecialistId(specialistId);

    try {
      // Find if a conversation with this expert already exists in state
      const existingConv = conversations.find(c => c.agent_id === specialistId);
      if (existingConv) {
        setActiveConversationId(existingConv.id);
      } else {
        // If it does not exist, create it via API
        const config = agentSidebarConfig[specialistId] || { name: specialistId };
        const res = await api.createConversation(token, config.name, specialistId);
        setConversations((prev) => [res, ...prev]);
        setActiveConversationId(res.id);
      }
    } catch (err) {
      console.error('Failed to open expert conversation:', err);
    } finally {
      setConnectingSpecialistId(null);
    }
  };

  const handleDisconnectSpecialist = async (specialistId: string) => {
    if (!activeConversationId) return;
    const token = api.getToken();
    if (!token) return;

    setRemovingSpecialistId(specialistId);

    try {
      const newMsgs = await api.disconnectSpecialist(activeConversationId, token);
      
      // Update conversations first
      await loadConversations();
      
      setRemovingSpecialistId(null);

      // Show "<Agent Name> left the conversation." toast banner for 2 seconds
      const specName = agentSidebarConfig[specialistId]?.name || specialistId;
      setTempSystemEvent({ text: `${specName} left the conversation.`, id: Date.now().toString() });
      setTimeout(() => {
        setTempSystemEvent(null);
      }, 2000);

      // Sequentially stagger appending the disconnect messages (farewell from Buddy)
      let currentIdx = 0;
      const appendNextMessage = () => {
        if (currentIdx >= newMsgs.length) {
          setStaggerTypingAgentId(null);
          focusInput();
          return;
        }

        const msg = newMsgs[currentIdx];
        setStaggerTypingAgentId('buddy');

        setTimeout(() => {
          setMessages((prev) => [...prev, {
            ...msg,
            timestamp: new Date(msg.timestamp)
          }]);
          currentIdx++;
          appendNextMessage();
        }, 800); // 800ms delay for farewell message typing
      };

      appendNextMessage();

    } catch (err) {
      console.error('Failed to disconnect specialist:', err);
      setRemovingSpecialistId(null);
    }
  };

  const handleSend = async (content: string) => {
    if (!activeConversationId) return;
    sendMessage(content);
  };

  const handleSkipOnboarding = async () => {
    const token = getToken();
    if (!token) return;
    setSkipLoading(true);
    try {
      await skipOnboarding(token);
      // Reload to get fresh user state (onboarding_completed = true)
      window.location.reload();
    } catch (err) {
      console.error('Failed to skip onboarding:', err);
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
    <div className="h-screen flex flex-col relative overflow-hidden">
      {/* Immersive blur overlay */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          background: 'rgba(8, 12, 28, 0.45)',
          zIndex: 0,
        }}
      />

      <Navbar />

      <div className="flex-1 flex pt-20 overflow-hidden relative" style={{ zIndex: 1 }}>
        {/* Sidebar */}
        <AnimatePresence>
          {sidebarOpen && (
            <motion.aside
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 280, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.3, ease: 'easeInOut' }}
              className="h-full overflow-hidden flex-shrink-0 border-r"
              style={{ borderColor: 'var(--glass-border)' }}
            >
              <div className="h-full flex flex-col p-3 w-[280px]">
                {/* Contacts Header */}
                <div className="px-3 py-2 flex items-center justify-between mb-4 border-b border-white/5">
                  <span className="font-bold text-base tracking-wide text-[var(--text-primary)]">
                    Contacts
                  </span>
                  <div className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    <span className="text-[10px] text-emerald-400 font-semibold uppercase">Online</span>
                  </div>
                </div>

                {/* Contacts list */}
                <div className="flex-1 overflow-y-auto space-y-1 pr-1 custom-scrollbar">
                  {(() => {
                    const buddyConvos = conversations.filter((c) => c.agent_id === 'buddy' || !c.agent_id);
                    
                    const EXPERTS_LIST = [
                      { id: 'maya', name: 'Dr. Maya', role: 'Health Support', emoji: '👨‍⚕️', gradient: 'linear-gradient(135deg, #059669 0%, #047857 100%)', border: 'rgba(16, 185, 129, 0.3)' },
                      { id: 'finance', name: 'Finance Coach', role: 'Financial Support', emoji: '💰', gradient: 'linear-gradient(135deg, #db2777 0%, #be185d 100%)', border: 'rgba(236, 72, 153, 0.3)' },
                      { id: 'mentor', name: 'Career Coach', role: 'Career Support', emoji: '📚', gradient: 'linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%)', border: 'rgba(139, 92, 246, 0.3)' },
                      { id: 'relationship', name: 'Relationship Coach', role: 'Relationship Support', emoji: '💜', gradient: 'linear-gradient(135deg, #a855f7 0%, #7e22ce 100%)', border: 'rgba(168, 85, 247, 0.3)' },
                      { id: 'lex', name: 'Legal Advisor', role: 'Legal Support', emoji: '⚖️', gradient: 'linear-gradient(135deg, #d97706 0%, #b45309 100%)', border: 'rgba(245, 158, 11, 0.3)' },
                    ];

                    const renderContactItem = (convo: Conversation) => {
                      const info = agentSidebarConfig[convo.agent_id || 'buddy'] || {
                        name: convo.title || 'Support Agent',
                        emoji: '🤝',
                        gradient: 'linear-gradient(135deg, #64748b 0%, #475569 100%)',
                        border: 'rgba(148, 163, 184, 0.3)',
                        role: undefined
                      };
                      const isActive = activeConversationId === convo.id;
                      
                      return (
                        <div
                          key={convo.id}
                          onClick={() => {
                            setActiveConversationId(convo.id);
                          }}
                          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 cursor-pointer border"
                          style={{
                            background: isActive
                              ? 'rgba(56, 189, 248, 0.08)'
                              : 'transparent',
                            borderColor: isActive
                              ? 'rgba(56, 189, 248, 0.15)'
                              : 'transparent',
                          }}
                        >
                          {/* Avatar */}
                          <div className="relative flex-shrink-0">
                            <div
                              className="w-10 h-10 rounded-full flex items-center justify-center text-lg select-none"
                              style={{
                                background: info.gradient,
                                boxShadow: isActive ? `0 0 10px ${info.border}` : 'none',
                              }}
                            >
                              {info.emoji}
                            </div>
                            <div 
                              className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full border border-[#090d1a] bg-emerald-500"
                              title="Online"
                            />
                          </div>

                          {/* Details */}
                          <div className="flex-1 min-w-0 flex flex-col justify-center">
                            <div className="flex items-center justify-between gap-1">
                              <span className="font-semibold text-xs text-[var(--text-primary)] truncate">
                                {info.name}
                              </span>
                              {convo.lastMessageTimestamp && (
                                <span className="text-[9px] text-[var(--text-muted)] flex-shrink-0">
                                  {formatDate(convo.lastMessageTimestamp)}
                                </span>
                              )}
                            </div>
                            {info.role && (
                              <span className="text-[9px] text-[var(--text-muted)] font-medium -mt-0.5">
                                {info.role}
                              </span>
                            )}
                            {convo.lastMessage ? (
                              <p className="text-[11px] text-[var(--text-muted)] truncate mt-0.5 leading-tight">
                                {convo.lastMessage}
                              </p>
                            ) : (
                              <p className="text-[11px] text-[var(--text-muted)] italic truncate mt-0.5 leading-tight">
                                No messages yet
                              </p>
                            )}
                          </div>
                        </div>
                      );
                    };

                    const renderStaticExpertItem = (expert: typeof EXPERTS_LIST[0]) => {
                      // Check if a conversation for this expert already exists
                      const existingConv = conversations.find((c) => c.agent_id === expert.id);
                      const isActive = existingConv ? activeConversationId === existingConv.id : false;
                      
                      const handleSelect = async () => {
                        if (existingConv) {
                          setActiveConversationId(existingConv.id);
                        } else {
                          // Create conversation on demand
                          try {
                            const token = getToken();
                            if (!token) return;
                            const res = await api.createConversation(token, expert.name, expert.id);
                            setConversations((prev) => [res, ...prev]);
                            setActiveConversationId(res.id);
                          } catch (err) {
                            console.error('Failed to create expert conversation:', err);
                          }
                        }
                      };

                      return (
                        <div
                          key={expert.id}
                          onClick={handleSelect}
                          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 cursor-pointer border"
                          style={{
                            background: isActive
                              ? 'rgba(56, 189, 248, 0.08)'
                              : 'transparent',
                            borderColor: isActive
                              ? 'rgba(56, 189, 248, 0.15)'
                              : 'transparent',
                          }}
                        >
                          {/* Avatar */}
                          <div className="relative flex-shrink-0">
                            <div
                              className="w-10 h-10 rounded-full flex items-center justify-center text-lg select-none"
                              style={{
                                background: expert.gradient,
                                boxShadow: isActive ? `0 0 10px ${expert.border}` : 'none',
                              }}
                            >
                              {expert.emoji}
                            </div>
                            <div 
                              className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full border border-[#090d1a] bg-emerald-500"
                              title="Online"
                            />
                          </div>

                          {/* Details */}
                          <div className="flex-1 min-w-0 flex flex-col justify-center">
                            <div className="flex items-center justify-between gap-1">
                              <span className="font-semibold text-xs text-[var(--text-primary)] truncate">
                                {expert.name}
                              </span>
                              {existingConv?.lastMessageTimestamp && (
                                <span className="text-[9px] text-[var(--text-muted)] flex-shrink-0">
                                  {formatDate(existingConv.lastMessageTimestamp)}
                                </span>
                              )}
                            </div>
                            <span className="text-[9px] text-[var(--text-muted)] font-medium -mt-0.5">
                              {expert.role}
                            </span>
                            {existingConv?.lastMessage ? (
                              <p className="text-[11px] text-[var(--text-muted)] truncate mt-0.5 leading-tight">
                                {existingConv.lastMessage}
                              </p>
                            ) : (
                              <p className="text-[11px] text-[var(--text-muted)] italic truncate mt-0.5 leading-tight opacity-50">
                                Tap to open chat
                              </p>
                            )}
                          </div>
                        </div>
                      );
                    };

                    return (
                      <>
                        {buddyConvos.map((c) => renderContactItem(c))}
                      </>
                    );
                  })()}
                </div>
              </div>
            </motion.aside>
          )}
        </AnimatePresence>

        {/* Main chat area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Chat header */}
          <div
            className="flex items-center gap-4 px-4 py-3 border-b"
            style={{ borderColor: 'var(--glass-border)' }}
          >
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 rounded-lg transition-colors cursor-pointer hover:bg-white/5 flex-shrink-0"
              style={{ color: 'var(--text-muted)' }}
            >
              {sidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
            </button>

            {(() => {
              const activeConv = conversations.find(c => c.id === activeConversationId);
              const info = activeConv ? agentSidebarConfig[activeConv.agent_id || 'buddy'] : agentSidebarConfig.buddy;
              const isBuddy = activeConv?.agent_id === 'buddy';
              
              return (
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  {isBuddy ? (
                    <EsonaLogo 
                      size={36} 
                      showParticles={false} 
                      glowIntensity="low" 
                      aiState={isStreaming ? 'speaking' : isLoading ? 'listening' : 'idle'}
                    />
                  ) : (
                    <div
                      className="w-9 h-9 rounded-full flex items-center justify-center text-lg select-none flex-shrink-0"
                      style={{
                        background: info.gradient,
                        boxShadow: `0 0 10px ${info.border}`,
                      }}
                    >
                      {info.emoji}
                    </div>
                  )}
                  <div className="min-w-0 flex flex-col">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold truncate" style={{ color: 'var(--text-primary)' }}>
                        {info.name}
                      </p>
                      {info.role && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-[var(--text-muted)] flex-shrink-0">
                          {info.role}
                        </span>
                      )}
                    </div>
                    {isBuddy && activeConv?.active_specialists && activeConv.active_specialists.length > 0 ? (
                      <p className="text-[11px] text-sky-400 font-medium">
                        Group Chat with Esona
                      </p>
                    ) : (
                      <p className="text-xs flex items-center gap-1" style={{ color: 'var(--accent-emerald)' }}>
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block"></span>
                        Online
                      </p>
                    )}
                  </div>

                  {/* Connected Specialist Pills (only in Buddy chat) */}
                  {isBuddy && activeConv?.active_specialists && activeConv.active_specialists.length > 0 && (
                    <div className="hidden sm:flex items-center gap-2 ml-4 overflow-x-auto py-1 custom-scrollbar">
                      {activeConv.active_specialists.map((specId) => {
                        const specInfo = agentSidebarConfig[specId];
                        if (!specInfo) return null;
                        return (
                          <div 
                            key={specId} 
                            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border text-white flex-shrink-0"
                            style={{
                              background: specInfo.gradient,
                              borderColor: specInfo.border,
                              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)',
                            }}
                          >
                            {removingSpecialistId === specId ? (
                              <span className="flex items-center gap-0.5">
                                Removing {specInfo.name}
                                <span className="animate-bounce">.</span>
                                <span className="animate-bounce [animation-delay:0.2s]">.</span>
                                <span className="animate-bounce [animation-delay:0.4s]">.</span>
                              </span>
                            ) : (
                              <>
                                <span>{specInfo.emoji}</span>
                                <span>{specInfo.name}</span>
                                <button
                                  disabled={removingSpecialistId !== null}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDisconnectSpecialist(specId);
                                  }}
                                  className="ml-1 p-0.5 rounded-full hover:bg-white/20 text-white/80 hover:text-white transition-colors cursor-pointer text-[10px] leading-none font-bold"
                                  title="Disconnect Specialist"
                                >
                                  ✕
                                </button>
                              </>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })()}

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
              {messages.length === 0 && !isLoading ? (
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
                    Hi{user?.name ? `, ${user.name}` : ''}! I'm Esona 💙
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
                    const activeConv = conversations.find(c => c.id === activeConversationId);
                    const suggestedSpec = message.agentAnalysis?.suggested_specialist;
                    const isAlreadyConnected = activeConv?.active_specialists?.includes(suggestedSpec);
                    const isDismissed = dismissedSuggestions.includes(message.id);
                    const showSuggestion = false;

                    return (
                      <div key={message.id} className="space-y-3">
                        <MessageBubble message={message} />
                        {showSuggestion && (
                          <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: 10 }}
                            className="flex flex-col items-center my-4 p-4 rounded-2xl border bg-black/40 backdrop-blur-md max-w-sm mx-auto space-y-3"
                            style={{ borderColor: 'rgba(56, 189, 248, 0.25)', boxShadow: '0 8px 32px rgba(56, 189, 248, 0.05)' }}
                          >
                            <p className="text-xs text-[var(--text-secondary)] text-center px-2 leading-relaxed">
                              Esona suggested involving <strong>{agentSidebarConfig[suggestedSpec]?.name || suggestedSpec}</strong> for specialized {agentSidebarConfig[suggestedSpec]?.role?.toLowerCase() || 'support'}.
                            </p>
                            <div className="flex gap-3 w-full justify-center">
                              <button
                                disabled={connectingSpecialistId !== null}
                                onClick={() => handleConnectSpecialist(suggestedSpec)}
                                className={`px-5 py-2 rounded-xl text-xs font-semibold shadow-lg transition-all duration-200 ${
                                  connectingSpecialistId !== null
                                    ? 'bg-sky-500/50 text-white/70 cursor-not-allowed'
                                    : 'bg-gradient-to-r from-sky-400 to-blue-500 hover:from-sky-500 hover:to-blue-600 text-white shadow-sky-500/10 cursor-pointer'
                                }`}
                              >
                                {connectingSpecialistId === suggestedSpec ? (
                                  <span className="flex items-center gap-0.5">
                                    Opening {agentSidebarConfig[suggestedSpec]?.name || suggestedSpec}
                                    <span className="animate-bounce">.</span>
                                    <span className="animate-bounce [animation-delay:0.2s]">.</span>
                                    <span className="animate-bounce [animation-delay:0.4s]">.</span>
                                  </span>
                                ) : (
                                  'Open Chat'
                                )}
                              </button>
                              <button
                                disabled={connectingSpecialistId !== null}
                                onClick={() => setDismissedSuggestions((prev) => [...prev, message.id])}
                                className={`px-5 py-2 border rounded-xl text-xs font-semibold transition-all duration-200 ${
                                  connectingSpecialistId !== null
                                    ? 'bg-white/0 border-white/5 text-[var(--text-muted)] cursor-not-allowed'
                                    : 'bg-white/5 hover:bg-white/10 border-white/10 text-[var(--text-secondary)] cursor-pointer'
                                }`}
                              >
                                Not Now
                              </button>
                            </div>
                          </motion.div>
                        )}
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
    </div>
  );
}
