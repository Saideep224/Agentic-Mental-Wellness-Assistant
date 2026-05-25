'use client';

import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { motion } from 'framer-motion';
import { Send } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSend, disabled = false }: ChatInputProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  }, [input]);

  const handleSend = () => {
    if (!input.trim() || disabled) return;
    onSend(input.trim());
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.2 }}
      className="px-4 sm:px-6 py-4"
    >
      <div
        className="flex items-end gap-3 p-3 rounded-2xl transition-all duration-300"
        style={{
          background: 'var(--glass-bg)',
          border: input.trim().length > 0 ? '1px solid rgba(56, 189, 248, 0.35)' : '1px solid var(--glass-border)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          boxShadow: input.trim().length > 0 ? '0 0 25px rgba(56, 189, 248, 0.12), 0 0 15px rgba(167, 139, 250, 0.08)' : 'none',
        }}
      >
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? 'Esona is thinking...' : 'Type your message...'}
          disabled={disabled}
          rows={1}
          className="flex-1 bg-transparent resize-none text-sm leading-relaxed outline-none px-2 py-1.5"
          style={{
            color: 'var(--text-primary)',
            maxHeight: '150px',
          }}
        />

        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={handleSend}
          disabled={!input.trim() || disabled}
          className="flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-300 cursor-pointer"
          style={{
            background:
              input.trim() && !disabled
                ? 'linear-gradient(135deg, var(--accent-cyan), var(--accent-blue))'
                : 'rgba(255, 255, 255, 0.05)',
            color:
              input.trim() && !disabled
                ? 'var(--bg-primary)'
                : 'var(--text-muted)',
            opacity: input.trim() && !disabled ? 1 : 0.5,
          }}
        >
          <Send size={16} />
        </motion.button>
      </div>

      <p className="text-center mt-2 text-xs" style={{ color: 'var(--text-muted)' }}>
        Press Enter to send · Shift+Enter for new line
      </p>
    </motion.div>
  );
}
