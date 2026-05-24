'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { Message } from '@/types';
import { generateId } from '@/lib/utils';
import * as api from '@/lib/api';

interface UseChatOptions {
  conversationId: string | null;
}

export function useChat({ conversationId }: UseChatOptions) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Load messages for current conversation
  const loadMessages = useCallback(async () => {
    if (!conversationId) return;
    const token = api.getToken();
    if (!token) return;

    try {
      setIsLoading(true);
      const msgs = await api.getConversationMessages(conversationId, token);
      setMessages(
        msgs.map((m) => ({
          ...m,
          timestamp: new Date(m.timestamp),
        }))
      );
    } catch (err) {
      console.error('Failed to load messages:', err);
      setError('Failed to load messages');
    } finally {
      setIsLoading(false);
    }
  }, [conversationId]);

  // Load messages when conversation changes
  useEffect(() => {
    if (conversationId) {
      loadMessages();
    } else {
      setMessages([]);
    }
  }, [conversationId, loadMessages]);

  // Cleanup EventSource on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!conversationId || !content.trim()) return;
      const token = api.getToken();
      if (!token) return;

      setError(null);

      // Add user message immediately
      const userMessage: Message = {
        id: generateId(),
        role: 'user',
        content: content.trim(),
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
      setIsStreaming(true);

      const aiMessageId = generateId();
      let aiContent = '';

      // Add placeholder AI message
      setMessages((prev) => [
        ...prev,
        {
          id: aiMessageId,
          role: 'assistant',
          content: '',
          timestamp: new Date(),
        },
      ]);

      try {
        // Try SSE streaming
        const eventSource = api.sendMessageSSE(conversationId, content.trim(), token);
        eventSourceRef.current = eventSource;

        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'chunk' && data.content) {
              aiContent += data.content;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === aiMessageId
                    ? {
                        ...m,
                        content: aiContent,
                      }
                    : m
                )
              );
            } else if (data.type === 'done') {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === aiMessageId
                    ? {
                        ...m,
                        id: data.message_id || data.messageId || m.id,
                        emotionDetected: data.emotion_detected || data.emotionDetected || m.emotionDetected,
                        moodScore: data.mood_score || data.moodScore || m.moodScore,
                      }
                    : m
                )
              );
              eventSource.close();
              eventSourceRef.current = null;
              setIsStreaming(false);
              setIsLoading(false);
            }
          } catch {
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
          eventSourceRef.current = null;

          // Fallback to regular POST
          if (!aiContent) {
            try {
              const response = await api.sendMessage(conversationId, content.trim(), token);
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
              console.error('Message send failed:', err);
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === aiMessageId
                    ? {
                        ...m,
                        content:
                          "I'm having trouble connecting right now. Please try again in a moment. 💙",
                      }
                    : m
                )
              );
              setError('Failed to send message');
            }
          }
          setIsStreaming(false);
          setIsLoading(false);
        };
      } catch (err) {
        console.error('Failed to initiate chat:', err);
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
        setIsStreaming(false);
        setIsLoading(false);
        setError('Connection failed');
      }
    },
    [conversationId]
  );

  return {
    messages,
    setMessages,
    isLoading,
    isStreaming,
    error,
    sendMessage,
    loadMessages,
  };
}
