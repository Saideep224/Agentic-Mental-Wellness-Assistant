'use client';

import { useState, useRef, useEffect, KeyboardEvent, forwardRef } from 'react';
import { motion } from 'framer-motion';
import { ArrowUp } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

const ChatInput = forwardRef<HTMLTextAreaElement, ChatInputProps>(
  ({ onSend, disabled = false }, ref) => {
    const [input, setInput] = useState('');
    const [isFocused, setIsFocused] = useState(false);
    const localRef = useRef<HTMLTextAreaElement>(null);

    // Merge forwarded ref and local ref
    const setRef = (node: HTMLTextAreaElement | null) => {
      localRef.current = node;
      if (typeof ref === 'function') {
        ref(node);
      } else if (ref) {
        (ref as React.MutableRefObject<HTMLTextAreaElement | null>).current = node;
      }
    };

    // Auto-resize textarea
    const adjustHeight = () => {
      const textarea = localRef.current;
      if (textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
      }
    };

    useEffect(() => {
      adjustHeight();
    }, [input]);

    const handleSend = () => {
      if (!input.trim() || disabled) return;
      onSend(input.trim());
      setInput('');
      if (localRef.current) {
        localRef.current.style.height = 'auto';
      }
      requestAnimationFrame(() => {
        localRef.current?.focus();
      });
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
        e.preventDefault();
        handleSend();
      }
    };

    const hasText = input.trim().length > 0;

    return (
      <div 
        className="w-full px-4 sm:px-6 pb-6 relative z-10 mx-auto max-w-[1120px] select-none"
      >
        <div
          className="flex items-end gap-3 p-2.5 transition-all duration-300 relative"
          style={{
            borderRadius: '28px',
            background: 'rgba(6, 14, 32, 0.90)',
            backdropFilter: 'blur(18px)',
            WebkitBackdropFilter: 'blur(18px)',
            border: isFocused
              ? '1px solid rgba(34, 211, 238, 0.35)'
              : '1px solid rgba(110, 150, 210, 0.18)',
            boxShadow: isFocused
              ? '0 0 25px rgba(34, 211, 238, 0.12), 0 14px 45px rgba(0, 0, 0, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.025)'
              : '0 14px 45px rgba(0, 0, 0, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.025)',
          }}
        >
          <textarea
            ref={setRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder="Message Esona..."
            disabled={disabled}
            rows={1}
            inputMode="text"
            aria-label="Message Esona"
            className="flex-1 bg-transparent resize-none text-sm leading-relaxed outline-none pl-4 pr-2 py-2"
            style={{
              color: 'var(--text-primary)',
              minHeight: '24px',
              maxHeight: '180px',
            }}
          />

          <motion.button
            whileHover={hasText && !disabled ? { scale: 1.04, y: -0.5 } : {}}
            whileTap={hasText && !disabled ? { scale: 0.96 } : {}}
            onClick={handleSend}
            disabled={!hasText || disabled}
            aria-label="Send message"
            className="flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center transition-all duration-300 cursor-pointer"
            style={{
              background:
                hasText && !disabled
                  ? 'rgba(34, 211, 238, 0.15)'
                  : 'rgba(255, 255, 255, 0.03)',
              border:
                hasText && !disabled
                  ? '1px solid rgba(34, 211, 238, 0.4)'
                  : '1px solid rgba(255, 255, 255, 0.05)',
              color:
                hasText && !disabled
                  ? '#22d3ee'
                  : 'rgba(255, 255, 255, 0.2)',
              opacity: hasText && !disabled ? 1 : 0.4,
              boxShadow: hasText && !disabled ? '0 0 12px rgba(34, 211, 238, 0.2)' : 'none',
            }}
          >
            <ArrowUp size={16} strokeWidth={2.5} />
          </motion.button>
        </div>
      </div>
    );
  }
);

ChatInput.displayName = 'ChatInput';

export default ChatInput;
