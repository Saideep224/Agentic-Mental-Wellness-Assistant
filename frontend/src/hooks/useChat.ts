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
        eventSourceRef.current = null;
      }

      // Connection state variables
      const maxRetries = 2;
      let connectionTimeout: NodeJS.Timeout | null = null;
      let isMessageCreated = false;
      let messageId = '';
      let accumulatedContent = '';
      let burstQueue = '';
      let isProcessingBurst = false;

      const cleanUpConnection = () => {
        if (connectionTimeout) {
          clearTimeout(connectionTimeout);
          connectionTimeout = null;
        }
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
      };

      const processBurst = async (currentMessageId: string) => {
        if (isProcessingBurst) return;
        isProcessingBurst = true;
        
        while (burstQueue.length > 0) {
          // Adjust chunk length dynamically to catch up if queue builds up
          let chunkLength = 1;
          if (burstQueue.length > 50) {
            chunkLength = 6;
          } else if (burstQueue.length > 25) {
            chunkLength = 4;
          } else if (burstQueue.length > 10) {
            chunkLength = 2;
          }

          const chunk = burstQueue.slice(0, chunkLength);
          burstQueue = burstQueue.slice(chunkLength);
          accumulatedContent += chunk;
          
          // Render accumulated content update
          setMessages((prev) =>
            prev.map((msg) => (msg.id === currentMessageId ? { ...msg, content: accumulatedContent } : msg))
          );
          
          // Dynamic typing delay
          let delay = Math.floor(Math.random() * 8) + 4; // 4-12ms base
          
          // If queue is long, speed up delay to catch up
          if (burstQueue.length > 10) {
            delay = Math.max(2, delay - 4);
          }

          // Apply natural typing pauses for punctuation, only if queue isn't overflowed
          const lastChar = chunk[chunk.length - 1];
          if (['.', '!', '?'].includes(lastChar) && burstQueue.length <= 5) {
            delay = 180;
          } else if ([',', ';', ':'].includes(lastChar) && burstQueue.length <= 5) {
            delay = 70;
          }
          
          await new Promise((resolve) => setTimeout(resolve, delay));
        }
        isProcessingBurst = false;
      };

      const connectStream = (attempt: number) => {
        cleanUpConnection();

        try {
          const url = `${api.API_BASE}/api/chat/${targetId}/stream?message=${encodeURIComponent(content.trim())}&token=${encodeURIComponent(token)}`;
          const eventSource = new EventSource(url);
          eventSourceRef.current = eventSource;

          // Timeout if first chunk doesn't arrive within 12 seconds
          connectionTimeout = setTimeout(() => {
            console.warn(`[useChat] Stream connection attempt ${attempt + 1} timed out.`);
            cleanUpConnection();

            if (!isMessageCreated) {
              if (attempt < maxRetries) {
                console.info(`[useChat] Retrying stream connection (attempt ${attempt + 2}/${maxRetries + 1})...`);
                connectStream(attempt + 1);
              } else {
                setIsLoading(false);
                setIsStreaming(false);
                const fallbackMsg: Message = {
                  id: generateId(),
                  role: 'assistant',
                  content: "I'm having trouble reaching my database right now. Please try again. 💙",
                  timestamp: new Date(),
                };
                setMessages((prev) => [...prev, fallbackMsg]);
                setError('Request timed out');
              }
            } else {
              // Message was already created and streaming, handle mid-stream disconnect
              setIsStreaming(false);
              setIsLoading(false);
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === messageId
                    ? { ...msg, content: msg.content + "\n\n[Connection was lost. Please try again. 💙]" }
                    : msg
                )
              );
            }
          }, 12000);

          eventSource.onmessage = (e) => {
            // Clear connection timeout on the very first message/chunk received
            if (connectionTimeout) {
              clearTimeout(connectionTimeout);
              connectionTimeout = null;
            }

            try {
              const data = JSON.parse(e.data);
              
              if (data.type === 'chunk') {
                if (!isMessageCreated) {
                  isMessageCreated = true;
                  messageId = generateId();
                  const partMessage: Message = {
                    id: messageId,
                    role: 'assistant',
                    content: '',
                    timestamp: new Date(),
                  };
                  setIsLoading(false);
                  setIsStreaming(true);
                  setMessages((prev) => [...prev, partMessage]);
                }
                
                let chunkText = data.content.replace(/\|\|\|/g, '\n\n');
                burstQueue += chunkText;
                processBurst(messageId);
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
                    cleanUpConnection();
                  }
                }, 50);
              } else if (data.type === 'error') {
                console.error('SSE Error event:', data.content);
                cleanUpConnection();
                setIsLoading(false);
                setIsStreaming(false);
                setError(data.content || 'Stream error');
                
                if (!isMessageCreated) {
                  const errorMsg: Message = {
                    id: generateId(),
                    role: 'assistant',
                    content: data.content || "I encountered an error trying to process that. Please try again. 💙",
                    timestamp: new Date(),
                  };
                  setMessages((prev) => [...prev, errorMsg]);
                } else {
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === messageId
                        ? { ...msg, content: msg.content + `\n\n[Error: ${data.content || "Connection lost."} 💙]` }
                        : msg
                    )
                  );
                }
              }
            } catch (parseErr) {
              console.error('Failed to parse SSE message data:', parseErr);
            }
          };

          eventSource.onerror = (e) => {
            console.error('EventSource connection error:', e);
            if (connectionTimeout) {
              clearTimeout(connectionTimeout);
              connectionTimeout = null;
            }
            cleanUpConnection();

            if (!isMessageCreated) {
              if (attempt < maxRetries) {
                console.info(`[useChat] Retrying stream connection after error (attempt ${attempt + 2}/${maxRetries + 1})...`);
                setTimeout(() => {
                  connectStream(attempt + 1);
                }, 1000);
              } else {
                setIsLoading(false);
                setIsStreaming(false);
                const fallbackMsg: Message = {
                  id: generateId(),
                  role: 'assistant',
                  content: "I'm having trouble connecting right now. Please try again in a moment. 💙",
                  timestamp: new Date(),
                };
                setMessages((prev) => [...prev, fallbackMsg]);
                setError('Connection failed');
              }
            } else {
              setIsStreaming(false);
              setIsLoading(false);
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === messageId
                    ? { ...msg, content: msg.content + "\n\n[Connection was lost. Please try again. 💙]" }
                    : msg
                )
              );
            }
          };
        } catch (streamErr) {
          console.error('Failed to initialize EventSource:', streamErr);
          setIsLoading(false);
          setIsStreaming(false);
          setError('Failed to initialize stream');
          
          if (!isMessageCreated) {
            const fallbackMsg: Message = {
              id: generateId(),
              role: 'assistant',
              content: "I failed to initiate the chat stream. Please try again. 💙",
              timestamp: new Date(),
            };
            setMessages((prev) => [...prev, fallbackMsg]);
          }
        }
      };

      // Start initial connection
      connectStream(0);
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
