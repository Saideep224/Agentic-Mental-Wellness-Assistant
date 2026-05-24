'use client';

import { useState, useEffect, useCallback } from 'react';
import { MoodDataPoint, EmotionalProfile, StressPattern, PersonalityInsight, CommunicationPreference } from '@/types';
import * as api from '@/lib/api';

export function useMoodData() {
  const [moodTrends, setMoodTrends] = useState<MoodDataPoint[]>([]);
  const [emotionalProfile, setEmotionalProfile] = useState<EmotionalProfile | null>(null);
  const [stressPatterns, setStressPatterns] = useState<StressPattern[]>([]);
  const [insights, setInsights] = useState<PersonalityInsight[]>([]);
  const [communicationPrefs, setCommunicationPrefs] = useState<CommunicationPreference | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    const token = api.getToken();
    if (!token) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const [moods, profile, stress, personalityInsights] = await Promise.allSettled([
        api.getMoodTrends(token),
        api.getEmotionalProfile(token),
        api.getStressPatterns(token),
        api.getInsights(token),
      ]);

      if (moods.status === 'fulfilled') setMoodTrends(moods.value);
      if (profile.status === 'fulfilled') setEmotionalProfile(profile.value);
      if (stress.status === 'fulfilled') setStressPatterns(stress.value);
      if (personalityInsights.status === 'fulfilled') setInsights(personalityInsights.value);

      // Extract communication preferences from profile if available
      if (profile.status === 'fulfilled' && profile.value.comfortPreferences) {
        const cp = profile.value.comfortPreferences as Record<string, unknown>;
        setCommunicationPrefs({
          preferredTone: (cp.preferredTone as string) || 'Warm and understanding',
          whatHelps: (cp.whatHelps as string[]) || [],
          whatToAvoid: (cp.whatToAvoid as string[]) || [],
        });
      }
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
      setError('Unable to load your dashboard data. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  return {
    moodTrends,
    emotionalProfile,
    stressPatterns,
    insights,
    communicationPrefs,
    isLoading,
    error,
    refresh: fetchAll,
  };
}
