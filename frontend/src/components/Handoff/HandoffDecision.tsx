import React from 'react';
import { HandoffPageConfig } from '../../types/handoff';
import { ArrowRight } from 'lucide-react';
import { StatusBadge } from '../ui/StatusBadge';

interface HandoffDecisionProps {
  decision: HandoffPageConfig['decision'];
  palette: HandoffPageConfig['palette'];
  onContinue: () => void;
}

export const HandoffDecision: React.FC<HandoffDecisionProps> = ({
  decision,
  palette,
  onContinue,
}) => {
  return (
    <div className="w-full max-w-3xl mx-auto mt-4 px-3 flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-white/10 select-none">
      {/* Decision Status & Description */}
      <div className="flex items-center gap-2.5">
        <StatusBadge
          variant={decision.type === 'ready_for_coding' || decision.type === 'ready_for_deploy' ? 'passed' : 'needs_review'}
          label={decision.label}
        />
        <span className="text-[11px] text-white/50 hidden md:inline truncate max-w-md">
          {decision.description}
        </span>
      </div>

      {/* Subtle Continue Action Button */}
      <button
        type="button"
        onClick={onContinue}
        className="group flex items-center gap-2 px-3 py-1.5 rounded text-xs font-medium text-white/90 hover:text-white bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 transition-all duration-200 active:scale-[0.98] focus:outline-none focus:ring-1 focus:ring-white/30"
      >
        <span>{decision.actionLabel}</span>
        <ArrowRight
          className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5"
          style={{ color: palette.primary }}
        />
      </button>
    </div>
  );
};
