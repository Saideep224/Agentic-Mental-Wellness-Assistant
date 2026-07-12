'use client';

import { useState, useEffect } from 'react';
import { motion, MotionValue, useTransform, useReducedMotion } from 'framer-motion';
import { GRAPH_NODES, GRAPH_EDGES } from './demoData';

interface Props {
  progress: MotionValue<number>;
  isActive: boolean;
}

export default function KnowledgeGraphScene({ progress, isActive }: Props) {
  const shouldReduceMotion = useReducedMotion();
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const handleResize = () => setIsMobile(window.innerWidth < 640);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Scene visible range: [0.625, 0.75]
  const opacity = useTransform(progress, [0, 0.625, 0.635, 0.74, 0.75, 1], [0, 0, 1, 1, 0, 0], { clamp: true });
  const containerY = useTransform(progress, [0.625, 0.75], [20, shouldReduceMotion ? 20 : -20], { clamp: true });

  // Phase 1: YOU node fades in (0.625 to 0.632)
  const youOpacity = useTransform(progress, [0.625, 0.632], [0, 1], { clamp: true });

  // Phase 2: Primary nodes and connection lines draw sequentially (0.630 to 0.700)
  const draw0 = useTransform(progress, [0.630, 0.638], [0, 1], { clamp: true }); // college
  const draw1 = useTransform(progress, [0.640, 0.648], [0, 1], { clamp: true }); // japan
  const draw2 = useTransform(progress, [0.650, 0.658], [0, 1], { clamp: true }); // exams
  const draw3 = useTransform(progress, [0.660, 0.668], [0, 1], { clamp: true }); // relationship
  const draw4 = useTransform(progress, [0.670, 0.678], [0, 1], { clamp: true }); // dreams
  const draw5 = useTransform(progress, [0.680, 0.688], [0, 1], { clamp: true }); // night
  const draw6 = useTransform(progress, [0.690, 0.698], [0, 1], { clamp: true }); // friends

  // Phase 3: Secondary emotional nodes & lines draw sequentially (0.700 to 0.730)
  const drawSec0 = useTransform(progress, [0.700, 0.706], [0, 1], { clamp: true }); // anxiety
  const drawSec1 = useTransform(progress, [0.706, 0.712], [0, 1], { clamp: true }); // dream_dest
  const drawSec2 = useTransform(progress, [0.712, 0.718], [0, 1], { clamp: true }); // sadness
  const drawSec3 = useTransform(progress, [0.718, 0.724], [0, 1], { clamp: true }); // overthinking
  const drawSec4 = useTransform(progress, [0.724, 0.730], [0, 1], { clamp: true }); // comfort

  // Phase 4: Bottom explanation text reveals (0.710 to 0.750)
  // Fades in: 0.71 -> 0.73 | Holds: 0.73 -> 0.745 | Exits: 0.745 -> 0.75
  const textOpacity = useTransform(progress, [0, 0.71, 0.73, 0.745, 0.75, 1], [0, 0, 1, 1, 0, 0], { clamp: true });
  const textY = useTransform(progress, [0.71, 0.75], [15, shouldReduceMotion ? 15 : 0], { clamp: true });

  const getPrimaryEdgeDraw = (toNodeId: string) => {
    if (toNodeId === 'college') return draw0;
    if (toNodeId === 'japan') return draw1;
    if (toNodeId === 'exams') return draw2;
    if (toNodeId === 'relationship') return draw3;
    if (toNodeId === 'dreams') return draw4;
    if (toNodeId === 'night') return draw5;
    return draw6;
  };

  const getSecondaryEdgeDraw = (toNodeId: string) => {
    if (toNodeId === 'anxiety') return drawSec0;
    if (toNodeId === 'dream_dest') return drawSec1;
    if (toNodeId === 'sadness') return drawSec2;
    if (toNodeId === 'overthinking') return drawSec3;
    return drawSec4;
  };

  const getNodeOpacity = (nodeId: string) => {
    if (nodeId === 'you') return youOpacity;
    if (nodeId === 'college') return draw0;
    if (nodeId === 'japan') return draw1;
    if (nodeId === 'exams') return draw2;
    if (nodeId === 'relationship') return draw3;
    if (nodeId === 'dreams') return draw4;
    if (nodeId === 'night') return draw5;
    if (nodeId === 'friends') return draw6;
    if (nodeId === 'anxiety') return drawSec0;
    if (nodeId === 'dream_dest') return drawSec1;
    if (nodeId === 'sadness') return drawSec2;
    if (nodeId === 'overthinking') return drawSec3;
    return drawSec4;
  };

  // Calculate coordinates in SVG space (box: 800x440)
  const center = { x: 400, y: 200 };
  
  const getCoords = (nodeId: string) => {
    const node = GRAPH_NODES.find((n) => n.id === nodeId);
    if (!node) return center;
    if (nodeId === 'you') return center;

    // Mobile: reduce the expansion radius to fit screens
    const scaleFactorX = isMobile ? 3.5 : 7.2;
    const scaleFactorY = isMobile ? 2.5 : 4.0;
    
    // On mobile, omit secondary nodes to avoid clutter
    const isSecondary = !['college', 'japan', 'exams', 'relationship', 'dreams', 'night', 'friends'].includes(nodeId);
    if (isMobile && isSecondary) {
      // Hide secondary nodes by shifting them off-screen or keeping them near parent
      if (nodeId === 'anxiety') return { x: center.x - 70, y: center.y + 30 };
      if (nodeId === 'comfort') return { x: center.x, y: center.y - 80 };
      if (nodeId === 'dream_dest') return { x: center.x + 80, y: center.y - 50 };
      if (nodeId === 'sadness') return { x: center.x + 80, y: center.y + 40 };
      return { x: center.x - 50, y: center.y + 80 }; // overthinking
    }

    return {
      x: center.x + (node.x - 50) * scaleFactorX,
      y: center.y + (node.y - 50) * scaleFactorY,
    };
  };

  return (
    <motion.div
      className="absolute inset-0 flex flex-col items-center justify-center px-6 select-none z-10"
      style={{
        opacity,
        y: containerY,
        pointerEvents: isActive ? 'auto' : 'none',
      }}
    >
      {/* Knowledge Graph Wrapper */}
      <div className="w-full max-w-3xl h-[280px] sm:h-[350px] relative mb-6">
        
        {/* SVG Drawing Canvas */}
        <svg viewBox="0 0 800 400" className="w-full h-full absolute inset-0 z-0 overflow-visible">
          {/* 1. Edges (Drawing Lines) */}
          {GRAPH_EDGES.map((edge, idx) => {
            const isSecondary = !['college', 'japan', 'exams', 'relationship', 'dreams', 'night', 'friends'].includes(edge.to);
            if (isMobile && isSecondary) return null; // skip secondary on mobile
            
            const start = getCoords(edge.from);
            const end = getCoords(edge.to);
            
            const edgeDraw = isSecondary ? getSecondaryEdgeDraw(edge.to) : getPrimaryEdgeDraw(edge.to);
            
            return (
              <motion.line
                key={`edge-${idx}`}
                x1={start.x}
                y1={start.y}
                x2={end.x}
                y2={end.y}
                stroke={edge.color || 'rgba(148, 163, 184, 0.15)'}
                strokeWidth={isSecondary ? 1.5 : 1}
                strokeDasharray={isSecondary ? "4 4" : "0"}
                style={{
                  pathLength: edgeDraw,
                  opacity: edgeDraw,
                }}
              />
            );
          })}

          {/* 2. Secondary Edges Label indicators (Desktop Only) */}
          {!isMobile && GRAPH_EDGES.map((edge, idx) => {
            const isSecondary = !['college', 'japan', 'exams', 'relationship', 'dreams', 'night', 'friends'].includes(edge.to);
            if (!isSecondary) return null;
            
            const start = getCoords(edge.from);
            const end = getCoords(edge.to);
            const midX = (start.x + end.x) / 2;
            const midY = (start.y + end.y) / 2;
            
            const labelOpacity = getSecondaryEdgeDraw(edge.to);

            return (
              <motion.g
                key={`label-${idx}`}
                style={{ opacity: labelOpacity }}
              >
                <rect x={midX - 25} y={midY - 8} width={50} height={14} rx={4} fill="#040614" stroke="rgba(255,255,255,0.05)" strokeWidth={0.5} />
                <text x={midX} y={midY + 2} textAnchor="middle" fill="#8B9BB8" fontSize="8" letterSpacing="0.05em">
                  {edge.label}
                </text>
              </motion.g>
            );
          })}

          {/* 3. Render Nodes */}
          {GRAPH_NODES.map((node) => {
            const isSecondary = !['you', 'college', 'japan', 'exams', 'relationship', 'dreams', 'night', 'friends'].includes(node.id);
            if (isMobile && isSecondary) return null; // skip secondary on mobile

            const coords = getCoords(node.id);
            const nodeOpacity = getNodeOpacity(node.id);

            return (
              <motion.g
                key={node.id}
                style={{ opacity: nodeOpacity }}
                whileHover={{ scale: 1.1 }}
              >
                {/* Node Ring/Glow */}
                <circle
                  cx={coords.x}
                  cy={coords.y}
                  r={node.id === 'you' ? 12 : 7}
                  fill="transparent"
                  stroke={node.color}
                  strokeWidth={1.5}
                  className="opacity-40 animate-pulse"
                />
                
                {/* Core Circle */}
                <circle
                  cx={coords.x}
                  cy={coords.y}
                  r={node.id === 'you' ? 6 : 4}
                  fill={node.color}
                />

                {/* Node Text Label */}
                <text
                  x={coords.x}
                  y={coords.y + (node.id === 'you' ? 24 : 16)}
                  textAnchor="middle"
                  fill={node.id === 'you' ? '#FFF' : '#A8BDD6'}
                  fontSize={node.id === 'you' ? '11' : '9'}
                  fontWeight={node.id === 'you' ? 'bold' : 'normal'}
                  letterSpacing="0.08em"
                  className="pointer-events-none select-none font-medium"
                  style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}
                >
                  {node.label}
                </text>
              </motion.g>
            );
          })}
        </svg>
      </div>

      {/* 4. Narrative Footer */}
      <motion.div
        className="text-center max-w-xl mx-auto flex flex-col gap-3"
        style={{
          opacity: textOpacity,
          y: textY,
        }}
      >
        <h2 className="text-2xl sm:text-3xl font-light text-slate-100 leading-snug">
          Esona doesn't just remember messages. <br />
          <span className="font-semibold text-white">She understands how your world connects.</span>
        </h2>
        <p className="text-[10px] sm:text-xs uppercase tracking-[0.2em] text-[#8BA0B8]">
          Knowledge Graph powered contextual memory.
        </p>
      </motion.div>
    </motion.div>
  );
}
