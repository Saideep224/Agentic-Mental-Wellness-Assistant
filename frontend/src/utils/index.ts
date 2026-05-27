/**
 * Utility functions — class merging, date formatting, emotion colors, localStorage helpers.
 */

import clsx, { ClassValue } from 'clsx';
import { format, formatDistanceToNow, isToday, isYesterday } from 'date-fns';

/**
 * Merge class names with clsx
 */
export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}

/**
 * Generate a unique ID
 */
export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
}

/**
 * Format a date for display
 */
export function formatDate(date: Date | string | null | undefined): string {
  if (!date) return 'Just now';
  try {
    const d = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(d.getTime())) return 'Just now';

    const getLocalDateString = (dateObj: Date) => {
      return dateObj.toLocaleDateString("en-IN", {
        timeZone: "Asia/Kolkata",
        year: "numeric",
        month: "numeric",
        day: "numeric",
      });
    };

    const dString = getLocalDateString(d);
    const today = new Date();
    const todayString = getLocalDateString(today);

    const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
    const yesterdayString = getLocalDateString(yesterday);

    const timeString = d.toLocaleString("en-IN", {
      timeZone: "Asia/Kolkata",
      hour: "numeric",
      minute: "numeric",
      hour12: true
    });

    if (dString === todayString) {
      return timeString;
    }
    if (dString === yesterdayString) {
      return `Yesterday at ${timeString}`;
    }

    return d.toLocaleDateString("en-IN", {
      timeZone: "Asia/Kolkata",
      month: "short",
      day: "numeric",
      year: "numeric"
    });
  } catch {
    return 'Just now';
  }
}

/**
 * Format a date as relative time
 */
export function formatRelativeTime(date: Date | string | null | undefined): string {
  if (!date) return 'just now';
  try {
    const d = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(d.getTime())) return 'just now';
    return formatDistanceToNow(d, { addSuffix: true });
  } catch {
    return 'just now';
  }
}

/**
 * Format timestamp for chat messages
 */
export function formatMessageTime(date: Date | string | null | undefined): string {
  if (!date) return '';
  try {
    const d = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(d.getTime())) return '';
    return d.toLocaleString("en-IN", {
      timeZone: "Asia/Kolkata",
      hour: "numeric",
      minute: "numeric",
      hour12: true
    });
  } catch {
    return '';
  }
}

/**
 * Truncate text to a maximum length
 */
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength).trim() + '...';
}

/**
 * Delay / sleep utility
 */
export function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Get emotion color mapping
 */
export function getEmotionColor(emotion: string): string {
  const em = (emotion || '').toLowerCase();
  if (em.includes('calm')) return '#22d3ee'; // cyan
  if (em.includes('sad') || em.includes('melancholy') || em.includes('numb')) return '#64748b'; // muted blue-gray
  if (em.includes('overthink') || em.includes('spiral')) return '#5b21b6'; // dark violet
  if (em.includes('stress') || em.includes('anx') || em.includes('burnout') || em.includes('exhaust') || em.includes('overwhelm')) return '#a855f7'; // soft purple
  return '#2dd4bf'; // aqua/teal fallback
}

/**
 * Get emotion glow CSS
 */
export function getEmotionGlow(emotion: string): string {
  const em = (emotion || '').toLowerCase();
  if (em.includes('calm')) return '0 0 20px rgba(34, 211, 238, 0.4)';
  if (em.includes('sad') || em.includes('melancholy') || em.includes('numb')) return '0 0 20px rgba(100, 116, 139, 0.4)';
  if (em.includes('overthink') || em.includes('spiral')) return '0 0 20px rgba(91, 33, 182, 0.4)';
  if (em.includes('stress') || em.includes('anx') || em.includes('burnout') || em.includes('exhaust') || em.includes('overwhelm')) return '0 0 20px rgba(168, 85, 247, 0.4)';
  return '0 0 20px rgba(45, 212, 191, 0.4)';
}

/**
 * Check if we're in the browser
 */
export function isBrowser(): boolean {
  return typeof window !== 'undefined';
}

/**
 * Safe localStorage getter
 */
export function getFromStorage(key: string): string | null {
  if (!isBrowser()) return null;
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

/**
 * Safe localStorage setter
 */
export function setToStorage(key: string, value: string): void {
  if (!isBrowser()) return;
  try {
    localStorage.setItem(key, value);
  } catch {
    // Storage might be full or restricted
  }
}

/**
 * Safe localStorage remover
 */
export function removeFromStorage(key: string): void {
  if (!isBrowser()) return;
  try {
    localStorage.removeItem(key);
  } catch {
    // Ignore errors
  }
}
