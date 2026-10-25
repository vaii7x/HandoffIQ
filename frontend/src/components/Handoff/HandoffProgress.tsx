import React from 'react';
import { AgentPalette } from '../../types/agent';

interface HandoffProgressProps {
  stageFraction: string; // e.g. "2/5" or "4/5"
  progressPercent: number; // e.g. 40 or 80
  statusText: string;
  palette: AgentPalette;
}

export const HandoffProgress: React.FC<HandoffProgressProps> = ({
  stageFraction,
  progressPercent,
  statusText,
  palette,
}) => {
  return (
    <div className="w-full max-w-[340px] sm:max-w-[420px] mx-auto mt-5 px-3 flex flex-col items-center">
      {/* Progress Track & Fraction */}
      <div className="w-full flex items-center gap-3">
        <div className="flex-1 h-1.5 bg-[#DFE1F2] rounded-full overflow-hidden p-[1px]">
          <div
            className="h-full rounded-full transition-all duration-700 ease-out"
            style={{
              width: `${progressPercent}%`,
              backgroundColor: palette.primary,
            }}
          />
        </div>
        <span
          className="text-xs font-mono font-medium tracking-wider select-none shrink-0"
          style={{
            color: palette.muted,
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {stageFraction}
        </span>
      </div>

      {/* Dynamic Status Text */}
      <div className="min-h-[22px] mt-2 flex items-center justify-center">
        <span
          className="text-[11px] sm:text-xs font-normal tracking-wide text-[#737895]"
        >
          {statusText}
        </span>
      </div>
    </div>
  );
};
