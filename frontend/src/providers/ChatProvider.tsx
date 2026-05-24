'use client';

import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { Message, Conversation } from '@/types';
import { generateId } from '@/lib/utils';
import * as api from '@/lib/api';

interface ChatContextType {
  messages: Message[];
  conversations: Conversation[];
  activeConversationId: string | null;
  isLoading: boolean;
  isStreaming: boolean;
  sendMessage: (content: string) => Promise<void>;
  loadConversations: () => Promise<void>;
  createNewConversation: () => Promise<void>;
  setActiveConversation: (id: string) => Promise<void>;
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
}

const ChatContext = createContext<ChatContextType | null>(null);

export function useChatContext() {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChatContext must be used within a ChatProvider');
  }
  return context;
}

interface ChatProviderProps {
  children: ReactNode;
}

export default function ChatProvider({ children }: ChatProviderProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);

  const loadConversations = useCallback(async () => {
    try {
      const token = api.getToken();
      if (!token) return;
      const convos = await api.getConversations(token);
      setConversations(convos);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  }, []);

  const setActiveConversation = useCallback(async (id: string) => {
    setActiveConversationId(id);
    try {
      const token = api.getToken();
      if (!token) return;
      const msgs = await api.getConversationMessages(id, token);
      setMessages(
        msgs.map((m) => ({
          ...m,
          timestamp: new Date(m.timestamp),
        }))
      );
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  }, []);

  const createNewConversation = useCallback(async () => {
    try {
      const token = api.getToken();
      if (!token) return;
      const convo = await api.createConversation(token);
      setConversations((prev) => [convo, ...prev]);
      setActiveConversationId(convo.id);
      setMessages([]);
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  }, []);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!activeConversationId || !content.trim()) return;
      const token = api.getToken();
      if (!token) return;

      const userMessage: Message = {
        id: generateId(),
        role: 'user',
        content: content.trim(),
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
      setIsStreaming(true);

      try {
        // Try SSE streaming first
        const eventSource = api.sendMessageSSE(activeConversationId, content.trim(), token);
        let aiContent = '';
        const aiMessageId = generateId();

        // Add empty AI message
        setMessages((prev) => [
          ...prev,
          {
            id: aiMessageId,
            role: 'assistant',
            content: '',
            timestamp: new Date(),
          },
        ]);

        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.content) {
              aiContent += data.content;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === aiMessageId
                    ? {
                        ...m,
                        content: aiContent,
                        emotionDetected: data.emotionDetected || m.emotionDetected,
                        moodScore: data.moodScore || m.moodScore,
                      }
                    : m
                )
              );
            }
            if (data.done) {
              eventSource.close();
              setIsStreaming(false);
              setIsLoading(false);
            }
          } catch {
            // If JSON parse fails, treat as text chunk
            aiContent += event.data;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === aiMessageId ? { ...m, content: aiContent } : m
              )
            );
          }
        };

        eventSource.onerror = async () => {
          eventSource.close();
          // Fallback to regular POST if SSE fails
          if (!aiContent) {
            try {
              const response = await api.sendMessage(activeConversationId, content.trim(), token);
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === aiMessageId
                    ? {
                        ...m,
                        content: response.response,
                        emotionDetected: response.emotionDetected,
                        moodScore: response.moodScore,
                      }
                    : m
                )
              );
            } catch (err) {
              console.error('Fallback message send failed:', err);
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === aiMessageId
                    ? {
                        ...m,
                        content: "I'm having trouble connecting right now. Please try again in a moment. 💙",
                      }
                    : m
                )
              );
            }
          }
          setIsStreaming(false);
          setIsLoading(false);
        };
      } catch (error) {
        console.error('Failed to send message:', error);
        setIsStreaming(false);
        setIsLoading(false);
      }
    },
    [activeConversationId]
  );

  return (
    <ChatContext.Provider
      value={{
        messages,
        conversations,
        activeConversationId,
        isLoading,
        isStreaming,
        sendMessage,
        loadConversations,
        createNewConversation,
        setActiveConversation,
        setMessages,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}
