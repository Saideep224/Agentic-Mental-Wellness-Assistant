'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
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
} from 'lucide-react';
import Navbar from '@/components/layout/Navbar';
import EsonaLogo from '@/components/layout/EsonaLogo';
import ChatContainer from '@/components/chat/ChatContainer';
import MessageBubble from '@/components/chat/MessageBubble';
import ChatInput from '@/components/chat/ChatInput';
import TypingIndicator from '@/components/chat/TypingIndicator';
import { useChat } from '@/hooks/useChat';
import { Conversation } from '@/types';
import { getToken, getStoredUser } from '@/api';
import * as api from '@/api';
import { formatDate, truncateText } from '@/utils';

export default function ChatPage() {
  const router = useRouter();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(
    typeof window !== 'undefined' ? window.innerWidth > 768 : true
  );
  const [debugOpen, setDebugOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  // Track accordion state for the Live Agent Debug Panel
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
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

  const handleSaveTitle = async (id: string) => {
    if (!editTitle.trim()) {
      setEditingId(null);
      return;
    }
    const token = getToken();
    if (!token) return;

    setConversations((prev) =>
      prev.map((c) => (c.id === id ? { ...c, title: editTitle.trim() } : c))
    );
    setEditingId(null);

    try {
      await api.updateConversation(id, editTitle.trim(), token);
    } catch (err) {
      console.error('Failed to update title:', err);
      loadConversations();
    }
  };

  const handleDeleteConversation = async (id: string) => {
    if (!confirm('Are you sure you want to delete this conversation?')) return;
    const token = getToken();
    if (!token) return;

    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeConversationId === id) {
      setActiveConversationId(null);
    }

    try {
      await api.deleteConversation(id, token);
      const convos = await api.getConversations(token);
      setConversations(convos);
      if (convos.length > 0) {
        setActiveConversationId(convos[0].id);
      } else {
        setActiveConversationId(null);
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
      loadConversations();
    }
  };

  useEffect(() => {
    setMounted(true);
  }, []);

  const user = mounted ? getStoredUser() : null;

  const { messages, isLoading, isStreaming, sendMessage } = useChat({
    conversationId: activeConversationId,
  });

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
          setActiveConversationId(convos[0].id);
        }
      } else {
        // Auto-create first conversation
        setIsCreating(true);
        const convo = await api.createConversation(token);
        setConversations([convo]);
        setActiveConversationId(convo.id);
        setIsCreating(false);
      }
    } catch (err) {
      console.error('Failed to load conversations:', err);
      setIsCreating(false);
    }
  }, [activeConversationId]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // Create new conversation
  const handleNewConversation = async () => {
    const token = getToken();
    if (!token) return;
    setIsCreating(true);
    try {
      const convo = await api.createConversation(token);
      setConversations((prev) => [convo, ...prev]);
      setActiveConversationId(convo.id);
    } catch (err) {
      console.error('Failed to create conversation:', err);
    } finally {
      setIsCreating(false);
    }
  };

  const handleSend = async (content: string) => {
    if (!activeConversationId) {
      const token = getToken();
      if (!token) return;
      try {
        const convo = await api.createConversation(token);
        setConversations((prev) => [convo, ...prev]);
        setActiveConversationId(convo.id);
        sendMessage(content, convo.id);
      } catch (err) {
        console.error('Failed to auto-create conversation:', err);
      }
      return;
    }
    sendMessage(content);
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
              <div className="h-full flex flex-col p-4 w-[280px]">
                {/* New chat button */}
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleNewConversation}
                  disabled={isCreating}
                  className="w-full py-3 rounded-xl text-sm font-medium flex items-center justify-center gap-2 mb-4 cursor-pointer transition-all duration-300"
                  style={{
                    background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.1), rgba(59, 130, 246, 0.05))',
                    border: '1px solid rgba(56, 189, 248, 0.2)',
                    color: 'var(--accent-cyan)',
                  }}
                >
                  <Plus size={16} />
                  {isCreating ? 'Creating...' : 'New Chat'}
                </motion.button>

                {/* Conversations list */}
                <div className="flex-1 overflow-y-auto space-y-1 pr-1">
                  {conversations.length === 0 ? (
                    <div className="text-center py-10">
                      <MessageCircle
                        size={32}
                        className="mx-auto mb-3"
                        style={{ color: 'var(--text-muted)', opacity: 0.5 }}
                      />
                      <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        No conversations yet.
                        <br />
                        Start a new one!
                      </p>
                    </div>
                  ) : (
                    conversations.map((convo) => (
                      <div
                        key={convo.id}
                        onClick={() => {
                          if (editingId !== convo.id) {
                            setActiveConversationId(convo.id);
                          }
                        }}
                        className="w-full text-left px-3 py-3 rounded-xl transition-all duration-200 cursor-pointer group"
                        style={{
                          background:
                            activeConversationId === convo.id
                              ? 'rgba(56, 189, 248, 0.08)'
                              : 'transparent',
                          border:
                            activeConversationId === convo.id
                              ? '1px solid rgba(56, 189, 248, 0.15)'
                              : '1px solid transparent',
                        }}
                      >
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <div className="flex items-center gap-2 truncate flex-1">
                            <MessageCircle size={12} className="flex-shrink-0" style={{ color: 'var(--text-muted)' }} />
                            {editingId === convo.id ? (
                              <input
                                value={editTitle}
                                onChange={(e) => setEditTitle(e.target.value)}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') handleSaveTitle(convo.id);
                                  if (e.key === 'Escape') setEditingId(null);
                                }}
                                onBlur={() => handleSaveTitle(convo.id)}
                                onClick={(e) => e.stopPropagation()}
                                autoFocus
                                className="bg-black/40 text-xs rounded border border-white/20 px-2 py-0.5 w-full focus:outline-none focus:border-cyan-400 text-white"
                              />
                            ) : (
                              <span
                                className="text-sm font-medium truncate"
                                style={{
                                  color:
                                    activeConversationId === convo.id
                                      ? 'var(--text-primary)'
                                      : 'var(--text-secondary)',
                                }}
                              >
                                {convo.title || 'New Conversation'}
                              </span>
                            )}
                          </div>
                          
                          {editingId !== convo.id && (
                            <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex-shrink-0">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setEditingId(convo.id);
                                  setEditTitle(convo.title || 'New Conversation');
                                }}
                                className="p-1 text-white/40 hover:text-sky-400 hover:bg-white/5 rounded transition-all duration-150 cursor-pointer"
                                title="Edit Title"
                              >
                                <Edit2 size={12} />
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDeleteConversation(convo.id);
                                }}
                                className="p-1 text-white/40 hover:text-rose-400 hover:bg-white/5 rounded transition-all duration-150 cursor-pointer"
                                title="Delete Chat"
                              >
                                <Trash2 size={12} />
                              </button>
                            </div>
                          )}
                        </div>
                        {convo.lastMessage && (
                          <p
                            className="text-xs truncate pl-5"
                            style={{ color: 'var(--text-muted)' }}
                          >
                            {truncateText(convo.lastMessage, 50)}
                          </p>
                        )}
                        <p
                          className="text-xs pl-5 mt-0.5"
                          style={{ color: 'var(--text-muted)', opacity: 0.6 }}
                        >
                          {formatDate(convo.createdAt)}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </motion.aside>
          )}
        </AnimatePresence>

        {/* Main chat area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Chat header */}
          <div
            className="flex items-center gap-3 px-4 py-3 border-b"
            style={{ borderColor: 'var(--glass-border)' }}
          >
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 rounded-lg transition-colors cursor-pointer hover:bg-white/5"
              style={{ color: 'var(--text-muted)' }}
            >
              {sidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
            </button>

            <div className="flex items-center gap-2">
              <EsonaLogo 
                size={32} 
                showParticles={false} 
                glowIntensity="low" 
                aiState={isStreaming ? 'speaking' : isLoading ? 'listening' : 'idle'}
              />
              <div>
                <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                  Esona
                </p>
                <p className="text-xs" style={{ color: 'var(--accent-emerald)' }}>
                  ● Online
                </p>
              </div>
            </div>

            {/* Hidden Dev Insights Toggle */}
            <div className="ml-auto">
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
                  className="flex flex-col items-center justify-center h-full text-center py-20"
                >
                  <Sparkles
                    size={40}
                    className="mb-4 animate-breathe"
                    style={{ color: 'var(--accent-cyan)', opacity: 0.5 }}
                  />
                  <h3
                    className="text-xl font-semibold mb-2 glow-text"
                    style={{ fontFamily: 'var(--font-outfit), sans-serif' }}
                  >
                    Hey{user?.name ? `, ${user.name}` : ''} 👋
                  </h3>
                  <p className="text-sm max-w-sm" style={{ color: 'var(--text-secondary)' }}>
                    I&apos;m Esona, your supporting buddie. Feel free to talk about anything
                    — your day, your thoughts, or whatever&apos;s on your mind.
                  </p>
                  <p className="text-xs mt-4" style={{ color: 'var(--text-muted)' }}>
                    Everything here stays between us. 💙
                  </p>
                </motion.div>
              ) : (
                <>
                  {messages.map((message) => (
                    <MessageBubble key={message.id} message={message} />
                  ))}
                  <AnimatePresence>
                    {isLoading && !isStreaming && messages[messages.length - 1]?.role === 'user' && (
                      <TypingIndicator />
                    )}
                  </AnimatePresence>
                </>
              )}
            </ChatContainer>
          </div>

          {/* Input */}
          <ChatInput onSend={handleSend} disabled={isLoading} />
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
              <div className="h-full flex flex-col p-4 w-[380px] overflow-y-auto space-y-4">
                <div className="flex items-center gap-2 pb-2 border-b border-white/10">
                  <Terminal size={16} className="text-sky-400" />
                  <h3 className="text-sm font-semibold tracking-wide uppercase text-sky-400">
                    Live Agent Debug Panel
                  </h3>
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
