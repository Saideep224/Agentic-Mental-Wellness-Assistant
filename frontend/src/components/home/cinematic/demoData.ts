export interface FloatingThought {
  text: string;
  x: string;
  y: string;
  depth: number;
}

export interface MemoryFragment {
  text: string;
  x: string;
  y: string;
  delay: number;
}

export interface GraphNode {
  id: string;
  label: string;
  x: number; // percent
  y: number; // percent
  color: string;
}

export interface GraphEdge {
  from: string;
  to: string;
  label?: string;
  color?: string;
}

export const FLOATING_THOUGHTS: FloatingThought[] = [
  { text: "i'm fine", x: "12%", y: "20%", depth: 1 },
  { text: "just tired", x: "78%", y: "15%", depth: 2 },
  { text: "it's nothing", x: "25%", y: "75%", depth: 3 },
  { text: "idk", x: "85%", y: "70%", depth: 1 },
  { text: "leave it", x: "15%", y: "55%", depth: 2 },
  { text: "can't sleep", x: "70%", y: "45%", depth: 3 },
  { text: "my head won't stop", x: "80%", y: "80%", depth: 1 },
  { text: "nothing happened", x: "32%", y: "30%", depth: 2 }
];

export const MEMORY_FRAGMENTS: MemoryFragment[] = [
  { text: "exams next week", x: "15%", y: "25%", delay: 0.1 },
  { text: "wants to visit Japan", x: "75%", y: "20%", delay: 0.3 },
  { text: "relationship has been difficult", x: "20%", y: "70%", delay: 0.5 },
  { text: "usually overthinks at night", x: "70%", y: "75%", delay: 0.7 },
  { text: "prefers short replies", x: "45%", y: "85%", delay: 0.9 }
];

export const GRAPH_NODES: GraphNode[] = [
  { id: "you", label: "YOU", x: 50, y: 50, color: "#22d3ee" },
  { id: "college", label: "College", x: 32, y: 28, color: "#B6C2D9" },
  { id: "japan", label: "Japan", x: 68, y: 22, color: "#B6C2D9" },
  { id: "exams", label: "Exams", x: 26, y: 48, color: "#B6C2D9" },
  { id: "relationship", label: "Relationship", x: 74, y: 54, color: "#B6C2D9" },
  { id: "dreams", label: "Dreams", x: 64, y: 78, color: "#B6C2D9" },
  { id: "night", label: "Night", x: 36, y: 74, color: "#B6C2D9" },
  { id: "friends", label: "Friends", x: 50, y: 20, color: "#B6C2D9" },
  // Emotional nodes
  { id: "anxiety", label: "Anxiety", x: 12, y: 35, color: "#FB923C" },
  { id: "dream_dest", label: "Dream", x: 86, y: 16, color: "#4ADE80" },
  { id: "sadness", label: "Sadness", x: 88, y: 68, color: "#60A5FA" },
  { id: "overthinking", label: "Overthinking", x: 22, y: 84, color: "#F59E0B" },
  { id: "comfort", label: "Comfort", x: 50, y: 6, color: "#4ADE80" }
];

export const GRAPH_EDGES: GraphEdge[] = [
  // Primary connections from YOU
  { from: "you", to: "college" },
  { from: "you", to: "japan" },
  { from: "you", to: "exams" },
  { from: "you", to: "relationship" },
  { from: "you", to: "dreams" },
  { from: "you", to: "night" },
  { from: "you", to: "friends" },
  // Secondary emotional connections
  { from: "exams", to: "anxiety", label: "causes", color: "#FB923C" },
  { from: "japan", to: "dream_dest", label: "target", color: "#4ADE80" },
  { from: "relationship", to: "sadness", label: "triggers", color: "#60A5FA" },
  { from: "night", to: "overthinking", label: "amplifies", color: "#F59E0B" },
  { from: "friends", to: "comfort", label: "gives", color: "#4ADE80" }
];

export const PERSONALIZATION_PREFS = [
  "short replies",
  "gentle tone",
  "needs listening",
  "overthinks at night"
];
