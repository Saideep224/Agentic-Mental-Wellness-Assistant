'use client';

import { motion } from 'framer-motion';
import { Message } from '@/types';
import { formatMessageTime } from '@/utils';
import EmotionalAura from './EmotionalAura';

interface MessageBubbleProps {
  message: Message;
  isGroupStart?: boolean;
  isGroupEnd?: boolean;
}

const getEmotionDisplay = (emotion: string | undefined, emotionScore?: number, moodScore?: number) => {
  if (!emotion) return null;
  const emotionKey = emotion.toLowerCase().trim();
  let emoji = '😐';
  let label = 'Neutral';

  switch (emotionKey) {
    case 'happy':
    case 'happiness':
    case 'joy':
      emoji = '😊';
      label = 'Happy';
      break;
    case 'sad':
    case 'sadness':
    case 'grief':
      emoji = '😢';
      label = 'Sadness';
      break;
    case 'stress':
    case 'stressed':
    case 'burnout':
      emoji = '😫';
      label = 'Stress';
      break;
    case 'anxiety':
    case 'anxious':
    case 'panic':
      emoji = '😟';
      label = 'Anxiety';
      break;
    case 'frustration':
    case 'frustrated':
    case 'angry':
    case 'annoyed':
      emoji = '😤';
      label = 'Frustration';
      break;
    case 'loneliness':
    case 'lonely':
    case 'alone':
      emoji = '😔';
      label = 'Loneliness';
      break;
    case 'neutral':
      emoji = '😐';
      label = 'Neutral';
      break;
    default:
      emoji = '💭';
      label = emotion.charAt(0).toUpperCase() + emotion.slice(1);
      break;
  }

  const score = emotionScore !== undefined && emotionScore !== null 
    ? emotionScore 
    : (moodScore !== undefined && moodScore !== null ? moodScore : null);

  const percentage = score !== null ? `${Math.round(score * 100)}%` : '';
  
  return { emoji, label, percentage };
};

const agentConfig: Record<string, { emoji: string; name: string; gradient: string; border: string }> = {
  buddy: { emoji: '💙', name: 'Esona', gradient: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)', border: 'rgba(56, 189, 248, 0.3)' },
  lex: { emoji: '⚖️', name: 'Lex', gradient: 'linear-gradient(135deg, #d97706 0%, #b45309 100%)', border: 'rgba(245, 158, 11, 0.3)' },
  maya: { emoji: '👨‍⚕️', name: 'Dr. Maya', gradient: 'linear-gradient(135deg, #059669 0%, #047857 100%)', border: 'rgba(16, 185, 129, 0.3)' },
  ray: { emoji: '👮', name: 'Officer Ray', gradient: 'linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)', border: 'rgba(239, 68, 68, 0.3)' },
  techie: { emoji: '💻', name: 'Techie', gradient: 'linear-gradient(135deg, #4f46e5 0%, #4338ca 100%)', border: 'rgba(99, 102, 241, 0.3)' },
  mentor: { emoji: '📚', name: 'Mentor', gradient: 'linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%)', border: 'rgba(139, 92, 246, 0.3)' },
  finance: { emoji: '💰', name: 'Finance Coach', gradient: 'linear-gradient(135deg, #db2777 0%, #be185d 100%)', border: 'rgba(236, 72, 153, 0.3)' },
  fitness: { emoji: '🏋️', name: 'Fitness Coach', gradient: 'linear-gradient(135deg, #0d9488 0%, #0f766e 100%)', border: 'rgba(20, 184, 166, 0.3)' },
  relationship: { emoji: '💜', name: 'Relationship Coach', gradient: 'linear-gradient(135deg, #a855f7 0%, #7e22ce 100%)', border: 'rgba(168, 85, 247, 0.3)' },
};

