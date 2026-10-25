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
    <div className="w-full max-w-4xl mx-auto my-4 sm:my-5 px-3">
      <div className="bg-white border border-[#DFE1F2] rounded-2xl shadow-[0_2px_10px_rgba(23,26,53,0.02)] flex flex-wrap sm:flex-nowrap items-stretch divide-y sm:divide-y-0 sm:divide-x divide-[#DFE1F2] py-3.5 select-none">
        {stats.map((stat) => (
          <div
            key={stat.id}
            className="flex-1 min-w-[110px] flex flex-col items-center justify-center text-center px-2.5 py-2 sm:py-0"
          >
            {/* Number value */}
            <span
              className="text-lg sm:text-2xl font-mono font-semibold tracking-tight mb-1"
              style={{
                color: stat.highlight ? palette.primary : '#171A35',
                fontVariantNumeric: 'tabular-nums',
              }}
            >
              {stat.value}
            </span>

            {/* Label */}
            <span className="text-[11px] sm:text-xs text-[#737895] font-normal tracking-wide leading-tight text-center">
              {stat.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
