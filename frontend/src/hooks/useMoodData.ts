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

      if (moods.status === 'fulfilled') {
        setMoodTrends(moods.value);
      }

      if (profile.status === 'fulfilled' && profile.value) {
        const rawProfile = profile.value as any;
        
        // Compute overall mood from trends or default to 7.0
        const averageMood = (moods.status === 'fulfilled' && moods.value.length > 0)
          ? parseFloat((moods.value.reduce((acc: number, item: any) => acc + item.score, 0) / moods.value.length).toFixed(1))
          : 7.0;

        // Compute dominant emotions based on real chat history/mood trends
        const emotionCounts: Record<string, number> = {};
        if (moods.status === 'fulfilled') {
          moods.value.forEach((item: any) => {
            if (item.emotion) {
              const em = item.emotion.toLowerCase().trim();
              emotionCounts[em] = (emotionCounts[em] || 0) + 1;
            }
          });
        }
        
        const total = Object.values(emotionCounts).reduce((a, b) => a + b, 0);
        let calculatedEmotions = [];
        if (total > 0) {
          const colors: Record<string, string> = {
            calm: '#22d3ee',
            happy: '#34d399',
            reflective: '#a78bfa',
            anxious: '#f472b6',
            sad: '#60a5fa',
            neutral: '#94a3b8',
            motivated: '#f59e0b',
            confident: '#10b981',
          };
          calculatedEmotions = Object.entries(emotionCounts).map(([emotion, count]) => {
            const label = emotion.charAt(0).toUpperCase() + emotion.slice(1);
            return {
              emotion: label,
              percentage: Math.round((count / total) * 100),
              color: colors[emotion] || '#94a3b8',
            };
          }).sort((a, b) => b.percentage - a.percentage);
        } else {
          // Default baseline emotions from onboarding
          const domEmotion = rawProfile.emotional_baseline?.dominant_emotion || rawProfile.emotional_style?.dominant_emotion || 'neutral';
          const label = domEmotion.charAt(0).toUpperCase() + domEmotion.slice(1);
          calculatedEmotions = [
            { emotion: label, percentage: 100, color: '#22d3ee' }
          ];
        }

        const mappedProfile = {
          personalityType: rawProfile.personality_type || {},
          emotionalBaseline: rawProfile.emotional_baseline || rawProfile.emotional_style || {},
          comfortPreferences: rawProfile.comfort_preferences || rawProfile.interests || {},
          communicationStyle: rawProfile.communication_style || {},
          dominantEmotions: calculatedEmotions,
          overallMood: averageMood,
          communicationStyleLabel: rawProfile.communication_style?.preferred_style || 'Empathetic Listener',
          personalityLabel: rawProfile.personality_type?.type || 'Thoughtful Processor',
        };
        
        setEmotionalProfile(mappedProfile);

        // Map communication preferences
        const cp = rawProfile.comfort_preferences || rawProfile.interests || {};
        const cs = rawProfile.communication_style || {};
        setCommunicationPrefs({
          preferredTone: cs.preferred_style || 'Warm and understanding',
          whatHelps: cp.mood_boosters || [],
          whatToAvoid: cs.annoyances || [],
        });
      }

      if (stress.status === 'fulfilled') {
        setStressPatterns(stress.value);
      }

      if (personalityInsights.status === 'fulfilled') {
        setInsights(personalityInsights.value);
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
