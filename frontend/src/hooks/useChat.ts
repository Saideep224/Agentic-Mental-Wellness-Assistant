'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { Message } from '@/types';
import { generateId } from '@/utils';
import * as api from '@/api';

interface UseChatOptions {
  conversationId: string | null;
  activeSpecialistId?: string | null;
  onSpecialistAction?: (action: 'invited' | 'removed', specialistId: string) => void;
}

export function useChat({ conversationId, activeSpecialistId, onSpecialistAction }: UseChatOptions) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streamPlaceholder, setStreamPlaceholder] = useState<string | null>(null);
  const [typingAgentId, setTypingAgentId] = useState<string | null>(null);
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
      setTypingAgentId(activeSpecialistId || 'buddy');

      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }

      // Connection state variables
      const maxRetries = 2;
      let connectionTimeout: NodeJS.Timeout | null = null;
      let isMessageCreated = false;
      let activeBubbleId = '';
      let bubbleCount = 0;
      let accumulatedContent = '';
      let burstQueue = '';
      let isProcessingBurst = false;
      let currentSenderType = 'buddy';
      let buddyBubbleSpawned = false;

      const cleanUpConnection = () => {
        if (connectionTimeout) {
          clearTimeout(connectionTimeout);
          connectionTimeout = null;
        }
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
        setTypingAgentId(null);
      };

      const processBurst = async (messageId: string) => {
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

          // Check if we hit the delimiter "|||"
          if (accumulatedContent.includes('|||')) {
            const parts = accumulatedContent.split('|||');
            
            // The text before the delimiter is the finished content for the current bubble
            const cleanContent = parts[0].trim();
            setMessages((prev) =>
              prev.map((msg) => (msg.id === activeBubbleId ? { ...msg, content: cleanContent } : msg))
            );

            // Spawn a new bubble
            bubbleCount++;
            activeBubbleId = `${messageId}-${bubbleCount}`;
            accumulatedContent = parts.slice(1).join('|||'); // Carry over the remaining content

            const nextBubble: Message = {
              id: activeBubbleId,
              role: 'assistant',
              content: '',
              timestamp: new Date(),
            };
            setMessages((prev) => [...prev, nextBubble]);
          } else {
            // Clean display: remove any leading delimiters and strip trailing pipe characters
            const displayContent = accumulatedContent.replace(/^\|+/, '').replace(/\|+$/, '').trim();
            setMessages((prev) =>
              prev.map((msg) => (msg.id === activeBubbleId ? { ...msg, content: displayContent } : msg))
            );
          }
          
          // Dynamic typing delay
          let delay = Math.floor(Math.random() * 8) + 4; // 4-12ms base
          
          // If queue is long, speed up delay to catch up
          if (burstQueue.length > 10) {
            delay = Math.max(2, delay - 4);
          }

          // Apply natural typing pauses for punctuation, only if queue isn't overflowed
          const lastChar = chunk[chunk.length - 1];
          if (['.', '!', '?'].includes(lastChar) && burstQueue.length <= 5 && !accumulatedContent.includes('|')) {
            delay = 180;
          } else if ([',', ';', ':'].includes(lastChar) && burstQueue.length <= 5 && !accumulatedContent.includes('|')) {
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

          // Timeout if first chunk/placeholder doesn't arrive within 4 seconds (attempt 1) or 8 seconds (attempt 2)
          const timeoutMs = attempt === 0 ? 4000 : 8000;
          connectionTimeout = setTimeout(() => {
            console.warn(`[useChat] Stream connection attempt ${attempt + 1} timed out.`);
            cleanUpConnection();

             if (!isMessageCreated) {
              if (attempt < maxRetries) {
                console.info(`[useChat] Retrying stream connection (attempt ${attempt + 2}/${maxRetries + 1})...`);
                setStreamPlaceholder(null);
                connectStream(attempt + 1);
              } else {
                setIsLoading(false);
                setIsStreaming(false);
                setStreamPlaceholder(null);
                setMessages((prev) => {
                  const fallbackMsg: Message = {
                    id: generateId(),
                    role: 'assistant',
                    content: "my imaginary wifi betrayed me for a second... 😭 wait, what were we saying?",
                    timestamp: new Date(),
                  };
                  return [...prev, fallbackMsg];
                });
                setError('Request timed out');
              }
            } else {
              // Message was already created and streaming, handle mid-stream disconnect
              setIsStreaming(false);
              setIsLoading(false);
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === activeBubbleId
                    ? { ...msg, content: msg.content + "\n\n(wait, my brain froze for a second... 😭 let's try that again.)" }
                    : msg
                )
              );
            }
          }, timeoutMs);

          eventSource.onmessage = (e) => {
            // Clear connection timeout on the very first message/chunk received
            if (connectionTimeout) {
              clearTimeout(connectionTimeout);
              connectionTimeout = null;
            }

            try {
              const data = JSON.parse(e.data);
              if (data.type === 'placeholder') {
                // Show temporary placeholder bubble via separate state
                setIsLoading(false);
                setStreamPlaceholder(data.content);
              } else if (data.type === 'specialist_start') {
                setIsLoading(false);
                setIsStreaming(true);
                setStreamPlaceholder(null);
                isMessageCreated = true;
                currentSenderType = data.specialist_id;
                setTypingAgentId(data.specialist_id);
                
                const messageId = generateId();
                activeBubbleId = `${messageId}-0`;
                bubbleCount = 0;
                accumulatedContent = '';
                burstQueue = '';
                
                setMessages((prev) => {
                  const specBubble: Message = {
                    id: activeBubbleId,
                    role: 'assistant',
                    content: '',
                    sender_type: currentSenderType,
                    timestamp: new Date(),
                  };
                  return [...prev, specBubble];
                });
              } else if (data.type === 'specialist_chunk') {
                burstQueue += data.content;
                const messageId = activeBubbleId.split('-')[0];
                processBurst(messageId);
              } else if (data.type === 'specialist_done') {
                const finalId = data.message_id || activeBubbleId;
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === activeBubbleId
                      ? { ...msg, id: finalId, content: msg.content.trim() }
                      : msg
                  )
                );
                buddyBubbleSpawned = false;
              } else if (data.type === 'chunk') {
                if (!buddyBubbleSpawned) {
                  buddyBubbleSpawned = true;
                  isMessageCreated = true;
                  currentSenderType = 'buddy';
                  setTypingAgentId('buddy');
                  
                  const messageId = generateId();
                  activeBubbleId = `${messageId}-0`;
                  bubbleCount = 0;
                  accumulatedContent = '';
                  burstQueue = '';
                  
                  setIsLoading(false);
                  setIsStreaming(true);
                  setStreamPlaceholder(null);
                  
                  setMessages((prev) => {
                    const buddyBubble: Message = {
                      id: activeBubbleId,
                      role: 'assistant',
                      content: '',
                      sender_type: 'buddy',
                      timestamp: new Date(),
                    };
                    return [...prev, buddyBubble];
                  });
                }
                
                burstQueue += data.content;
                const messageId = activeBubbleId.split('-')[0];
                processBurst(messageId);
              } else if (data.type === 'done') {
                // Wait for burst queue to empty before finalizing
                const finalize = setInterval(() => {
                  if (burstQueue.length === 0 && !isProcessingBurst) {
                    clearInterval(finalize);
                    setIsStreaming(false);
                    setTypingAgentId(null);
                    
                    setStreamPlaceholder(null);
                    const finalMessageId = data.message_id || activeBubbleId;
                    
                    setMessages((prev) => {
                      let lastUserIdx = -1;
                      for (let i = prev.length - 1; i >= 0; i--) {
                        if (prev[i].role === 'user') {
                          lastUserIdx = i;
                          break;
                        }
                      }
                      return prev.map((msg, idx) => {
                        if (msg.id === activeBubbleId) {
                          return {
                            ...msg,
                            id: finalMessageId,
                            emotionDetected: data.emotion_detected,
                            moodScore: data.mood_score,
                            emotionScore: data.emotion_score,
                            stressScore: data.stress_score,
                            anxietyScore: data.anxiety_score,
                            agentAnalysis: data.agent_analysis,
                          };
                        }
                        if (idx === lastUserIdx) {
                          return {
                            ...msg,
                            emotionDetected: data.emotion_detected,
                            moodScore: data.mood_score,
                            emotionScore: data.emotion_score,
                            stressScore: data.stress_score,
                            anxiety_score: data.anxiety_score,
                          };
                        }
                        return msg;
                      });
                    });
                    cleanUpConnection();
                  }
                }, 50);
              } else if (data.type === 'specialist_action') {
                // Natural language specialist invite/remove — notify parent to update UI
                if (onSpecialistAction && data.action && data.specialist_id) {
                  onSpecialistAction(data.action, data.specialist_id);
                }
              } else if (data.type === 'error') {
                console.error('SSE Error event:', data.content);
                cleanUpConnection();
                setIsLoading(false);
                setIsStreaming(false);
                setStreamPlaceholder(null);
                setTypingAgentId(null);
                setError(data.content || 'Stream error');
                
                if (!isMessageCreated) {
                  setMessages((prev) => {
                    const errorMsg: Message = {
                      id: generateId(),
                      role: 'assistant',
                      content: "wait, I lost my train of thought for a moment... 😭 let's try that again.",
                      timestamp: new Date(),
                    };
                    return [...prev, errorMsg];
                  });
                } else {
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === activeBubbleId
                        ? { ...msg, content: msg.content + "\n\n(sorry, my brain lagged for a moment... 😭 what were we saying?)" }
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
                setStreamPlaceholder(null);
                setTimeout(() => {
                  connectStream(attempt + 1);
                }, 1000);
              } else {
                setIsLoading(false);
                setIsStreaming(false);
                setStreamPlaceholder(null);
                setMessages((prev) => {
                  const fallbackMsg: Message = {
                    id: generateId(),
                    role: 'assistant',
                    content: "my thoughts buffered for a moment 😭 let's try again! what's on your mind?",
                    timestamp: new Date(),
                  };
                  return [...prev, fallbackMsg];
                });
                setError('Connection failed');
              }
            } else {
              setIsStreaming(false);
              setIsLoading(false);
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === activeBubbleId
                    ? { ...msg, content: msg.content + "\n\n(sorry, my brain lagged for a moment... 😭 what were we saying?)" }
                    : msg
                )
              );
            }
          };
        } catch (streamErr) {
          console.error('Failed to initialize EventSource:', streamErr);
          setIsLoading(false);
          setIsStreaming(false);
          setStreamPlaceholder(null);
          setError('Failed to initialize stream');
          
          if (!isMessageCreated) {
            setMessages((prev) => {
              const fallbackMsg: Message = {
                id: generateId(),
                role: 'assistant',
                content: "wait, I lost my train of thought for a second... 😭 what was that?",
                timestamp: new Date(),
              };
              return [...prev, fallbackMsg];
            });
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
    streamPlaceholder,
    typingAgentId,
    error,
    sendMessage,
    loadMessages,
  };
}
