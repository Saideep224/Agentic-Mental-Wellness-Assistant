/**
 * Chat API — messaging, conversations CRUD.
 */

import { Message, Conversation } from '@/types';
import { API_BASE, apiPost, apiGet, apiPatch, apiDelete } from './client';

// ============================================
// MESSAGING
// ============================================

export function sendMessageSSE(
  conversationId: string,
  message: string,
  token: string
): EventSource {
  const url = `${API_BASE}/api/chat/${conversationId}/stream?message=${encodeURIComponent(message)}&token=${encodeURIComponent(token)}`;
  return new EventSource(url);
}

export async function sendMessage(
  conversationId: string,
  message: string,
  token: string
): Promise<{ response: string; emotionDetected?: string; moodScore?: number; agentAnalysis?: any }> {
  return apiPost('/api/chat/message', { message, conversation_id: conversationId }, token);
}

export async function getFirstMessage(
  conversationId: string,
  token: string
): Promise<{ response: string; emotionDetected?: string; moodScore?: number }> {
  // A personalized session greeting is an enhancement, not a prerequisite for
  // opening chat. The previous implementation allowed a 500 from this optional
  // endpoint to bubble into useChat.loadMessages(), which incorrectly displayed
  // "Failed to load messages" even when message history had loaded successfully.
  try {
    return await apiPost(`/api/chat/conversations/${conversationId}/first-message`, {}, token);
  } catch (error) {
    console.warn('[Esona Chat] Optional session greeting unavailable; continuing with chat.', error);
    return {
      response: '',
      emotionDetected: 'neutral',
      moodScore: 0.5,
    };
  }
}


// ============================================
// CONVERSATIONS CRUD
// ============================================

export async function getConversations(token: string): Promise<Conversation[]> {
  const data = await apiGet<any[]>('/api/chat/conversations', token);
  return data.map((c) => ({
    id: c.id,
    title: c.title,
    createdAt: c.created_at ? new Date(c.created_at) : new Date(),
    lastMessage: c.last_message,
    agent_id: c.agent_id || 'buddy',
    active_specialists: c.active_specialists || [],
    lastMessageTimestamp: c.last_message_timestamp || c.last_message_ts,
  }));
}

export async function getConversationMessages(conversationId: string, token: string): Promise<Message[]> {
  const data = await apiGet<any[]>(`/api/chat/conversations/${conversationId}/messages`, token);
  return data.map((m) => ({
    id: m.id,
    role: m.role,
    content: m.content,
    timestamp: m.created_at ? new Date(m.created_at) : new Date(),
    sender_type: m.sender_type,
    emotionDetected: m.emotion_detected ?? m.emotionDetected,
    moodScore: m.mood_score ?? m.moodScore,
    emotionScore: m.emotion_score ?? m.emotionScore,
    stressScore: m.stress_score ?? m.stressScore,
    anxietyScore: m.anxiety_score ?? m.anxietyScore,
    agentAnalysis: m.agent_analysis ?? m.agentAnalysis,
  }));
}

export async function createConversation(
  token: string,
  title?: string,
  agentId?: string
): Promise<Conversation> {
  const data = await apiPost<any>('/api/chat/conversations', { title, agent_id: agentId }, token);
  return {
    id: data.id,
    title: data.title,
    createdAt: data.created_at ? new Date(data.created_at) : new Date(),
    lastMessage: data.last_message,
    agent_id: data.agent_id || 'buddy',
    active_specialists: data.active_specialists || [],
  };
}

export async function updateConversation(
  conversationId: string,
  title: string,
  token: string
): Promise<Conversation> {
  const data = await apiPatch<any>(`/api/chat/conversations/${conversationId}`, { title }, token);
  return {
    id: data.id,
    title: data.title,
    createdAt: data.created_at ? new Date(data.created_at) : new Date(),
    lastMessage: data.last_message,
    agent_id: data.agent_id || 'buddy',
    active_specialists: data.active_specialists || [],
  };
}

export async function deleteConversation(conversationId: string, token: string): Promise<void> {
  await apiDelete(`/api/chat/conversations/${conversationId}`, token);
}

export async function connectSpecialist(
  conversationId: string,
  specialistId: string,
  token: string
): Promise<Message[]> {
  const data = await apiPost<any[]>(
    `/api/chat/conversations/${conversationId}/connect-specialist`,
    { specialist_id: specialistId },
    token
  );
  return data.map((m) => ({
    id: m.id,
    role: m.role,
    content: m.content,
    timestamp: m.created_at ? new Date(m.created_at) : new Date(),
    sender_type: m.sender_type,
    emotionDetected: m.emotion_detected ?? m.emotionDetected,
    moodScore: m.mood_score ?? m.moodScore,
    emotionScore: m.emotion_score ?? m.emotionScore,
    stressScore: m.stress_score ?? m.stressScore,
    anxietyScore: m.anxiety_score ?? m.anxietyScore,
    agentAnalysis: m.agent_analysis ?? m.agentAnalysis,
  }));
}

export async function disconnectSpecialist(
  conversationId: string,
  token: string
): Promise<Message[]> {
  const data = await apiPost<any[]>(
    `/api/chat/conversations/${conversationId}/disconnect-specialist`,
    {},
    token
  );
  return data.map((m) => ({
    id: m.id,
    role: m.role,
    content: m.content,
    timestamp: m.created_at ? new Date(m.created_at) : new Date(),
    sender_type: m.sender_type,
    emotionDetected: m.emotion_detected ?? m.emotionDetected,
    moodScore: m.mood_score ?? m.moodScore,
    emotionScore: m.emotion_score ?? m.emotionScore,
    stressScore: m.stress_score ?? m.stressScore,
    anxietyScore: m.anxiety_score ?? m.anxietyScore,
    agentAnalysis: m.agent_analysis ?? m.agentAnalysis,
  }));
}
