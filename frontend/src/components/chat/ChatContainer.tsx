'use client';

import { useRef, useEffect, ReactNode } from 'react';
import { motion } from 'framer-motion';

interface ChatContainerProps {
  children: ReactNode;
}

export default function ChatContainer({ children }: ChatContainerProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
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
        className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 space-y-4"
        style={{
          scrollBehavior: 'smooth',
        }}
      >
        {children}
      </div>
    </motion.div>
  );
}
