'use client';

import { motion } from 'framer-motion';
import { Message } from '@/types';
import { formatMessageTime } from '@/lib/utils';
import EmotionalAura from './EmotionalAura';

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <motion.div
      initial={{ opacity: 0, x: isUser ? 20 : -20, y: 10 }}
      animate={{ opacity: 1, x: 0, y: 0 }}
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
                background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-purple))',
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
          className="px-4 py-3 rounded-2xl text-sm leading-relaxed"
          style={{
            background: isUser
              ? 'rgba(56, 189, 248, 0.12)'
              : 'rgba(167, 139, 250, 0.08)',
            border: isUser
              ? '1px solid rgba(56, 189, 248, 0.2)'
              : '1px solid rgba(167, 139, 250, 0.15)',
            borderBottomRightRadius: isUser ? '6px' : '18px',
            borderBottomLeftRadius: isUser ? '18px' : '6px',
            color: 'var(--text-primary)',
            backdropFilter: 'blur(10px)',
            WebkitBackdropFilter: 'blur(10px)',
          }}
        >
          <div className="markdown-content whitespace-pre-wrap">{message.content}</div>
        </div>

        {/* Timestamp & emotion */}
        <div
          className={`flex items-center gap-2 mt-1.5 px-1 ${
            isUser ? 'justify-end' : 'justify-start'
          }`}
        >
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
            {formatMessageTime(message.timestamp)}
          </span>
        </div>
      </div>
    </motion.div>
  );
}
