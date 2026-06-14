'use client';

import { motion } from 'framer-motion';
import { Message } from '@/types';
import { formatMessageTime } from '@/utils';
import EmotionalAura from './EmotionalAura';

interface MessageBubbleProps {
  message: Message;
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

  const percentage = score !== null ? ` (${Math.round(score * 100)}%)` : '';
  
  return { emoji, label, percentage };
};

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const emotionDisplay = getEmotionDisplay(message.emotionDetected, message.emotionScore, message.moodScore);

  return (
    <motion.div
      initial={{ opacity: 0, x: isUser ? 20 : -20, y: 10 }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      whileHover={{ y: -1 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      className={`flex items-end gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      {/* AI avatar with aura */}
      {!isUser && (
        <div className="flex-shrink-0 mb-6">
          <EmotionalAura emotion={message.emotionDetected || 'neutral'}>
            <div
              className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold"
              style={{
                background: 'var(--gradient-primary)',
                color: 'var(--bg-primary)',
              }}
            >
              E
            </div>
          </EmotionalAura>
        </div>
      )}

      {/* Message content */}
      <div className={`max-w-[75%] ${isUser ? 'order-1' : ''}`}>
        <div
          className="px-4 py-3 rounded-2xl text-sm leading-relaxed transition-all duration-300 hover:brightness-105"
          style={{
            background: isUser
              ? 'linear-gradient(135deg, rgba(56, 189, 248, 0.15) 0%, rgba(59, 130, 246, 0.08) 100%)'
              : 'linear-gradient(135deg, rgba(167, 139, 250, 0.1) 0%, rgba(244, 114, 182, 0.05) 100%)',
            border: isUser
              ? '1px solid rgba(56, 189, 248, 0.25)'
              : '1px solid rgba(167, 139, 250, 0.18)',
            boxShadow: isUser
              ? '0 4px 15px rgba(56, 189, 248, 0.04)'
              : '0 4px 15px rgba(167, 139, 250, 0.03)',
            borderBottomRightRadius: isUser ? '6px' : '18px',
            borderBottomLeftRadius: isUser ? '18px' : '6px',
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
        <div
          className={`flex flex-col gap-1 mt-1.5 px-1 ${
            isUser ? 'items-end' : 'items-start'
          }`}
        >
          {emotionDisplay && (
            <div
              className="flex items-center gap-1.5 text-[11px] px-2 py-0.5 rounded-full mb-0.5"
              style={{
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid rgba(255, 255, 255, 0.05)',
                color: 'var(--text-muted)',
                backdropFilter: 'blur(4px)',
              }}
            >
              <span className="opacity-75">Detected Emotion:</span>
              <span className="font-semibold text-[var(--text-primary)] flex items-center gap-1">
                <span>{emotionDisplay.emoji}</span>
                <span>{emotionDisplay.label}</span>
                {emotionDisplay.percentage && (
                  <span className="opacity-75 font-normal text-[10px]">{emotionDisplay.percentage}</span>
                )}
              </span>
            </div>
          )}
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
            {formatMessageTime(message.timestamp)}
          </span>
        </div>
      </div>
    </motion.div>
  );
}
