export interface Track {
  id: string;
  title: string;
  artist: string;
  src: string;
  categories: string[];
  energy: 'low' | 'medium' | 'high';
  attributionUrl?: string;
}

export const musicLibrary: Track[] = [
  {
    id: "happy-happy-upbeat-496594",
    title: "Happy Happy Upbeat",
    artist: "The Mountain",
    src: "/music/happy/the_mountain-happy-happy-upbeat-496594.mp3",
    categories: ["happy", "energetic"],
    energy: "high",
    attributionUrl: "https://pixabay.com/music/upbeat-the-mountain-happy-happy-upbeat-496594/"
  },
  {
    id: "energetic-action-sport-500409",
    title: "Energetic Action Sport",
    artist: "AlexGrohl",
    src: "/music/energetic/alexgrohl-energetic-action-sport-500409.mp3",
    categories: ["energetic", "happy"],
    energy: "high",
    attributionUrl: "https://pixabay.com/music/upbeat-alexgrohl-energetic-action-sport-500409/"
  },
  {
    id: "energetic-upbeat-background-music-330148",
    title: "Energetic Upbeat Background Music",
    artist: "LNPlusMusic",
    src: "/music/energetic/lnplusmusic-energetic-upbeat-background-music-330148.mp3",
    categories: ["energetic"],
    energy: "high",
    attributionUrl: "https://pixabay.com/music/upbeat-lnplusmusic-energetic-upbeat-background-music-330148/"
  },
  {
    id: "ambient-calm-ambient-dreamscape-529861",
    title: "Ambient Calm Ambient Dreamscape",
    artist: "Morgan",
    src: "/music/calm/morgan-ambient-calm-ambient-dreamscape-529861.mp3",
    categories: ["calm"],
    energy: "low",
    attributionUrl: "https://pixabay.com/music/ambient-morgan-ambient-calm-ambient-dreamscape-529861/"
  },
  {
    id: "relaxing-145038",
    title: "Relaxing",
    artist: "Music For Videos",
    src: "/music/calm/music_for_videos-relaxing-145038.mp3",
    categories: ["calm", "grounding"],
    energy: "low",
    attributionUrl: "https://pixabay.com/music/relaxing-music-for-videos-relaxing-145038/"
  },
  {
    id: "spa-560318",
    title: "Spa",
    artist: "Mirostar",
    src: "/music/calm/mirostar-spa-560318.mp3",
    categories: ["calm", "grounding"],
    energy: "low",
    attributionUrl: "https://pixabay.com/music/ambient-mirostar-spa-560318/"
  },
  {
    id: "deep-grounding-earth-bowl-vibrations-388623",
    title: "Deep Grounding Earth Bowl Vibrations",
    artist: "MeditativeTiger",
    src: "/music/grounding/meditativetiger-deep-grounding-earth-bowl-vibrations-388623.mp3",
    categories: ["grounding", "calm"],
    energy: "low",
    attributionUrl: "https://pixabay.com/music/ambient-meditativetiger-deep-grounding-earth-bowl-vibrations-388623/"
  }
];
