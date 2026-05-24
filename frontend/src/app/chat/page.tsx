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
} from 'lucide-react';
import Navbar from '@/components/layout/Navbar';
import ChatContainer from '@/components/chat/ChatContainer';
import MessageBubble from '@/components/chat/MessageBubble';
import ChatInput from '@/components/chat/ChatInput';
import TypingIndicator from '@/components/chat/TypingIndicator';
import { useChat } from '@/hooks/useChat';
import { Conversation } from '@/types';
import { getToken, getStoredUser } from '@/lib/api';
import * as api from '@/lib/api';
import { formatDate, truncateText } from '@/lib/utils';

export default function ChatPage() {
  const router = useRouter();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [mounted, setMounted] = useState(false);

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
      if (convos.length > 0 && !activeConversationId) {
        setActiveConversationId(convos[0].id);
      }
    } catch (err) {
      console.error('Failed to load conversations:', err);
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
      // Auto-create conversation if none exists
      const token = getToken();
      if (!token) return;
      try {
        const convo = await api.createConversation(token);
        setConversations((prev) => [convo, ...prev]);
        setActiveConversationId(convo.id);
        // Wait for state to update then send
        setTimeout(() => sendMessage(content), 100);
      } catch (err) {
        console.error('Failed to auto-create conversation:', err);
      }
      return;
    }
    sendMessage(content);
  };

  return (
    <div className="h-screen flex flex-col">
      <Navbar />

      <div className="flex-1 flex pt-20 overflow-hidden">
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
                    background: 'linear-gradient(135deg, rgba(34, 211, 238, 0.1), rgba(59, 130, 246, 0.05))',
                    border: '1px solid rgba(34, 211, 238, 0.2)',
                    color: 'var(--accent-cyan)',
                  }}
                >
                  <Plus size={16} />
                  {isCreating ? 'Creating...' : 'New Chat'}
                </motion.button>

                {/* Conversations list */}
                <div className="flex-1 overflow-y-auto space-y-1">
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
                      <button
                        key={convo.id}
                        onClick={() => setActiveConversationId(convo.id)}
                        className="w-full text-left px-3 py-3 rounded-xl transition-all duration-200 cursor-pointer"
                        style={{
                          background:
                            activeConversationId === convo.id
                              ? 'rgba(34, 211, 238, 0.08)'
                              : 'transparent',
                          border:
                            activeConversationId === convo.id
                              ? '1px solid rgba(34, 211, 238, 0.15)'
                              : '1px solid transparent',
                        }}
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <MessageCircle size={12} style={{ color: 'var(--text-muted)' }} />
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
                      </button>
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
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold"
                style={{
                  background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-purple))',
                  color: 'var(--bg-primary)',
                }}
              >
                E
              </div>
              <div>
                <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                  Esona
                </p>
                <p className="text-xs" style={{ color: 'var(--accent-emerald)' }}>
                  ● Online
                </p>
              </div>
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
                    className="mb-4"
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
      </div>
    </div>
  );
}
