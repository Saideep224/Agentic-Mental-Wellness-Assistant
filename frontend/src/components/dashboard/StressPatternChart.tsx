'use client';

import { motion } from 'framer-motion';
import {
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
} from 'recharts';
import { StressPattern } from '@/types';

interface StressPatternChartProps {
  data: StressPattern[];
  title?: string;
}

export default function StressPatternChart({ data, title = "Stress Patterns" }: StressPatternChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="glass-card p-8 flex flex-col items-center justify-center min-h-[320px] text-center border border-white/5 bg-white/2 hover:border-white/10 transition-all duration-300">
        <div className="w-12 h-12 rounded-full flex items-center justify-center mb-4 text-2xl" style={{ background: 'rgba(167, 139, 250, 0.1)', color: 'var(--accent-purple)' }}>
          📊
        </div>
        <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-space-grotesk), sans-serif' }}>
          {title}
        </h3>
        <p className="text-sm max-w-sm" style={{ color: 'var(--text-muted)' }}>
          No emotional data yet. Chat with Esona to generate your emotional dimension radar profile.
        </p>
      </div>
    );
  }
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.1 }}
      className="glass-card p-6"
    >
      <h3
        className="text-lg font-semibold mb-1"
        style={{
          color: 'var(--text-primary)',
          fontFamily: 'var(--font-space-grotesk), sans-serif',
        }}
      >
        {title}
      </h3>
      <p className="text-xs mb-6" style={{ color: 'var(--text-muted)' }}>
        Areas that affect your stress levels
      </p>

      <div className="w-full h-64">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="75%" data={data}>
            <PolarGrid stroke="rgba(255, 255, 255, 0.06)" />
            <PolarAngleAxis
              dataKey="category"
              tick={{ fill: '#94a3b8', fontSize: 11 }}
            />
            <Radar
              name="Stress"
              dataKey="value"
              stroke="#a78bfa"
              fill="#a78bfa"
              fillOpacity={0.15}
              strokeWidth={2}
              dot={{
                r: 4,
                fill: '#a78bfa',
                stroke: 'rgba(167, 139, 250, 0.3)',
                strokeWidth: 3,
              }}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}
