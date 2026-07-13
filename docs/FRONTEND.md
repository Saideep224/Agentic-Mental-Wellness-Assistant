# Frontend Architecture

The Esona client is a Next.js (Next 15) Single Page Application built using React, TypeScript, Tailwind CSS, and Framer Motion. It implements a premium glassmorphic dark interface optimized for desktop and mobile layouts.

## Page Routing & Navigation

Esona utilizes the standard Next.js App Router:
- **`/` (Homepage)**: Renders a custom vertical scrolling cinematic home (`CinematicHome.tsx`) introducing Esona's core concepts (emotions, memories, knowledge graph, personalization) via interactive GSAP-like Framer Motion scroll sections.
- **`/login`**: Houses the Supabase OAuth / Credentials login panel.
- **`/onboarding`**: Houses the 27-question personal onboarding wizard. Uses smooth category transitions, double-click prevention, and live-saving progress.
- **`/knowing-me`**: Sequential questionnaire allowing users to answer additional daily mental health prompts.
- **`/chat`**: Standard chat panel. Displays chat history sidebar, dynamic emotional aura backgrounds, and standard message bubbles.
- **`/dashboard`**: Renders the "My Growth" dashboard, including interactive charts for mood, stress, and anxiety.

---

## Component Taxonomy

- **`ambient/`**:
  - `VideoBackground.tsx`: Renders time-of-day dynamic MP4 loops (`BG1.mp4` / `BG2.mp4`) with fade-in overlay.
  - `BreathingOrb.tsx`: Custom SVG glowing pulse representing mindfulness prompts.
  - `FloatingParticles.tsx`: Canvas particle field reacting to UI hover states.
- **`chat/`**:
  - `MessageBubble.tsx`: Renders incoming AI messages and outgoing user text with custom emotional aura glows.
  - `MoodMusicPanel.tsx`: Soundboard containing calm, happy, and grounding loops.
  - `ChatInput.tsx`: Custom auto-resizing text field supporting keyboard shortcuts.
- **`dashboard/`**:
  - `MoodTrendChart.tsx` & `StressPatternChart.tsx`: Renders responsive SVG charts using Recharts.
- **`layout/`**:
  - `Navbar.tsx` & `ProfileModal.tsx`: Global navigation header and profile editors.
  - `FullPageTransition.tsx`: Translucent loading gate for route switches.

---

## Custom Hooks

- **`useChat`**: Orchestrates sending queries, appending bubbles, reading SSE chunks, and syncing local state with database logs.
- **`useOnboarding`**: Manages current question indices, validation, answer saving, and redirection.
- **`useMoodData`**: Fetches and formats mood history coordinates for dashboard widgets.
- **`useAmbientAudio`**: Manages Web Audio API triggers for the soundboard.
