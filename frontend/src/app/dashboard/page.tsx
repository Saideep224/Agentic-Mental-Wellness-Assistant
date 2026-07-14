'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  RefreshCw, Sparkles, ChevronDown, ChevronUp, Loader2,
  Heart, Wind, Compass, Info, X, Cloud, Zap, Flame, MoveUp, MoveDown, HelpCircle
} from 'lucide-react';
import Link from 'next/link';
import Navbar from '@/components/layout/Navbar';
import FullPageTransition from '@/components/layout/FullPageTransition';
import { useMoodData } from '@/hooks/useMoodData';
import { getToken, getStoredUser, recalculateProfile } from '@/api';
import { questions } from '@/data/questions';

// ============================================
// SUB-COMPONENTS FOR MY GROWTH PAGE
// ============================================

// 1. Inner Weather Component
function InnerWeather({ weather }: { weather: any }) {
  if (!weather) return (
    <div className="glass-card p-6 text-center text-slate-500 italic text-xs">
      No emotional logs recorded yet. Start chatting to reflect your inner weather! 🌤️
    </div>
  );

  const getEnergyColor = (val: string) => {
    if (val === 'LOW') return 'text-violet-400 border-violet-500/20 bg-violet-500/5';
    if (val === 'HIGH') return 'text-sky-400 border-sky-500/20 bg-sky-500/5';
    return 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5';
  };

  const getLoadColor = (val: string) => {
    if (val === 'HIGH') return 'text-pink-400 border-pink-500/20 bg-pink-500/5';
    if (val === 'MEDIUM') return 'text-amber-400 border-amber-500/20 bg-amber-500/5';
    return 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5';
  };

  const getDirectionColor = (val: string) => {
    if (val === 'UNSETTLED') return 'text-rose-400 border-rose-500/20 bg-rose-500/5';
    if (val === 'IMPROVING') return 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5';
    return 'text-cyan-400 border-cyan-500/20 bg-cyan-500/5';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-6 relative overflow-hidden"
    >
      {/* Glow accent */}
      <div className="absolute -right-10 -top-10 w-24 h-24 rounded-full bg-cyan-500/5 blur-2xl pointer-events-none" />

      <h3 className="text-xs uppercase tracking-widest text-slate-500 font-semibold mb-6 flex items-center gap-1.5">
        <Cloud size={14} className="text-cyan-400" />
        Your Inner Weather
      </h3>

      <div className="text-center py-4 mb-6">
        <h4 className="text-lg sm:text-xl font-bold text-white mb-2" style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}>
          &ldquo;{weather.description}&rdquo;
        </h4>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className={`p-3 rounded-xl border text-center ${getEnergyColor(weather.energy)}`}>
          <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-1">Energy</div>
          <div className="text-sm font-bold flex items-center justify-center gap-1">
            <Flame size={14} />
            {weather.energy}
          </div>
        </div>

        <div className={`p-3 rounded-xl border text-center ${getLoadColor(weather.mind_load)}`}>
          <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-1">Mind Load</div>
          <div className="text-sm font-bold flex items-center justify-center gap-1">
            <Zap size={14} />
            {weather.mind_load}
          </div>
        </div>

        <div className={`p-3 rounded-xl border text-center ${getDirectionColor(weather.emotional_direction)}`}>
          <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-1">Direction</div>
          <div className="text-sm font-bold flex items-center justify-center gap-1">
            <Compass size={14} />
            {weather.emotional_direction}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// 2. Esona Noticed Component (Dismissible behavioral patterns)
function EsonaNoticed({ notices }: { notices: any[] }) {
  const [activeNotices, setActiveNotices] = useState<any[]>([]);

  useEffect(() => {
    if (notices) {
      setActiveNotices(notices);
    }
  }, [notices]);

  const handleDismiss = (id: string) => {
    setActiveNotices(prev => prev.filter(n => n.id !== id));
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-6"
    >
      <h3 className="text-xs uppercase tracking-widest text-slate-500 font-semibold mb-4 flex items-center gap-1.5">
        <Sparkles size={14} className="text-cyan-400" />
        Esona Noticed
      </h3>

      <div className="space-y-3">
        <AnimatePresence mode="popLayout">
          {activeNotices.length > 0 ? (
            activeNotices.map((notice) => (
              <motion.div
                key={notice.id}
                layout
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, x: -30, scale: 0.95 }}
                transition={{ duration: 0.2 }}
                className="p-4 rounded-xl bg-white/2 border border-white/5 flex items-start justify-between gap-4"
              >
                <div>
                  <h4 className="text-xs font-bold text-cyan-400 mb-1">{notice.pattern}</h4>
                  <p className="text-xs text-slate-300 leading-relaxed">{notice.evidence}</p>
                </div>
                <button
                  onClick={() => handleDismiss(notice.id)}
                  className="p-1 rounded-lg hover:bg-white/5 text-slate-500 hover:text-rose-400 transition-colors cursor-pointer"
                  title="Not quite me"
                >
                  <X size={14} />
                </button>
              </motion.div>
            ))
          ) : (
            <div className="text-center py-6 text-xs text-slate-500 italic">
              All cleared! Start chatting more to unlock new patterns. 🌿
            </div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

// 3. Emotional Constellation Component (SVG Theme Visualizer)
function EmotionalConstellation({ constellation }: { constellation: any }) {
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  if (!constellation || !constellation.nodes || constellation.nodes.length === 0) return null;

  const nodes = constellation.nodes;
  const links = constellation.links;

  // Simple deterministic circular layout for visual stability
  const width = 360;
  const height = 260;
  const cx = width / 2;
  const cy = height / 2;
  const r = 85;

  const nodeCoords = nodes.map((node: any, idx: number) => {
    if (node.id === 'you') {
      return { ...node, x: cx, y: cy };
    }
    const angle = ((idx - 1) / (nodes.length - 1)) * 2 * Math.PI;
    return {
      ...node,
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
    };
  });

  const getCoords = (id: string) => {
    const found = nodeCoords.find((n: any) => n.id === id);
    return found ? { x: found.x, y: found.y } : { x: cx, y: cy };
  };

  const getNodeColor = (type: string) => {
    if (type === 'user') return 'fill-cyan-400/20 stroke-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.5)]';
    if (type === 'stressor') return 'fill-pink-500/10 stroke-pink-400';
    if (type === 'coping') return 'fill-emerald-500/10 stroke-emerald-400';
    return 'fill-purple-500/10 stroke-purple-400';
  };

  const getExerciseRecommendation = (label: string) => {
    const clean = label.toLowerCase();
    if (clean.includes('stud') || clean.includes('exam') || clean.includes('career')) return 'Thought Untangle';
    if (clean.includes('sleep') || clean.includes('tir') || clean.includes('exhaust')) return 'Sensory Grounding';
    return 'Box Breathing';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-6 flex flex-col md:grid md:grid-cols-5 gap-6"
    >
      <div className="md:col-span-3 flex flex-col">
        <h3 className="text-xs uppercase tracking-widest text-slate-500 font-semibold mb-2 flex items-center gap-1.5">
          <Compass size={14} className="text-cyan-400" />
          Emotional Constellation
        </h3>
        <p className="text-[10px] text-slate-500 mb-4">
          Click on nodes to explore triggers, coping mechanisms, and personalized Calm spaces.
        </p>

        <div ref={containerRef} className="relative w-full aspect-[4/3] bg-slate-950/20 rounded-2xl border border-white/5 overflow-hidden flex items-center justify-center">
          <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full">
            {/* Draw Links */}
            {links.map((link: any, idx: number) => {
              const start = getCoords(link.source);
              const end = getCoords(link.target);
              return (
                <line
                  key={idx}
                  x1={start.x}
                  y1={start.y}
                  x2={end.x}
                  y2={end.y}
                  className="stroke-slate-700/40 stroke-1 stroke-dasharray-[4,4] animate-[dash_20s_linear_infinite]"
                  strokeDasharray="4,4"
                />
              );
            })}

            {/* Draw Nodes */}
            {nodeCoords.map((node: any, idx: number) => {
              const isSelected = selectedNode?.id === node.id;
              const radius = node.type === 'user' ? 22 : 14 + (node.weight || 0.5) * 6;
              return (
                <g
                  key={node.id}
                  onClick={() => setSelectedNode(node)}
                  className="cursor-pointer group"
                >
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={radius}
                    className={`transition-all duration-300 stroke-1 ${getNodeColor(node.type)} ${
                      isSelected ? 'stroke-[2px] scale-110 shadow-lg' : 'hover:stroke-[1.5px] hover:stroke-cyan-300'
                    }`}
                    style={{
                      filter: isSelected ? 'drop-shadow(0 0 8px currentColor)' : 'none'
                    }}
                  />
                  <text
                    x={node.x}
                    y={node.y + radius + 12}
                    textAnchor="middle"
                    className={`text-[8px] font-medium tracking-wide ${
                      isSelected ? 'fill-cyan-400 font-bold' : 'fill-slate-400 group-hover:fill-slate-200'
                    }`}
                  >
                    {node.label}
                  </text>
                  {node.type === 'user' && (
                    <text
                      x={node.x}
                      y={node.y + 3}
                      textAnchor="middle"
                      className="text-[9px] font-bold fill-cyan-400 pointer-events-none"
                    >
                      Me
                    </text>
                  )}
                </g>
              );
            })}
          </svg>
        </div>
      </div>

      <div className="md:col-span-2 flex flex-col justify-between p-4 rounded-xl border border-white/5 bg-slate-900/10 backdrop-blur-sm min-h-[220px]">
        {selectedNode && selectedNode.id !== 'you' ? (
          <div className="flex flex-col h-full justify-between gap-4">
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <span className="px-2 py-0.5 rounded text-[8px] font-bold uppercase bg-cyan-500/10 text-cyan-400 border border-cyan-500/10">
                  {selectedNode.type}
                </span>
              </div>
              <h4 className="text-sm font-bold text-white mb-1">{selectedNode.label}</h4>
              <p className="text-xs text-slate-400 leading-relaxed mb-3">
                This theme shows up in your conversations. We suggest focusing on the Calm space activity below to ground yourself.
              </p>

              <div className="p-3 rounded-lg bg-slate-950/20 border border-white/5">
                <div className="text-[10px] text-slate-500 font-semibold mb-1 uppercase">Recommended Exercise</div>
                <div className="text-xs font-bold text-emerald-400 flex items-center gap-1">
                  <Wind size={12} />
                  {getExerciseRecommendation(selectedNode.label)}
                </div>
              </div>
            </div>

            <Link
              href={`/chat?topic=${encodeURIComponent(selectedNode.label)}`}
              className="flex items-center justify-center gap-1.5 w-full py-2.5 rounded-lg text-xs font-semibold bg-cyan-400 text-bg-primary hover:bg-cyan-300 transition-all cursor-pointer text-center"
            >
              Talk about this with Esona
            </Link>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center text-center h-full gap-2 py-6">
            <Info size={24} className="text-slate-600" />
            <p className="text-xs text-slate-500 max-w-[180px] leading-relaxed">
              Click any element of your constellation to view details and recommendations.
            </p>
          </div>
        )}
      </div>
    </motion.div>
  );
}

// 4. Calm Space Exercises
function CalmSpace({ exercises }: { exercises: any }) {
  const [activeTab, setActiveTab] = useState<'breathe' | 'ground' | 'drift'>('breathe');

  // Box Breathing State
  const [breathState, setBreathState] = useState<'Inhale' | 'Hold' | 'Exhale' | 'Hold.'>('Inhale');
  const [breathSeconds, setBreathSeconds] = useState(4);
  const breathTimerRef = useRef<any>(null);

  useEffect(() => {
    if (activeTab === 'breathe') {
      breathTimerRef.current = setInterval(() => {
        setBreathSeconds(prev => {
          if (prev <= 1) {
            setBreathState(state => {
              if (state === 'Inhale') return 'Hold';
              if (state === 'Hold') return 'Exhale';
              if (state === 'Exhale') return 'Hold.';
              return 'Inhale';
            });
            return 4;
          }
          return prev - 1;
        });
      }, 1000);
    } else {
      if (breathTimerRef.current) clearInterval(breathTimerRef.current);
    }

    return () => {
      if (breathTimerRef.current) clearInterval(breathTimerRef.current);
    };
  }, [activeTab]);

  // Grounding Container State
  const [groundStep, setGroundStep] = useState(1);
  const [groundInputs, setGroundInputs] = useState<string[]>([]);
  const [currentInput, setCurrentInput] = useState('');

  const steps = [
    { num: 5, label: "things you can SEE 👀" },
    { num: 4, label: "things you can TOUCH 🤝" },
    { num: 3, label: "things you can HEAR 👂" },
    { num: 2, label: "things you can SMELL 👃" },
    { num: 1, label: "thing you can TASTE 👅" }
  ];

  const handleGroundSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentInput.trim()) return;

    setGroundInputs(prev => [...prev, currentInput.trim()]);
    setCurrentInput('');

    if (groundInputs.length + 1 >= steps[groundStep - 1].num) {
      if (groundStep < 5) {
        setGroundStep(s => s + 1);
        setGroundInputs([]);
      } else {
        setGroundStep(6); // completed state
      }
    }
  };

  const resetGrounding = () => {
    setGroundStep(1);
    setGroundInputs([]);
    setCurrentInput('');
  };

  // Canvas Fireflies (Mind Drift) State
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const canvasRequestRef = useRef<any>(null);

  useEffect(() => {
    if (activeTab === 'drift' && canvasRef.current) {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      let width = (canvas.width = canvas.offsetWidth);
      let height = (canvas.height = canvas.offsetHeight);

      const handleResize = () => {
        if (canvas) {
          width = canvas.width = canvas.offsetWidth;
          height = canvas.height = canvas.offsetHeight;
        }
      };
      window.addEventListener('resize', handleResize);

      const fireflies: any[] = [];
      const numFireflies = 30;

      for (let i = 0; i < numFireflies; i++) {
        fireflies.push({
          x: Math.random() * width,
          y: Math.random() * height,
          r: Math.random() * 2 + 1,
          alpha: Math.random() * 0.6 + 0.2,
          speedX: (Math.random() - 0.5) * 0.5,
          speedY: (Math.random() - 0.5) * 0.5,
          phase: Math.random() * Math.PI * 2,
        });
      }

      const animate = () => {
        ctx.clearRect(0, 0, width, height);

        // draw background gradient representing forest night
        const bgGrad = ctx.createLinearGradient(0, 0, 0, height);
        bgGrad.addColorStop(0, '#040614');
        bgGrad.addColorStop(1, '#0c0b25');
        ctx.fillStyle = bgGrad;
        ctx.fillRect(0, 0, width, height);

        // draw fireflies
        fireflies.forEach(f => {
          f.x += f.speedX;
          f.y += f.speedY;

          // boundaries
          if (f.x < 0) f.x = width;
          if (f.x > width) f.x = 0;
          if (f.y < 0) f.y = height;
          if (f.y > height) f.y = 0;

          // glow pulsing
          f.phase += 0.02;
          const currentAlpha = f.alpha + Math.sin(f.phase) * 0.15;

          ctx.beginPath();
          ctx.arc(f.x, f.y, f.r, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(34, 211, 238, ${Math.max(0.1, currentAlpha)})`;
          ctx.shadowBlur = f.r * 6;
          ctx.shadowColor = '#22d3ee';
          ctx.fill();
        });

        canvasRequestRef.current = requestAnimationFrame(animate);
      };

      animate();

      const handleCanvasClick = (e: MouseEvent) => {
        const rect = canvas.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const clickY = e.clientY - rect.top;

        // spawn 5 fireflies at click coordinates
        for (let idx = 0; idx < 5; idx++) {
          fireflies.push({
            x: clickX,
            y: clickY,
            r: Math.random() * 2 + 1,
            alpha: Math.random() * 0.8 + 0.3,
            speedX: (Math.random() - 0.5) * 1.5,
            speedY: (Math.random() - 0.5) * 1.5,
            phase: Math.random() * Math.PI * 2,
          });
        }

        // cap total fireflies
        if (fireflies.length > 80) {
          fireflies.splice(0, 5);
        }
      };

      canvas.addEventListener('click', handleCanvasClick);

      return () => {
        window.removeEventListener('resize', handleResize);
        if (canvas) canvas.removeEventListener('click', handleCanvasClick);
        cancelAnimationFrame(canvasRequestRef.current);
      };
    }
  }, [activeTab]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-6"
    >
      <h3 className="text-xs uppercase tracking-widest text-slate-500 font-semibold mb-4 flex items-center gap-1.5">
        <Wind size={14} className="text-cyan-400" />
        Calm Space
      </h3>

      <div className="flex border-b border-white/5 mb-6">
        <button
          onClick={() => setActiveTab('breathe')}
          className={`flex-1 pb-3 text-xs font-bold transition-all relative cursor-pointer ${
            activeTab === 'breathe' ? 'text-cyan-400' : 'text-slate-500 hover:text-slate-300'
          }`}
        >
          Box Breathe
          {activeTab === 'breathe' && (
            <motion.div layoutId="calmUnderline" className="absolute bottom-0 left-0 right-0 h-[2px] bg-cyan-400" />
          )}
        </button>
        <button
          onClick={() => setActiveTab('ground')}
          className={`flex-1 pb-3 text-xs font-bold transition-all relative cursor-pointer ${
            activeTab === 'drift' ? 'text-cyan-400' : 'text-slate-500 hover:text-slate-300'
          }`}
          style={{ display: 'none' }} /* Hide unused spacer tab or map correctly */
        />
        <button
          onClick={() => setActiveTab('ground')}
          className={`flex-1 pb-3 text-xs font-bold transition-all relative cursor-pointer ${
            activeTab === 'ground' ? 'text-cyan-400' : 'text-slate-500 hover:text-slate-300'
          }`}
        >
          5-4-3-2-1 Grounding
          {activeTab === 'ground' && (
            <motion.div layoutId="calmUnderline" className="absolute bottom-0 left-0 right-0 h-[2px] bg-cyan-400" />
          )}
        </button>
        <button
          onClick={() => setActiveTab('drift')}
          className={`flex-1 pb-3 text-xs font-bold transition-all relative cursor-pointer ${
            activeTab === 'drift' ? 'text-cyan-400' : 'text-slate-500 hover:text-slate-300'
          }`}
        >
          Mind Drift (Fireflies)
          {activeTab === 'drift' && (
            <motion.div layoutId="calmUnderline" className="absolute bottom-0 left-0 right-0 h-[2px] bg-cyan-400" />
          )}
        </button>
      </div>

      <div className="min-h-[220px] flex items-center justify-center">
        {activeTab === 'breathe' && (
          <div className="flex flex-col items-center justify-center text-center">
            {/* Breathe circle animation */}
            <motion.div
              animate={{
                scale: breathState === 'Inhale' ? 1.5 : (breathState === 'Exhale' ? 1.0 : (breathState === 'Hold' ? 1.5 : 1.0)),
              }}
              transition={{ duration: 4, ease: 'easeInOut' }}
              className="w-24 h-24 rounded-full border border-cyan-400/30 flex flex-col items-center justify-center bg-cyan-400/5 mb-4 shadow-[0_0_20px_rgba(34,211,238,0.1)]"
            >
              <div className="text-sm font-bold text-white">{breathState}</div>
              <div className="text-[10px] text-cyan-400 mt-0.5">{breathSeconds}s</div>
            </motion.div>
            <p className="text-[10px] text-slate-500 max-w-[200px] leading-relaxed">
              Align your breathing to the pulsing circle. Inhale (4s), Hold (4s), Exhale (4s), Hold (4s).
            </p>
          </div>
        )}

        {activeTab === 'ground' && (
          <div className="w-full flex flex-col items-center justify-center max-w-sm">
            {groundStep <= 5 ? (
              <form onSubmit={handleGroundSubmit} className="w-full space-y-4">
                <div className="text-center mb-2">
                  <div className="text-[10px] uppercase font-bold tracking-wider text-slate-500">Step {groundStep} of 5</div>
                  <h4 className="text-sm font-bold text-white mt-1">
                    Describe {steps[groundStep - 1].num} {steps[groundStep - 1].label}
                  </h4>
                </div>

                <div className="flex flex-wrap gap-1.5 justify-center mb-2">
                  {groundInputs.map((val, idx) => (
                    <span key={idx} className="px-2 py-1 rounded-lg bg-emerald-500/10 text-emerald-300 border border-emerald-500/10 text-[10px] capitalize">
                      ✓ {val}
                    </span>
                  ))}
                  {Array.from({ length: steps[groundStep - 1].num - groundInputs.length }).map((_, idx) => (
                    <span key={idx} className="px-2.5 py-1 rounded-lg bg-white/2 border border-white/5 text-[10px] text-slate-600">
                      pending...
                    </span>
                  ))}
                </div>

                <div className="flex gap-2">
                  <input
                    type="text"
                    value={currentInput}
                    onChange={(e) => setCurrentInput(e.target.value)}
                    placeholder="Describe item..."
                    className="flex-1 px-3 py-2 text-xs glass-input focus:border-cyan-400/40"
                  />
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-xl text-xs font-semibold bg-cyan-400 text-bg-primary hover:bg-cyan-300 transition-colors cursor-pointer"
                  >
                    Add
                  </button>
                </div>
              </form>
            ) : (
              <div className="text-center py-6">
                <h4 className="text-base font-bold text-emerald-400 mb-1 flex items-center justify-center gap-1">
                  ✓ Grounding Complete
                </h4>
                <p className="text-xs text-slate-400 max-w-[220px] mx-auto leading-relaxed mb-4">
                  Excellent work. Your focus has successfully shifted back to your body and surroundings.
                </p>
                <button
                  onClick={resetGrounding}
                  className="px-4 py-2 rounded-xl text-xs font-semibold border border-white/10 text-slate-300 hover:bg-white/5 cursor-pointer"
                >
                  Start Again
                </button>
              </div>
            )}
          </div>
        )}

        {activeTab === 'drift' && (
          <div className="relative w-full h-[220px] rounded-2xl border border-white/5 overflow-hidden">
            <canvas ref={canvasRef} className="absolute inset-0 w-full h-full cursor-pointer" />
            <div className="absolute bottom-2 left-1/2 -translate-x-1/2 bg-slate-950/70 backdrop-blur-md px-3 py-1 rounded-full text-[9px] text-slate-500 font-semibold pointer-events-none select-none">
              Click anywhere on the dark canvas to spawn fireflies ✨
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}

// 5. Something Is Shifting Component (Longitudinal Shifts)
function SomethingIsShifting({ shift }: { shift: any }) {
  if (!shift) return null;

  const isPositive = shift.direction === 'rising';
  const getIcon = () => {
    if (shift.direction === 'rising') return <MoveUp size={16} className="text-emerald-400" />;
    if (shift.direction === 'falling') return <MoveDown size={16} className="text-rose-400" />;
    return <HelpCircle size={16} className="text-slate-500" />;
  };

  const getBorderColor = () => {
    if (shift.direction === 'rising') return 'border-emerald-500/15 bg-emerald-500/2';
    if (shift.direction === 'falling') return 'border-rose-500/15 bg-rose-500/2';
    return 'border-white/5 bg-white/1';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      className={`glass-card p-6 border ${getBorderColor()}`}
    >
      <h3 className="text-xs uppercase tracking-widest text-slate-500 font-semibold mb-4 flex items-center gap-1.5">
        {getIcon()}
        Something Is Shifting
      </h3>

      <div className="flex items-center gap-6 mb-4">
        <div>
          <div className="text-[10px] text-slate-500 uppercase font-semibold mb-0.5">Last Week</div>
          <div className="text-2xl font-bold text-white">{shift.recent_average}</div>
        </div>
        <div className="text-slate-600 text-lg">&rarr;</div>
        <div>
          <div className="text-[10px] text-slate-500 uppercase font-semibold mb-0.5">Prior Week</div>
          <div className="text-2xl font-bold text-slate-400">{shift.prior_average}</div>
        </div>
      </div>

      <p className="text-xs text-slate-300 leading-relaxed">
        {shift.observation}
      </p>
    </motion.div>
  );
}

// ============================================
// MAIN PAGE EXPORT
// ============================================

export default function DashboardPage() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [isLoadingPage, setIsLoadingPage] = useState(true);
  const [isRecalculating, setIsRecalculating] = useState(false);

  const {
    emotionalProfile,
    growthSummary,
    isLoading,
    refresh,
  } = useMoodData();

  useEffect(() => {
    setMounted(true);
    const token = getToken();
    if (!token) {
      router.push('/login');
      return;
    }
    setTimeout(() => setIsLoadingPage(false), 800);
  }, [router]);

  const handleRecalculate = async () => {
    const token = getToken();
    if (!token) return;

    setIsRecalculating(true);
    try {
      await recalculateProfile(token);
      await refresh();
    } catch (err) {
      console.error('[MyGrowth] Recalculation failed:', err);
    } finally {
      setIsRecalculating(false);
    }
  };

  const user = mounted ? getStoredUser() : null;

  if (!mounted || isLoadingPage || isLoading) {
    return (
      <AnimatePresence>
        <FullPageTransition message="Reading your inner coordinates..." />
      </AnimatePresence>
    );
  }

  // Retrieve completion metadata
  const completion = growthSummary?.knowing_me_completion || {
    is_complete: false,
    answered_count: 0,
    total_questions: 27,
    analysis_status: 'not_ready'
  };

  return (
    <div className="min-h-screen">
      <Navbar />

      {/* Account Deletion Modal (Removed) */}

      <main className="max-w-6xl mx-auto px-4 sm:px-6 pt-24 pb-16">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="flex items-center justify-between mb-8"
        >
          <div>
            <h1
              className="text-2xl sm:text-3xl font-bold mb-1"
              style={{
                color: 'var(--text-primary)',
                fontFamily: 'var(--font-space-grotesk), sans-serif',
              }}
            >
              Your Inner Weather 🌦️
            </h1>
            <p className="text-xs text-slate-500">
              Personalized growth tracker, behavioral insights, and guided calm activities.
            </p>
          </div>

          <motion.button
            whileHover={{ scale: 1.05, rotate: 90 }}
            whileTap={{ scale: 0.95 }}
            onClick={refresh}
            disabled={isLoading}
            className="p-3 rounded-xl glass-card cursor-pointer transition-all duration-300 hover:border-[rgba(56,189,248,0.3)]"
            title="Refresh data"
          >
            <RefreshCw
              size={16}
              className={isLoading ? 'animate-spin' : ''}
              style={{ color: 'var(--accent-cyan)' }}
            />
          </motion.button>
        </motion.div>

        {/* COMPLETED STATE VIEW */}
        {completion.is_complete ? (
          <>
            {completion.analysis_status === 'ready' && growthSummary ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* 1. Inner Weather */}
                <InnerWeather weather={growthSummary.inner_weather} />

                {/* 2. Esona Noticed */}
                <EsonaNoticed notices={growthSummary.esona_noticed} />

                {/* 3. Constellation (Full Width) */}
                <div className="lg:col-span-2">
                  <EmotionalConstellation constellation={growthSummary.emotional_constellation} />
                </div>

                {/* 4. Calm Space */}
                <CalmSpace exercises={growthSummary.calm_space} />

                {/* 5. Something Is Shifting */}
                <SomethingIsShifting shift={growthSummary.something_is_shifting} />
              </div>
            ) : (
              /* PENDING / FAILED GENERATION LOADING CONTAINER */
              <motion.div
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                className="p-12 rounded-2xl text-center glass-card border border-white/5 max-w-lg mx-auto"
              >
                <div className="mb-6">
                  {completion.analysis_status === 'failed' ? (
                    <div className="w-16 h-16 rounded-2xl bg-rose-500/10 border border-rose-500/15 mx-auto flex items-center justify-center mb-4 text-rose-400 text-2xl">
                      ⚠
                    </div>
                  ) : (
                    <div className="w-16 h-16 rounded-2xl bg-cyan-500/5 border border-cyan-500/15 mx-auto flex items-center justify-center mb-4">
                      <Loader2 className="animate-spin text-cyan-400" size={28} />
                    </div>
                  )}
                  <h3
                    className="text-lg font-bold text-white mb-2"
                    style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}
                  >
                    {completion.analysis_status === 'failed'
                      ? 'AI Profile Generation Interrupted'
                      : 'Esona is mapping your coordinates...'
                    }
                  </h3>
                  <p className="text-xs text-slate-400 leading-relaxed mb-6">
                    {completion.analysis_status === 'failed'
                      ? 'We had trouble parsing your questionnaire responses. Click the button below to retry profile initialization.'
                      : 'All 27 answers collected! We are currently running MentalBERT and our personalization pipeline to generate your emotional space.'
                    }
                  </p>

                  <button
                    onClick={handleRecalculate}
                    disabled={isRecalculating}
                    className="inline-flex items-center gap-1.5 px-6 py-3 rounded-xl text-xs font-bold bg-cyan-400 text-bg-primary hover:bg-cyan-300 disabled:opacity-50 cursor-pointer shadow-[0_0_15px_rgba(34,211,238,0.2)]"
                  >
                    {isRecalculating ? (
                      <>
                        <Loader2 className="animate-spin" size={14} />
                        Calculating...
                      </>
                    ) : (
                      <>
                        <RefreshCw size={14} />
                        Generate Profile
                      </>
                    )}
                  </button>
                </div>
              </motion.div>
            )}
          </>
        ) : (
          /* UNCOMPLETED / ONBOARDING CTA CARD */
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-12 rounded-2xl text-center glass-card border border-white/5 max-w-lg mx-auto"
          >
            <div className="w-16 h-16 rounded-2xl bg-pink-500/5 border border-pink-500/15 mx-auto flex items-center justify-center mb-4">
              <Heart className="text-pink-400" size={28} />
            </div>
            <h3
              className="text-xl font-bold text-white mb-2"
              style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}
            >
              Complete Knowing Me Questionnaire
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed mb-6">
              You have answered {completion.answered_count || 0} of {completion.total_questions || 27} questions.
              Complete all questions to unlock your custom Inner Weather, Emotional Constellation, and AI personality calibration.
            </p>

            <Link
              href="/knowing-me"
              className="inline-flex items-center gap-1.5 px-6 py-3 rounded-xl text-xs font-bold transition-all duration-300"
              style={{
                background: 'var(--gradient-primary)',
                color: 'var(--bg-primary)',
                boxShadow: '0 0 15px rgba(56, 189, 248, 0.25)',
              }}
            >
              <Heart size={14} />
              Continue Questionnaire &rarr;
            </Link>
          </motion.div>
        )}

      </main>
    </div>
  );
}
