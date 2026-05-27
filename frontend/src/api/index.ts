/**
 * API barrel re-export — provides backward compatibility for `import * as api from '@/api'`.
 * 
 * For new code, prefer importing from specific sub-modules:
 *   import { getToken } from '@/api/client';
 *   import { sendMessage } from '@/api/chat';
 */

export * from './client';
export * from './auth';
export * from './chat';
export * from './onboarding';
export * from './dashboard';
export * from './supabaseSync';
