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
        
        // Display parts sequentially with burst typing
        const loadedMsgs: Message[] = [];
        for (let i = 0; i < parts.length; i++) {
          setIsLoading(true);
          
          const messageId = `${generateId()}-${i}`;
          const partMessage: Message = {
            id: messageId,
            role: 'assistant',
            content: '',
            timestamp: new Date(),
            emotionDetected: i === parts.length - 1 ? detectedEmotion : undefined,
            moodScore: i === parts.length - 1 ? moodScore : undefined,
          };
          
          loadedMsgs.push(partMessage);
          setMessages([...loadedMsgs]);
          setIsLoading(false);

          // Burst stream typing
          const fullText = parts[i];
          let currentText = '';
          const chars = Array.from(fullText);
          for (let charIdx = 0; charIdx < chars.length; charIdx++) {
            currentText += chars[charIdx];
            setMessages((prev) =>
              prev.map((msg) => (msg.id === messageId ? { ...msg, content: currentText } : msg))
            );
            
            let delay = Math.floor(Math.random() * 8) + 2; // 2-10ms burst
            if (['.', '!', '?'].includes(chars[charIdx])) delay = 100;
            else if ([',', ';', ':'].includes(chars[charIdx])) delay = 50;
            
            await new Promise((resolve) => setTimeout(resolve, delay));
          }
          
          partMessage.content = fullText;

          if (i < parts.length - 1) {
            await new Promise((resolve) => setTimeout(resolve, 200));
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

      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      try {
        const url = `${api.API_BASE}/api/chat/${targetId}/stream?message=${encodeURIComponent(content.trim())}&token=${encodeURIComponent(token)}`;
        const eventSource = new EventSource(url);
        eventSourceRef.current = eventSource;

        const messageId = generateId();
        const partMessage: Message = {
          id: messageId,
          role: 'assistant',
          content: '',
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, partMessage]);

        let accumulatedContent = '';
        let burstQueue = '';
        let isProcessingBurst = false;

        const processBurst = async () => {
          if (isProcessingBurst) return;
          isProcessingBurst = true;
          
          while (burstQueue.length > 0) {
            const char = burstQueue[0];
            burstQueue = burstQueue.slice(1);
            accumulatedContent += char;
            
            // Render chunk
            setMessages((prev) =>
              prev.map((msg) => (msg.id === messageId ? { ...msg, content: accumulatedContent } : msg))
            );
            
            // Dynamic burst typing delay
            let delay = Math.floor(Math.random() * 10) + 5; // 5-15ms for normal characters
            if (['.', '!', '?'].includes(char)) delay = 250; // pause on punctuation
            else if ([',', ';', ':'].includes(char)) delay = 100; // soft pause
            
            await new Promise(r => setTimeout(r, delay));
          }
          isProcessingBurst = false;
        };

        eventSource.onmessage = (e) => {
          const data = JSON.parse(e.data);
          
          if (data.type === 'chunk') {
            setIsLoading(false);
            setIsStreaming(true);
            
            // Handle splitting inside chunks if LLM still emits |||
            let chunkText = data.content.replace(/\|\|\|/g, '\n\n');
            burstQueue += chunkText;
            processBurst();
          } else if (data.type === 'done') {
            // Wait for burst queue to empty before finalizing
            const finalize = setInterval(() => {
              if (burstQueue.length === 0 && !isProcessingBurst) {
                clearInterval(finalize);
                setIsStreaming(false);
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === messageId
                      ? {
                          ...msg,
                          id: data.message_id || messageId,
                          emotionDetected: data.emotion_detected,
                          moodScore: data.mood_score,
                          agentAnalysis: data.agent_analysis,
                        }
                      : msg
                  )
                );
                eventSource.close();
              }
            }, 50);
          } else if (data.type === 'error') {
            console.error('SSE Error:', data.content);
            eventSource.close();
            setIsLoading(false);
            setIsStreaming(false);
            setError('Stream error occurred');
          }
        };

        eventSource.onerror = (e) => {
          console.error('EventSource connection error:', e);
          eventSource.close();
          setIsLoading(false);
          setIsStreaming(false);
        };
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
