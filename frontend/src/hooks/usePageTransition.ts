'use client';

import { useState, useCallback } from 'react';

const MIN_DISPLAY_MS = 1000;

interface UsePageTransitionReturn {
  isTransitioning: boolean;
  startTransition: (asyncFn: () => Promise<void>) => Promise<void>;
}

/**
 * Enforces a minimum loader display time for any async operation.
 *
 * Usage:
 *   const { isTransitioning, startTransition } = usePageTransition();
 *   await startTransition(async () => { const data = await fetchData(); setState(data); });
 *
 * The loader remains visible for at least MIN_DISPLAY_MS (1000ms) regardless
 * of how fast the async function resolves.
 */
export function usePageTransition(): UsePageTransitionReturn {
  const [isTransitioning, setIsTransitioning] = useState(false);

  const startTransition = useCallback(async (asyncFn: () => Promise<void>) => {
    setIsTransitioning(true);
    const t0 = Date.now();
    try {
      await asyncFn();
    } finally {
      const elapsed = Date.now() - t0;
      const remaining = MIN_DISPLAY_MS - elapsed;
      if (remaining > 0) {
        await new Promise<void>((resolve) => setTimeout(resolve, remaining));
      }
      setIsTransitioning(false);
    }
  }, []);

  return { isTransitioning, startTransition };
}
