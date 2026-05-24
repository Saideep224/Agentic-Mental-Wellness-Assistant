'use client';

import { motion } from 'framer-motion';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import { MoodDataPoint } from '@/types';

interface MoodTrendChartProps {
  data: MoodDataPoint[];
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number; payload: MoodDataPoint }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) return null;

  return (
    <div
      className="glass-card px-4 py-3 text-sm"
      style={{
        boxShadow: 'var(--glow-cyan)',
      }}
    >
      <p className="font-medium mb-1" style={{ color: 'var(--text-primary)' }}>
        {label}
      </p>
      <p style={{ color: 'var(--accent-cyan)' }}>
        Mood: <span className="font-semibold">{payload[0].value}/10</span>
      </p>
      {payload[0].payload.emotion && (
        <p style={{ color: 'var(--text-muted)' }}>
          Feeling: {payload[0].payload.emotion}
        </p>
      )}
    </div>
  );
}

export default function MoodTrendChart({ data }: MoodTrendChartProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="glass-card p-6"
    >
      <h3
        className="text-lg font-semibold mb-1"
        style={{
          color: 'var(--text-primary)',
          fontFamily: 'var(--font-outfit), sans-serif',
        }}
      >
        Mood Trends
      </h3>
      <p className="text-xs mb-6" style={{ color: 'var(--text-muted)' }}>
        Your emotional journey over the last 30 days
      </p>

      <div className="w-full h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
            <defs>
              <linearGradient id="moodGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(255,255,255,0.03)"
              vertical={false}
            />
            <XAxis
              dataKey="date"
              tick={{ fill: '#64748b', fontSize: 11 }}
              axisLine={{ stroke: 'rgba(255,255,255,0.05)' }}
              tickLine={false}
            />
            <YAxis
              domain={[0, 10]}
              tick={{ fill: '#64748b', fontSize: 11 }}
              axisLine={{ stroke: 'rgba(255,255,255,0.05)' }}
              tickLine={false}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="score"
              stroke="#22d3ee"
              strokeWidth={2}
              fill="url(#moodGradient)"
              dot={{ r: 3, fill: '#22d3ee', strokeWidth: 0 }}
              activeDot={{
                r: 5,
                fill: '#22d3ee',
                stroke: 'rgba(34, 211, 238, 0.3)',
                strokeWidth: 4,
              }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}
