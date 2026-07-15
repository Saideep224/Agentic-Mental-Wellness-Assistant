'use client';

import { ReactNode, forwardRef, UIEvent } from 'react';

interface ChatContainerProps {
  children: ReactNode;
  onScroll?: (event: UIEvent<HTMLDivElement>) => void;
}

const ChatContainer = forwardRef<HTMLDivElement, ChatContainerProps>(
  ({ children, onScroll }, ref) => {
    return (
      <div className="flex flex-col h-full overflow-hidden select-none">
        <div
          ref={ref}
          onScroll={onScroll}
          className="flex-1 overflow-y-auto px-4 sm:px-6 py-4"
          style={{
            scrollBehavior: 'auto',
          }}
        >
          <div className="max-w-[1120px] mx-auto w-full flex flex-col pb-36">
            {children}
          </div>
        </div>
      </div>
    );
  }
);

ChatContainer.displayName = 'ChatContainer';

export default ChatContainer;
