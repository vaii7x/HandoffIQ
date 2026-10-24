import React from 'react';
import { StatItem } from '../../types/handoff';
import { AgentPalette } from '../../types/agent';

interface HandoffStatisticsProps {
  stats: StatItem[];
  palette: AgentPalette;
}

export const HandoffStatistics: React.FC<HandoffStatisticsProps> = ({
  stats,
  palette,
}) => {
  return (
    <div className="w-full max-w-3xl mx-auto my-4 sm:my-6 px-3">
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 sm:gap-0 py-3 sm:py-4 border-y border-white/10 select-none">
        {stats.map((stat, idx) => (
          <div
            key={stat.id}
            className={`flex flex-col items-center justify-center text-center px-2 ${
              idx < stats.length - 1 ? 'sm:border-r sm:border-white/10' : ''
            } ${idx === stats.length - 1 && stats.length % 2 !== 0 ? 'col-span-2 sm:col-span-1' : ''}`}
          >
            {/* Number value */}
            <span
              className="text-lg sm:text-2xl font-mono font-medium tracking-tight mb-1"
              style={{
                color: stat.highlight ? palette.primary : '#FFFFFF',
                fontVariantNumeric: 'tabular-nums',
              }}
            >
              {stat.value}
            </span>

            {/* Label */}
            <span className="text-[11px] sm:text-xs text-white/50 font-normal tracking-wide leading-tight">
              {stat.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
