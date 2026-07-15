'use client';

import EsonaLoader from './EsonaLoader';

interface FullPageTransitionProps {
  message?: string;
}

/**
 * Unified full-screen transition loader that forwards to the optimized EsonaLoader.
 */
export default function FullPageTransition({ message }: FullPageTransitionProps) {
  return <EsonaLoader message={message} force={true} duration={1200} />;
}
