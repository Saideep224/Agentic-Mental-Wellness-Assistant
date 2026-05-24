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
}

export default function StressPatternChart({ data }: StressPatternChartProps) {
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
          fontFamily: 'var(--font-outfit), sans-serif',
        }}
      >
        Stress Patterns
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
