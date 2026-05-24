import { Question } from '@/types';

export const questions: Question[] = [
  // ============================================
  // CATEGORY 1: Personality & Behavioral Understanding
  // ============================================
  {
    id: 1,
    text: "After a tiring day, what do you usually do?",
    category: "personality",
    categoryLabel: "Personality & Behavior",
    agentTarget: "personality",
    allowOther: true,
    options: [
      { label: "Scroll phone in silence", value: "scroll_phone", emoji: "🛋️" },
      { label: "Put on music and zone out", value: "music_zone", emoji: "🎧" },
      { label: "Text someone to vent", value: "text_vent", emoji: "📱" },
      { label: "Go for a walk alone", value: "walk_alone", emoji: "🚶" },
      { label: "Just sleep it off", value: "sleep", emoji: "😴" },
    ],
  },
  {
    id: 2,
    text: "Which line sounds most like you?",
    category: "personality",
    categoryLabel: "Personality & Behavior",
    agentTarget: "personality",
    allowOther: true,
    options: [
      { label: "I overthink everything, even small things", value: "overthink", emoji: "🤔" },
      { label: "I go with the flow, mostly", value: "go_with_flow", emoji: "😊" },
      { label: "I act fine even when I'm not", value: "act_fine", emoji: "🎭" },
      { label: "I feel things deeply but rarely show it", value: "feel_deeply", emoji: "💭" },
      { label: "My mood changes depending on who I'm with", value: "mood_changes", emoji: "⚡" },
    ],
  },
  {
    id: 3,
    text: "What drains your energy the most?",
    category: "personality",
    categoryLabel: "Personality & Behavior",
    agentTarget: "personality",
    allowOther: true,
    options: [
      { label: "Too much socializing", value: "socializing", emoji: "👥" },
      { label: "Repeating the same routine", value: "routine", emoji: "🔄" },
      { label: "Feeling misunderstood", value: "misunderstood", emoji: "💔" },
      { label: "Pressure to perform", value: "pressure", emoji: "📋" },
      { label: "Not having purpose or direction", value: "no_purpose", emoji: "🤷" },
    ],
  },
  {
    id: 4,
    text: "How do you usually text when you're upset?",
    category: "personality",
    categoryLabel: "Personality & Behavior",
    agentTarget: "personality",
    allowOther: true,
    options: [
      { label: "I go silent", value: "go_silent", emoji: "🔇" },
      { label: "I send long emotional texts", value: "long_texts", emoji: "😤" },
      { label: "I use humor to hide it", value: "humor_hide", emoji: "😂" },
      { label: "Short replies, one-word answers", value: "short_replies", emoji: "🤏" },
      { label: "I disappear from social media", value: "disappear", emoji: "📵" },
    ],
  },
  {
    id: 5,
    text: "Your mind's default mode lately?",
    category: "personality",
    categoryLabel: "Personality & Behavior",
    agentTarget: "personality",
    allowOther: true,
    options: [
      { label: "Overthinking everything", value: "overthinking", emoji: "🌀" },
      { label: "Emotionally numb", value: "numb", emoji: "😶" },
      { label: "Anxious about the future", value: "anxious", emoji: "😰" },
      { label: "Generally calm", value: "calm", emoji: "😊" },
      { label: "Unpredictable emotional swings", value: "unpredictable", emoji: "🎢" },
    ],
  },

  // ============================================
  // CATEGORY 2: Emotional State & Stress Analysis
  // ============================================
  {
    id: 6,
    text: "What keeps your mind busy at night?",
    category: "emotion",
    categoryLabel: "Emotional State & Stress",
    agentTarget: "emotion",
    allowOther: true,
    options: [
      { label: "Future uncertainty", value: "future", emoji: "🔮" },
      { label: "Past regrets or mistakes", value: "past_regrets", emoji: "💭" },
      { label: "Relationship worries", value: "relationships", emoji: "❤️" },
      { label: "Career or academic stress", value: "career", emoji: "📚" },
      { label: "A general feeling of emptiness", value: "emptiness", emoji: "🌫️" },
    ],
  },
  {
    id: 7,
    text: "What do you do first when stressed?",
    category: "emotion",
    categoryLabel: "Emotional State & Stress",
    agentTarget: "emotion",
    allowOther: true,
    options: [
      { label: "Eat something comforting", value: "eat", emoji: "🍫" },
      { label: "Listen to music", value: "music", emoji: "🎵" },
      { label: "Scroll through social media", value: "scroll", emoji: "📱" },
      { label: "Get irritable or snap at people", value: "irritable", emoji: "😤" },
      { label: "Shut down and isolate", value: "isolate", emoji: "🧊" },
    ],
  },
  {
    id: 8,
    text: "What affects your mood the fastest?",
    category: "emotion",
    categoryLabel: "Emotional State & Stress",
    agentTarget: "emotion",
    allowOther: true,
    options: [
      { label: "Someone's tone of voice or text", value: "tone", emoji: "💬" },
      { label: "Weather or environment", value: "weather", emoji: "🌧️" },
      { label: "How productive my day was", value: "productivity", emoji: "📊" },
      { label: "Being alone too long", value: "alone", emoji: "👤" },
      { label: "Feeling rejected or ignored", value: "rejected", emoji: "💔" },
    ],
  },
  {
    id: 9,
    text: "How often do you feel mentally exhausted?",
    category: "emotion",
    categoryLabel: "Emotional State & Stress",
    agentTarget: "emotion",
    allowOther: true,
    options: [
      { label: "Almost every day", value: "every_day", emoji: "😩" },
      { label: "A few times a week", value: "few_times_week", emoji: "📅" },
      { label: "Occasionally", value: "occasionally", emoji: "🗓️" },
      { label: "Rarely", value: "rarely", emoji: "😌" },
      { label: "I don't even notice anymore", value: "dont_notice", emoji: "🤷" },
    ],
  },
  {
    id: 10,
    text: "If your emotions were weather lately, they'd be...",
    category: "emotion",
    categoryLabel: "Emotional State & Stress",
    agentTarget: "emotion",
    allowOther: true,
    options: [
      { label: "Constant light rain", value: "light_rain", emoji: "🌧️" },
      { label: "Unpredictable storms", value: "storms", emoji: "⛈️" },
      { label: "Cloudy but manageable", value: "cloudy", emoji: "☁️" },
      { label: "Mostly sunny with some clouds", value: "sunny", emoji: "🌤️" },
      { label: "Foggy and hard to see through", value: "foggy", emoji: "🌫️" },
    ],
  },

  // ============================================
  // CATEGORY 3: Hobbies & Comfort Zone
  // ============================================
  {
    id: 11,
    text: "What helps you escape reality?",
    category: "hobbies",
    categoryLabel: "Hobbies & Comfort Zone",
    agentTarget: "personality,context",
    allowOther: true,
    options: [
      { label: "Gaming or binge-watching", value: "gaming_watching", emoji: "🎮" },
      { label: "Reading or journaling", value: "reading_journaling", emoji: "📖" },
      { label: "Creative stuff (art, music, writing)", value: "creative", emoji: "🎨" },
      { label: "Physical activity", value: "physical", emoji: "🏃" },
      { label: "Sleeping", value: "sleeping", emoji: "💤" },
    ],
  },
  {
    id: 12,
    text: "What content do you connect with most?",
    category: "hobbies",
    categoryLabel: "Hobbies & Comfort Zone",
    agentTarget: "personality,context",
    allowOther: true,
    options: [
      { label: "Sad/emotional music or playlists", value: "sad_music", emoji: "🎵" },
      { label: "Deep movies or anime", value: "deep_movies", emoji: "🎭" },
      { label: "Relatable memes", value: "memes", emoji: "📱" },
      { label: "Self-improvement content", value: "self_improvement", emoji: "📚" },
      { label: "Podcasts or real stories", value: "podcasts", emoji: "🎙️" },
    ],
  },
  {
    id: 13,
    text: "Where do you feel safest emotionally?",
    category: "hobbies",
    categoryLabel: "Hobbies & Comfort Zone",
    agentTarget: "personality,context",
    allowOther: true,
    options: [
      { label: "Alone in my room", value: "alone_room", emoji: "🛏️" },
      { label: "With one close person", value: "close_person", emoji: "👫" },
      { label: "In nature or outdoors", value: "nature", emoji: "🌿" },
      { label: "In my own thoughts or journal", value: "thoughts", emoji: "📝" },
      { label: "With music on, anywhere", value: "music_anywhere", emoji: "🎧" },
    ],
  },
  {
    id: 14,
    text: "Which hobby feels most 'you'?",
    category: "hobbies",
    categoryLabel: "Hobbies & Comfort Zone",
    agentTarget: "personality,context",
    allowOther: true,
    options: [
      { label: "Music (listening or making)", value: "music", emoji: "🎵" },
      { label: "Gaming", value: "gaming", emoji: "🎮" },
      { label: "Writing or journaling", value: "writing", emoji: "📖" },
      { label: "Art, design, or photography", value: "art", emoji: "🎨" },
      { label: "Coding or building things", value: "coding", emoji: "💻" },
    ],
  },
  {
    id: 15,
    text: "What usually improves your mood fastest?",
    category: "hobbies",
    categoryLabel: "Hobbies & Comfort Zone",
    agentTarget: "personality,context",
    allowOther: true,
    options: [
      { label: "A good laugh with someone", value: "laugh", emoji: "😂" },
      { label: "The right song at the right time", value: "right_song", emoji: "🎵" },
      { label: "Achieving something small", value: "achievement", emoji: "🏆" },
      { label: "A genuine compliment", value: "compliment", emoji: "🫂" },
      { label: "Just some peace and quiet", value: "peace", emoji: "🌅" },
    ],
  },

  // ============================================
  // CATEGORY 4: Communication & Response Preference
  // ============================================
  {
    id: 16,
    text: "How should this AI talk to you?",
    category: "communication",
    categoryLabel: "Communication & Preferences",
    agentTarget: "response",
    allowOther: true,
    options: [
      { label: "Like a close friend", value: "close_friend", emoji: "👋" },
      { label: "Smart but chill", value: "smart_chill", emoji: "🧠" },
      { label: "Gentle and reassuring", value: "gentle", emoji: "💛" },
      { label: "Straightforward, no sugar-coating", value: "straightforward", emoji: "😎" },
      { label: "Warm but not overly emotional", value: "warm", emoji: "🤝" },
    ],
  },
  {
    id: 17,
    text: "What type of replies annoy you most?",
    category: "communication",
    categoryLabel: "Communication & Preferences",
    agentTarget: "response",
    allowOther: true,
    options: [
      { label: "'Everything happens for a reason'", value: "everything_reason", emoji: "🙄" },
      { label: "Toxic positivity", value: "toxic_positivity", emoji: "💪" },
      { label: "Too formal or robotic", value: "too_formal", emoji: "📏" },
      { label: "Vague or generic answers", value: "vague", emoji: "😶" },
      { label: "Long paragraphs when I need short replies", value: "long_paragraphs", emoji: "📝" },
    ],
  },
  {
    id: 18,
    text: "When emotionally low, what helps more?",
    category: "communication",
    categoryLabel: "Communication & Preferences",
    agentTarget: "response",
    allowOther: true,
    options: [
      { label: "Someone just listening", value: "listening", emoji: "👂" },
      { label: "Practical advice or perspective", value: "advice", emoji: "💡" },
      { label: "Comfort and validation", value: "comfort", emoji: "🤗" },
      { label: "Distraction or humor", value: "distraction", emoji: "😂" },
      { label: "Space and silence", value: "space", emoji: "🤫" },
    ],
  },
  {
    id: 19,
    text: "Your social battery lately?",
    category: "communication",
    categoryLabel: "Communication & Preferences",
    agentTarget: "response",
    allowOther: true,
    options: [
      { label: "Always low", value: "always_low", emoji: "🔋" },
      { label: "Depends on the person", value: "depends", emoji: "🔌" },
      { label: "I recharge alone", value: "recharge_alone", emoji: "⚡" },
      { label: "Drains quickly in groups", value: "drains_groups", emoji: "🔄" },
      { label: "Pretty balanced", value: "balanced", emoji: "💚" },
    ],
  },
  {
    id: 20,
    text: "What do you wish people understood about you?",
    category: "communication",
    categoryLabel: "Communication & Preferences",
    agentTarget: "response",
    allowOther: true,
    options: [
      { label: "That I need space, not solutions", value: "need_space", emoji: "🤫" },
      { label: "That my silence doesn't mean I'm fine", value: "silence_not_fine", emoji: "💭" },
      { label: "That I'm more sensitive than I show", value: "more_sensitive", emoji: "🎭" },
      { label: "That I can handle the truth", value: "handle_truth", emoji: "🆗" },
      { label: "That I just need consistency, not grand gestures", value: "need_consistency", emoji: "🤝" },
    ],
  },
];

export const categories = [
  {
    id: "personality",
    label: "Personality & Behavior",
    emoji: "🧠",
    description: "Let's understand how you tick — your habits, reactions, and natural tendencies.",
    color: "cyan",
  },
  {
    id: "emotion",
    label: "Emotional State & Stress",
    emoji: "💭",
    description: "Help us understand your emotional landscape and what weighs on your mind.",
    color: "purple",
  },
  {
    id: "hobbies",
    label: "Hobbies & Comfort Zone",
    emoji: "🌿",
    description: "What makes you feel safe, happy, and like yourself?",
    color: "emerald",
  },
  {
    id: "communication",
    label: "Communication & Preferences",
    emoji: "💬",
    description: "Tell us how you'd like Esona to talk with you.",
    color: "pink",
  },
];

export function getQuestionsByCategory(category: string): Question[] {
  return questions.filter((q) => q.category === category);
}

export function getCategoryForQuestion(questionIndex: number): string {
  return questions[questionIndex]?.category ?? "personality";
}

export function getCategoryInfo(category: string) {
  return categories.find((c) => c.id === category);
}