export default function MessageBubble({ message, isGroupStart = true, isGroupEnd = true }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isSystem = (message.role as string) === 'system' || message.sender_type === 'system';
  const senderType = isSystem ? 'system' : (isUser ? 'user' : 'buddy');
  const config = agentConfig[senderType];
  const emotionDisplay = isUser ? getEmotionDisplay(message.emotionDetected, message.emotionScore, message.moodScore) : null;

  if (senderType === 'system') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 5 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-center w-full my-3"
      >
        <div 
          className="px-4 py-1.5 rounded-full text-xs font-semibold tracking-wide border shadow-sm select-none"
          style={{
            background: 'rgba(15, 23, 42, 0.65)',
            borderColor: 'rgba(56, 189, 248, 0.15)',
            color: '#94a3b8',
            backdropFilter: 'blur(8px)',
            WebkitBackdropFilter: 'blur(8px)',
          }}
        >
          {message.content}
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: isUser ? 20 : -20, y: 10 }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      whileHover={{ y: -0.5 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      className={`flex items-end gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      {/* Spacer or AI avatar with aura */}
      {!isUser && (
        <div className="flex-shrink-0 mb-6 w-9">
          {isGroupStart && (
            <EmotionalAura emotion={message.emotionDetected || 'neutral'}>
              <div
                className="w-9 h-9 rounded-full flex items-center justify-center text-lg select-none"
                style={{
                  background: config ? config.gradient : 'var(--gradient-primary)',
                  boxShadow: `0 0 12px ${config ? config.border : 'rgba(167, 139, 250, 0.2)'}`,
                }}
              >
                {config ? config.emoji : '💙'}
              </div>
            </EmotionalAura>
          )}
        </div>
      )}

      {/* Message content */}
      <div 
        className={`w-fit ${isUser ? 'order-1' : ''}`}
        style={{
          maxWidth: isUser ? '60%' : '70%',
        }}
      >
        {!isUser && config && isGroupStart && (
          <div 
            className="text-xs font-semibold mb-1.5 px-1 select-none flex items-center gap-1.5" 
            style={{ color: 'var(--text-secondary)' }}
          >
            <span>{config.emoji}</span>
            <span>{config.name}</span>
          </div>
        )}
        <div
          className="px-4 py-3 rounded-2xl text-sm leading-relaxed transition-all duration-300 hover:brightness-105"
          style={{
            background: isUser
              ? 'rgba(20, 35, 75, 0.8)'
              : 'rgba(10, 16, 32, 0.75)',
            border: isUser
              ? '1px solid rgba(34, 211, 238, 0.25)'
              : '1px solid rgba(123, 140, 255, 0.15)',
            boxShadow: isUser
              ? '0 4px 20px rgba(0, 0, 0, 0.2)'
              : '0 4px 20px rgba(0, 0, 0, 0.25)',
            borderBottomRightRadius: isUser ? '4px' : '20px',
            borderBottomLeftRadius: isUser ? '20px' : '4px',
            color: 'var(--text-primary)',
            backdropFilter: 'blur(12px)',
            WebkitBackdropFilter: 'blur(12px)',
          }}
        >
          <div className="markdown-content whitespace-pre-wrap">
            {message.isPlaceholder ? (
              <span className="italic opacity-70 animate-pulse inline-flex items-center gap-1">
                {message.content}
              </span>
            ) : (
              message.content
            )}
          </div>
        </div>

        {/* Timestamp & emotion */}
        {isGroupEnd && (
          <div
            className={`flex flex-col gap-1 mt-1 px-1 select-none ${
              isUser ? 'items-end' : 'items-start'
            }`}
          >
            {emotionDisplay && (
              <div
                className="flex items-center gap-1 text-[10px] text-slate-500 font-medium cursor-help"
                title={emotionDisplay.percentage ? `Confidence: ${emotionDisplay.percentage}` : undefined}
              >
                <span>{emotionDisplay.emoji}</span>
                <span className="hover:text-slate-300 transition-colors uppercase tracking-wider text-[9px]">
                  {emotionDisplay.label.toLowerCase()}
                </span>
              </div>
            )}
            <span className="text-[10px] text-slate-500 font-medium">
              {formatMessageTime(message.timestamp)}
            </span>
          </div>
        )}
      </div>
    </motion.div>
  );
}
