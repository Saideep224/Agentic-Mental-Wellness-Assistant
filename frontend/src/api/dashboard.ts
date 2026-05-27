/**
 * Dashboard API — mood trends, emotional profile, stress patterns, insights.
 */

import { MoodDataPoint, EmotionalProfile, StressPattern, PersonalityInsight } from '@/types';
import { apiGet } from './client';

export async function getMoodTrends(token: string): Promise<MoodDataPoint[]> {
  const data = await apiGet<any>('/api/dashboard/mood-trends', token);
  if (data && Array.isArray(data.data_points)) {
    return data.data_points.map((dp: any) => ({
      date: dp.date,
      score: dp.mood_score,
      emotion: dp.emotion || '',
    }));
  }
  return [];
}

export async function getEmotionalProfile(token: string): Promise<EmotionalProfile> {
  return apiGet<EmotionalProfile>('/api/dashboard/emotional-profile', token);
}

export async function getStressPatterns(token: string): Promise<StressPattern[]> {
  const data = await apiGet<any>('/api/dashboard/stress-patterns', token);
  if (data && Array.isArray(data.patterns)) {
    return data.patterns;
  }
  return [];
}

export async function getInsights(token: string): Promise<PersonalityInsight[]> {
  const data = await apiGet<any>('/api/dashboard/insights', token);
  if (data && Array.isArray(data.insights)) {
    return data.insights.map((item: any) => {
      let trait = item.category || 'Insight';
      let icon = '✨';
      
      // Simple emoji extractor
      const emojiRegex = /[\u00a9\u00ae\u2000-\u3300\ud83c\ud83d\ud83e]/g;
      const match = trait.match(emojiRegex);
      if (match && match.length > 0) {
        icon = match[0];
        trait = trait.replace(emojiRegex, '').trim();
      }
      
      return {
        trait,
        description: item.insight,
        strength: Math.round((item.confidence || 0.8) * 100),
        icon,
      };
    });
  }
  return [];
}
