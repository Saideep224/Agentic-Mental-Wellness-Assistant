'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { Message } from '@/types';
import { generateId } from '@/utils';
import * as api from '@/api';

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
      
      const splitMsgs: Message[] = [];
      for (const m of msgs) {
        if (m.role === 'assistant' && m.content.includes('|||')) {
          const parts = m.content.split('|||').map((p) => p.trim()).filter(Boolean);
          parts.forEach((part, idx) => {
            splitMsgs.push({
              ...m,
              id: `${m.id}-${idx}`,
              content: part,
              timestamp: new Date(m.timestamp),
            });
          });
        } else {
          splitMsgs.push({
            ...m,
            timestamp: new Date(m.timestamp),
          });
        }
      }
      
      if (splitMsgs.length === 0) {
        setIsLoading(true);
        // Call backend to generate first message
        const response = await api.getFirstMessage(conversationId, token);
        const responseText = response.response;
        const detectedEmotion = response.emotionDetected;
        const moodScore = response.moodScore;

        const parts = responseText.split('|||').map(p => p.trim()).filter(Boolean);
        
        // Display parts sequentially with typing/streaming delay
        const loadedMsgs: Message[] = [];
        for (let i = 0; i < parts.length; i++) {
          setIsLoading(true);
          
          // Typing delay for the stream
          const typingDelay = Math.max(700, Math.min(2000, parts[i].length * 15));
          await new Promise((resolve) => setTimeout(resolve, typingDelay));

          const messageId = `${generateId()}-${i}`;
          const partMessage: Message = {
            id: messageId,
            role: 'assistant',
            content: '',
            timestamp: new Date(),
            emotionDetected: i === parts.length - 1 ? detectedEmotion : undefined,
            moodScore: i === parts.length - 1 ? moodScore : undefined,
          };
          
          // Pre-add message so stream is visible in UI
          loadedMsgs.push(partMessage);
          setMessages([...loadedMsgs]);
          setIsLoading(false);

          // Stream typing
          const fullText = parts[i];
          let currentText = '';
          const chars = Array.from(fullText);
          for (let charIdx = 0; charIdx < chars.length; charIdx++) {
            currentText += chars[charIdx];
            // Update messages state
            setMessages((prev) =>
              prev.map((msg) => (msg.id === messageId ? { ...msg, content: currentText } : msg))
            );
            await new Promise((resolve) => setTimeout(resolve, 15));
          }
          
          // Update local accumulator message content
          partMessage.content = fullText;

          if (i < parts.length - 1) {
            setIsLoading(true);
            await new Promise((resolve) => setTimeout(resolve, 400));
          }
        }
      } else {
        setMessages(splitMsgs);
      }
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
    async (content: string, overrideConversationId?: string) => {
      const targetId = overrideConversationId || conversationId;
      if (!targetId || !content.trim()) return;
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
      setIsStreaming(false);

      try {
        // Send message directly to receive fully compiled response (with splits)
        const response = await api.sendMessage(targetId, content.trim(), token);
        const responseText = response.response;
        const detectedEmotion = response.emotionDetected;
        const moodScore = response.moodScore;
        const agentAnalysis = response.agentAnalysis;

        // Split raw response by |||
        const parts = responseText.split('|||').map(p => p.trim()).filter(Boolean);

        // Display parts sequentially with typing delay
        for (let i = 0; i < parts.length; i++) {
          setIsLoading(true); // Keep typing indicator active

          // Typing delay: e.g. minimum 700ms, maximum 2000ms
          const typingDelay = Math.max(700, Math.min(2000, parts[i].length * 15));
          await new Promise((resolve) => setTimeout(resolve, typingDelay));

          const messageId = `${generateId()}-${i}`;
          const partMessage: Message = {
            id: messageId,
            role: 'assistant',
            content: '', // Start empty
            timestamp: new Date(),
            emotionDetected: i === parts.length - 1 ? detectedEmotion : undefined,
            moodScore: i === parts.length - 1 ? moodScore : undefined,
            agentAnalysis: i === parts.length - 1 ? agentAnalysis : undefined,
          };

          setMessages((prev) => [...prev, partMessage]);
          setIsLoading(false); // Hide the typing indicator while typing this bubble

          // Stream the characters
          const fullText = parts[i];
          let currentText = '';
          const chars = Array.from(fullText);
          for (let charIdx = 0; charIdx < chars.length; charIdx++) {
            currentText += chars[charIdx];
            setMessages((prev) =>
              prev.map((msg) => (msg.id === messageId ? { ...msg, content: currentText } : msg))
            );
            await new Promise((resolve) => setTimeout(resolve, 15));
          }

          // Small gap between typing bubbles
          if (i < parts.length - 1) {
            setIsLoading(true);
            await new Promise((resolve) => setTimeout(resolve, 400));
          }
        }
      } catch (err) {
        console.error('Message send failed:', err);
        setMessages((prev) => [
          ...prev,
          {
            id: generateId(),
            role: 'assistant',
            content: "I'm having trouble connecting right now. Please try again in a moment. 💙",
            timestamp: new Date(),
          },
        ]);
        setError('Failed to send message');
      } finally {
        setIsLoading(false);
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
