'use client';

import { motion, AnimatePresence } from 'framer-motion';
import type { GrowthInsightItem } from '@/api/dashboard';

interface GrowthInsightsCardProps {
  insights: GrowthInsightItem[];
  totalLogs?: number;
  totalMemories?: number;
}

function TrendBadge({ trend }: { trend: string }) {
  const config = {
    rising: { label: '📈 Rising', bg: 'rgba(52, 211, 153, 0.08)', border: 'rgba(52, 211, 153, 0.2)', color: '#34d399' },
    falling: { label: '📉 Falling', bg: 'rgba(248, 113, 113, 0.08)', border: 'rgba(248, 113, 113, 0.2)', color: '#f87171' },
    stable: { label: '➡️ Stable', bg: 'rgba(148, 163, 184, 0.08)', border: 'rgba(148, 163, 184, 0.2)', color: '#94a3b8' },
  }[trend] ?? { label: '➡️ Stable', bg: 'rgba(148, 163, 184, 0.08)', border: 'rgba(148, 163, 184, 0.2)', color: '#94a3b8' };

  return (
    <span
      className="px-2 py-0.5 rounded-full text-[10px] font-semibold whitespace-nowrap"
      style={{ background: config.bg, border: `1px solid ${config.border}`, color: config.color }}
    >
      {config.label}
    </span>
  );
}

export default function GrowthInsightsCard({ insights, totalLogs = 0, totalMemories = 0 }: GrowthInsightsCardProps) {
  if (!insights || insights.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.4 }}
        className="glass-card p-6 lg:col-span-2"
      >
        <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-space-grotesk), sans-serif' }}>
          📊 Personal Growth Insights
        </h3>
        <p className="text-xs mb-6" style={{ color: 'var(--text-muted)' }}>
          Patterns derived from your conversations, emotions, and memories
        </p>
        <div className="text-center py-8">
          <p className="text-sm text-slate-500 italic">
            Keep chatting with Esona to unlock personalized growth observations 🌱
          </p>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.4 }}
      className="glass-card p-6 lg:col-span-2"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-space-grotesk), sans-serif' }}>
            📊 Personal Growth Insights
          </h3>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Patterns derived from your conversations, emotions, and memories
          </p>
        </div>

        {/* Stats chips */}
        <div className="flex gap-2 shrink-0">
          {totalLogs > 0 && (
            <span
              className="px-2.5 py-1 rounded-lg text-[10px] font-semibold"
              style={{
                background: 'rgba(56, 189, 248, 0.08)',
                border: '1px solid rgba(56, 189, 248, 0.15)',
                color: 'var(--accent-cyan)',
              }}
            >
              {totalLogs} mood logs
            </span>
          )}
          {totalMemories > 0 && (
            <span
              className="px-2.5 py-1 rounded-lg text-[10px] font-semibold"
              style={{
                background: 'rgba(168, 85, 247, 0.08)',
                border: '1px solid rgba(168, 85, 247, 0.15)',
                color: '#a855f7',
              }}
            >
              {totalMemories} memories
            </span>
          )}
        </div>
      </div>

      {/* Insights grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <AnimatePresence>
          {insights.map((item, idx) => (
            <motion.div
              key={`${item.category}-${idx}`}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.35, delay: idx * 0.06 }}
              className="group flex items-start gap-3 p-4 rounded-xl transition-all duration-300"
              style={{
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--glass-border)',
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLDivElement).style.background = 'rgba(56, 189, 248, 0.04)';
                (e.currentTarget as HTMLDivElement).style.borderColor = 'rgba(56, 189, 248, 0.18)';
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLDivElement).style.background = 'rgba(255, 255, 255, 0.02)';
                (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--glass-border)';
              }}
            >
              {/* Icon */}
              <div
                className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 text-lg select-none"
                style={{
                  background: 'rgba(56, 189, 248, 0.08)',
                  border: '1px solid rgba(56, 189, 248, 0.12)',
                }}
              >
                {item.icon}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-sky-400">
                    {item.category}
                  </span>
                  <TrendBadge trend={item.trend} />
                </div>

                <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                  {item.observation}
                </p>

                <p className="text-[10px] text-slate-600 mt-1.5">{item.timeframe}</p>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Footer note */}
      <p className="text-[10px] text-slate-600 mt-5 text-center">
        ✨ Esona generates these observations automatically from your emotional data — no manual input needed.
      </p>
    </motion.div>
  );
}
