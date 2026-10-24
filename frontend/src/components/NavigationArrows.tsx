import React from 'react';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { AgentPalette } from '../types/agent';

interface NavigationArrowsProps {
  palette: AgentPalette;
  hasPrev: boolean;
  hasNext: boolean;
  onPrev: () => void;
  onNext: () => void;
  prevName?: string;
  nextName?: string;
}

export const NavigationArrows: React.FC<NavigationArrowsProps> = ({
  palette,
  hasPrev,
  hasNext,
  onPrev,
  onNext,
  prevName,
  nextName,
}) => {
  return (
    <>
      {/* Left Arrow Button */}
      {hasPrev && (
        <button
          type="button"
          onClick={onPrev}
          aria-label={`Previous agent: ${prevName || ''}`}
          className="fixed left-3 sm:left-6 top-1/2 -translate-y-1/2 z-30 p-2 sm:p-3 rounded-full text-white/50 hover:text-white transition-all duration-300 hover:scale-110 active:scale-95 focus:outline-none focus:ring-1 focus:ring-white/40"
          style={{
            background: 'rgba(255, 255, 255, 0.04)',
            backdropFilter: 'blur(8px)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
          }}
          title={prevName ? `Go to ${prevName}` : 'Previous'}
        >
          <ArrowLeft className="w-4 h-4 sm:w-5 sm:h-5 transition-transform group-hover:-translate-x-0.5" />
        </button>
      )}

      {/* Right Arrow Button */}
      {hasNext && (
        <button
          type="button"
          onClick={onNext}
          aria-label={`Next agent: ${nextName || ''}`}
          className="fixed right-3 sm:right-6 top-1/2 -translate-y-1/2 z-30 p-2 sm:p-3 rounded-full text-white/50 hover:text-white transition-all duration-300 hover:scale-110 active:scale-95 focus:outline-none focus:ring-1 focus:ring-white/40"
          style={{
            background: 'rgba(255, 255, 255, 0.04)',
            backdropFilter: 'blur(8px)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
          }}
          title={nextName ? `Go to ${nextName}` : 'Next'}
        >
          <ArrowRight
            className="w-4 h-4 sm:w-5 sm:h-5 transition-transform group-hover:translate-x-0.5"
            style={{ color: palette.primary }}
          />
        </button>
      )}
    </>
  );
};
