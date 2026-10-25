import React, { useState } from 'react';
import { HandoffPageConfig } from '../../types/handoff';
import { CheckCircle2, AlertCircle } from 'lucide-react';

interface HandoffDecisionProps {
  decision: HandoffPageConfig['decision'] & { isBlocked?: boolean };
  palette: HandoffPageConfig['palette'];
  onContinue: () => void;
  discrepancies?: any[];
}

export const HandoffDecision: React.FC<HandoffDecisionProps> = ({
  decision,
  onContinue,
  discrepancies = [],
}) => {
  const isBlocked = decision.isBlocked ?? (decision.type === 'needs_review');
  const [selectedResolution, setSelectedResolution] = useState<'canonical' | 'handoff'>('canonical');
  const [isResolvedManually, setIsResolvedManually] = useState<boolean>(false);

  const effectiveBlocked = isBlocked && !isResolvedManually;

  return (
    <div className="w-full max-w-3xl mx-auto mt-5 px-3 flex flex-col gap-3 pt-4 border-t border-[#DFE1F2] select-none">
      {/* If blocked, show clear actionable clarification panel */}
      {effectiveBlocked && (
        <div className="w-full bg-[#FAF9FC] border border-[#ECECFA] rounded-xl p-3.5 space-y-2.5">
          <div className="flex items-center gap-2 text-xs font-semibold text-[#171A35]">
            <AlertCircle className="w-4 h-4 text-[#7664E8]" />
            <span>
              Clarification Action Required
              {discrepancies.length > 0
                ? ` (${discrepancies.length} discrepancy${discrepancies.length > 1 ? 'ies' : ''})`
                : ''}
            </span>
          </div>
          <p className="text-xs text-[#737895] leading-relaxed">
            One or more discrepancies require confirmation before code generation. Choose how to reconcile the specification:
          </p>
          <div className="flex flex-col sm:flex-row gap-2 pt-1">
            <button
              type="button"
              onClick={() => setSelectedResolution('canonical')}
              className={`flex-1 text-left px-3 py-2 rounded-lg text-xs border transition-colors ${
                selectedResolution === 'canonical'
                  ? 'border-[#7664E8] bg-[#ECECFA] text-[#171A35] font-medium'
                  : 'border-[#DFE1F2] bg-white text-[#737895]'
              }`}
            >
              <div className="font-semibold text-[#7664E8]">Enforce Canonical Requirement (Recommended)</div>
              <div className="text-[11px] text-[#737895] mt-0.5">Strictly adhere to original user prompt constraints.</div>
            </button>
            <button
              type="button"
              onClick={() => setSelectedResolution('handoff')}
              className={`flex-1 text-left px-3 py-2 rounded-lg text-xs border transition-colors ${
                selectedResolution === 'handoff'
                  ? 'border-[#7664E8] bg-[#ECECFA] text-[#171A35] font-medium'
                  : 'border-[#DFE1F2] bg-white text-[#737895]'
              }`}
            >
              <div className="font-semibold text-[#171A35]">Accept Downstream Proposal</div>
              <div className="text-[11px] text-[#737895] mt-0.5">Permit the downstream agent's proposed implementation detail.</div>
            </button>
          </div>
        </div>
      )}

      {/* Main Action Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-end gap-3 w-full">
        {effectiveBlocked && (
          <span className="text-xs font-mono text-[#B8721A] mr-auto">
            Clarification required before continuing to code generation
          </span>
        )}

        {/* Action Button */}
        {effectiveBlocked ? (
          <button
            type="button"
            onClick={() => {
              setIsResolvedManually(true);
              onContinue();
            }}
            className="flex items-center gap-1.5 px-5 py-2 rounded-xl text-xs font-medium text-white bg-[#7664E8] hover:bg-[#6855DE] shadow-sm active:scale-[0.98] transition-all"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Confirm Resolution & Continue</span>
          </button>
        ) : (
          <button
            type="button"
            onClick={onContinue}
            className="flex items-center px-6 py-2.5 rounded-xl text-xs font-medium text-white bg-[#7664E8] hover:bg-[#6855DE] shadow-sm active:scale-[0.98] transition-all focus:outline-none"
          >
            <span>{decision.actionLabel}</span>
          </button>
        )}
      </div>
    </div>
  );
};
