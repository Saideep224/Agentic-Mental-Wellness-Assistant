// ============================================
// QUESTION TYPES
// ============================================

export interface QuestionOption {
  label: string;
  value: string;
  emoji: string;
}

export interface Question {
  id: number;
  text: string;
  category: string;
  categoryLabel: string;
  agentTarget: string;
  options: QuestionOption[];
  allowOther: boolean;
}

// ============================================
// ONBOARDING TYPES
// ============================================

export interface OnboardingResponse {
  questionId: number;
  category: string;
  selectedAnswers: string[];
  customAnswer?: string;
}

export interface OnboardingState {
  currentQuestionIndex: number;
  responses: OnboardingResponse[];
  isCompleted: boolean;
  isSubmitting: boolean;
}

// ============================================
// CHAT TYPES
// ============================================

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  emotionDetected?: string;
  moodScore?: number;
  agentAnalysis?: Record<string, any>;
  isPlaceholder?: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: Date;
  lastMessage?: string;
}

export interface ChatState {
  messages: Message[];
  conversations: Conversation[];
  activeConversationId: string | null;
  isLoading: boolean;
  isStreaming: boolean;
}

// ============================================
// DASHBOARD TYPES
// ============================================

export interface MoodDataPoint {
  date: string;
  score: number;
  emotion: string;
}

export interface EmotionalProfile {
  personalityType: Record<string, unknown>;
  emotionalBaseline: Record<string, unknown>;
  comfortPreferences: Record<string, unknown>;
  communicationStyle: Record<string, unknown>;
  dominantEmotions: EmotionBreakdown[];
  overallMood: number;
  communicationStyleLabel: string;
  personalityLabel: string;
}

export interface EmotionBreakdown {
  emotion: string;
  percentage: number;
  color: string;
}

export interface StressPattern {
  category: string;
  value: number;
  fullMark: number;
}

export interface PersonalityInsight {
  trait: string;
  description: string;
  strength: number;
  icon: string;
}

export interface CommunicationPreference {
  preferredTone: string;
  whatHelps: string[];
  whatToAvoid: string[];
}

// ============================================
// USER TYPES
// ============================================

export interface User {
  id: string;
  name: string;
  email: string;
  onboardingCompleted: boolean;
  avatarUrl?: string | null;
  provider?: string;
  githubUsername?: string | null;
  createdAt?: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

// ============================================
// API RESPONSE TYPES
// ============================================

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface RegisterResponse {
  user: User;
  access_token: string;
}
