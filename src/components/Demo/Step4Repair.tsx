import React from 'react';
import type { DemoRepairItem } from '../../types/demo';

interface Step4Props {
  repairs: DemoRepairItem[];
  isRepaired: boolean;
  onApplyRepairs: () => void;
  isRepairing: boolean;
}

export const Step4Repair: React.FC<Step4Props> = ({
  repairs,
  isRepaired,
  onApplyRepairs,
  isRepairing,
}) => {
  return (
    <div className="w-full max-w-4xl mx-auto space-y-3">
      {/* Concise Header */}
      <div className="flex items-center justify-between pb-2 border-b border-[#DFE1F2]">
        <div>
          <h3 className="text-sm sm:text-base font-semibold text-[#171A35]">
            Specification Repairs
          </h3>
          <p className="text-xs text-[#737895]">
            Targeted patches restoring canonical invariants to the downstream handoff.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {!isRepaired ? (
            <button
              type="button"
              onClick={onApplyRepairs}
              disabled={isRepairing}
              className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-[#7664E8] hover:bg-[#6855DE] text-white transition-all cursor-pointer disabled:opacity-50 shadow-xs active:scale-[0.98]"
            >
              {isRepairing ? 'Applying repairs…' : 'Apply Repairs'}
            </button>
          ) : (
            <span className="text-[11px] font-mono text-[#1E8E5A] bg-[#F2FAF6] border border-[#CEF0DF] px-2.5 py-1 rounded-md font-medium">
              Patches applied ({repairs.length})
            </span>
          )}
        </div>
      </div>

      {/* Before / After Diff Cards */}
      <div className="space-y-2.5 pt-1">
        {repairs.map((rep) => (
          <div
            key={rep.id}
            className="p-3.5 sm:p-4 rounded-xl border border-[#DFE1F2] bg-white shadow-xs space-y-2.5"
          >
            {/* Header info */}
            <div className="flex items-center justify-between gap-2 border-b border-[#DFE1F2]/60 pb-2">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-[#FAF9FC] text-[#7664E8] border border-[#DFE1F2]">
                  {rep.requirement_id}
                </span>
                <span className="text-[11px] font-mono text-[#737895]">
                  {rep.id}
                </span>
              </div>

              <div>
                {isRepaired ? (
                  <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-[#F2FAF6] text-[#1E8E5A] border border-[#CEF0DF]">
                    Repaired
                  </span>
                ) : (
                  <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-[#FAF9FC] text-[#737895] border border-[#DFE1F2]">
                    Pending
                  </span>
                )}
              </div>
            </div>

            {/* Diffs */}
            <div className="space-y-1.5 text-xs font-mono">
              {/* Before */}
              <div className="p-2.5 rounded-lg bg-[#FFF8F8] border border-[#FCD6D9] text-[#9C1C1E] flex items-start gap-2">
                <span className="select-none font-bold text-[#D9383A] shrink-0">[-]</span>
                <span className="leading-relaxed">{rep.broken_text}</span>
              </div>

              {/* After */}
              <div className="p-2.5 rounded-lg bg-[#F2FAF6] border border-[#CEF0DF] text-[#136C43] flex items-start gap-2">
                <span className="select-none font-bold text-[#1E8E5A] shrink-0">[+]</span>
                <span className="leading-relaxed font-medium">{rep.repaired_text}</span>
              </div>
            </div>

            {/* Rationale */}
            <div className="p-2.5 rounded-lg bg-[#FAF9FC] border border-[#DFE1F2]/60 text-xs text-[#737895] font-sans">
              <strong className="text-[#171A35] font-medium">Repair rationale: </strong>
              <span>{rep.repair_reason}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
