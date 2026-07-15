'use client';

import { useRef, useEffect, ReactNode } from 'react';
import { motion } from 'framer-motion';

interface ChatContainerProps {
  children: ReactNode;
}

export default function ChatContainer({ children }: ChatContainerProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const isAtBottomRef = useRef<boolean>(true);
  const prevChildrenCountRef = useRef<number>(0);

  // Monitor scroll position to check if user is at bottom
  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const threshold = 150; // pixels from bottom
    const isAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight <= threshold;
    isAtBottomRef.current = isAtBottom;
  };

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;

    // Detect if we should scroll
    if (isAtBottomRef.current) {
      // Determine if a new message was added (count of child nodes changed)
      const maxWContainer = el.firstElementChild;
      const currentChildrenCount = maxWContainer ? maxWContainer.children.length : 0;
      const isNewMessage = currentChildrenCount !== prevChildrenCountRef.current;
      prevChildrenCountRef.current = currentChildrenCount;

      // Use 'smooth' scroll for new messages, 'auto' (instant) for streaming chunks to prevent jumpy layout/stuttering
      el.scrollTo({
        top: el.scrollHeight,
        behavior: isNewMessage ? 'smooth' : 'auto',
      });
    }
  });

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col h-full"
    >
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 space-y-4"
        style={{
          scrollBehavior: 'auto',
        }}
      >
        <div className="max-w-[1120px] mx-auto w-full space-y-4 pb-36">
          {children}
        </div>
      </div>
    </motion.div>
  );
}
