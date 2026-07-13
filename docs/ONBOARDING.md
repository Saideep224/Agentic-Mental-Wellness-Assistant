# Onboarding Questionnaire Flow

The onboarding questionnaire is a 27-question onboarding experience designed to discover the user's emotional state, lifestyle, habits, and communication preferences.

## Onboarding Question Structure

Questions are split into 5 categories, defined in [questions.ts](file:///e:/2026%20research%20intern/esona/frontend/src/data/questions.ts):
1. **Background (Q1 - Q5)**: Occupation, field, primary challenge, advice style preference, support needs.
2. **Personality (Q6 - Q10)**: Coping styles, self-description, energy drains, texting patterns under distress, mind defaults.
3. **Emotion (Q11 - Q15)**: Insomnia triggers, stress responses, mood variables, exhaustion frequencies, weather metaphor.
4. **Hobbies (Q16 - Q20)**: Escape mechanics, media connections, emotional safespans, hobbies, mood lifters.
5. **Communication (Q21 - Q27)**: Preferred AI tone, conversational annoyances, comfort mechanisms, social battery, age, gender.

---

## Live-Saving Progress
- **Live Saving**: Every time a user clicks "Next" after selecting an answer, the frontend invokes `/api/onboarding/answer` to write that answer directly to the `user_question_answers` database table.
- **Onboarding Sync**: On page load, the frontend checks `/api/onboarding/status`. If the user has a partially filled onboarding state, it downloads their previous answers, restores their position, and loads the active question, allowing them to resume without starting over.
- **Save Status Indicator**: A progress badge shows saving status ("Saving...", "Saved", or "Connection Offline").

---

## Onboarding Completion & Profile Generation
When the final question is answered and the user clicks submit:
1. The frontend calls `/api/onboarding/submit`.
2. The backend validates that all required questions are answered.
3. The backend calculates the initial `UserPersonalProfile` using a semantic mapping service (`derive_personality_profile`).
4. A background task triggers `analyze_onboarding` to run a deep analyzer, establishing the user's base personality traits, stress triggers, and custom coping strategies.
5. The `onboarding_completed` flag on `profiles` is toggled to `true`, granting access to the chat dashboard.
