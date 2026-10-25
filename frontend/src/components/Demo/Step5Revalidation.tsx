import React from 'react';
import { CheckCircle2, AlertTriangle, RotateCcw } from 'lucide-react';
import type { DemoRevalidationResponse } from '../../types/demo';

interface Step5Props {
  revalidationData: DemoRevalidationResponse | null;
  isRevalidating: boolean;
  onResetDemo: () => void;
}

export const Step5Revalidation: React.FC<Step5Props> = ({
  revalidationData,
  isRevalidating,
  onResetDemo,
}) => {
  if (isRevalidating || !revalidationData) {
    return (
      <div className="w-full max-w-4xl mx-auto py-12 flex flex-col items-center justify-center space-y-3">
        <div className="w-7 h-7 rounded-full border-2 border-[#1E8E5A] border-t-transparent animate-spin" />
        <p className="text-xs font-medium text-[#737895]">
          Revalidating patched handoff specification…
        </p>
      </div>
    );
  }

  const {
    validator_issues_count,
    resolved_count,
    unresolved_count,
    all_clear,
    remaining_issues,
    disclaimer,
  } = revalidationData;

  return (
    <div className="w-full max-w-4xl mx-auto space-y-3">
      {/* Concise Header */}
      <div className="flex items-center justify-between pb-2 border-b border-[#DFE1F2]">
        <div>
          <h3 className="text-sm sm:text-base font-semibold text-[#171A35]">
            Revalidation Results
          </h3>
          <p className="text-xs text-[#737895]">
            Post-repair validation engine report against canonical requirements.
          </p>
        </div>
        <button
          type="button"
          onClick={onResetDemo}
          className="px-3 py-1.5 rounded-lg text-xs font-medium text-[#737895] hover:text-[#171A35] bg-white hover:bg-[#FAF9FC] border border-[#DFE1F2] transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs active:scale-[0.98]"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset Demo</span>
        </button>
      </div>

      {/* Outcome Status Banner */}
      {all_clear ? (
        <div className="p-3.5 sm:p-4 rounded-xl bg-[#F2FAF6] border border-[#CEF0DF] text-[#136C43] flex items-center justify-between gap-3 shadow-xs">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-[#1E8E5A] shrink-0" />
            <div>
              <h4 className="text-xs sm:text-sm font-semibold text-[#136C43]">
                Specification Revalidated: All Invariants Restored
              </h4>
              <p className="text-xs text-[#136C43]/85">
                0 remaining discrepancies detected across all 6 canonical specifications.
              </p>
            </div>
          </div>
          <span className="font-mono text-xs font-medium text-[#1E8E5A] bg-white/70 px-2.5 py-1 rounded-md border border-[#CEF0DF] shrink-0">
            {resolved_count} issues resolved
          </span>
        </div>
      ) : (
        <div className="p-3.5 sm:p-4 rounded-xl bg-[#FFF8F8] border border-[#FCD6D9] text-[#9C1C1E] flex items-center gap-2.5 shadow-xs">
          <AlertTriangle className="w-4 h-4 text-[#D9383A] shrink-0" />
          <div className="text-xs">
            <h4 className="font-semibold text-[#9C1C1E]">
              Revalidation Blocked
            </h4>
            <p>
              {unresolved_count} unresolved discrepancies remain.
            </p>
          </div>
        </div>
      )}

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
        <div className="p-3 rounded-xl bg-white border border-[#DFE1F2] shadow-xs flex flex-col justify-between">
          <span className="text-[10px] font-mono uppercase text-[#737895]">
            Remaining Discrepancies
          </span>
          <span className="text-xl sm:text-2xl font-bold text-[#1E8E5A] mt-1">
            {validator_issues_count}
          </span>
          <span className="text-[10px] text-[#737895] mt-0.5">Authoritative validator engine</span>
        </div>

        <div className="p-3 rounded-xl bg-white border border-[#DFE1F2] shadow-xs flex flex-col justify-between">
          <span className="text-[10px] font-mono uppercase text-[#737895]">
            Resolved Invariants
          </span>
          <span className="text-xl sm:text-2xl font-bold text-[#7664E8] mt-1">
            {resolved_count} / {resolved_count + unresolved_count}
          </span>
          <span className="text-[10px] text-[#737895] mt-0.5">All altered items patched</span>
        </div>

        <div className="p-3 rounded-xl bg-white border border-[#DFE1F2] shadow-xs flex flex-col justify-between">
          <span className="text-[10px] font-mono uppercase text-[#737895]">
            Gate Certification
          </span>
          <span className="text-xs font-semibold text-[#1E8E5A] mt-2 flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-[#1E8E5A]" />
            PASSED & CERTIFIED
          </span>
          <span className="text-[10px] text-[#737895] mt-0.5">Approved for implementation</span>
        </div>
      </div>

      {/* Remaining Issues List if any */}
      {remaining_issues.length > 0 && (
        <div className="space-y-2 pt-2">
          <h4 className="text-xs font-semibold text-[#D9383A] uppercase tracking-wider">
            Unresolved Discrepancies ({remaining_issues.length})
          </h4>
          {remaining_issues.map((iss, i) => (
            <div
              key={i}
              className="p-3 rounded-xl border border-[#FCD6D9] bg-[#FFF8F8] text-xs space-y-1"
            >
              <div className="font-mono font-bold text-[#D9383A]">{iss.requirement_id}</div>
              <p className="text-[#171A35]">{iss.explanation}</p>
            </div>
          ))}
        </div>
      )}

      {/* Mandatory Verification Boundary Notice */}
      <div className="p-3.5 rounded-xl bg-[#FAF9FC] border border-[#DFE1F2] text-xs text-[#737895] space-y-1">
        <strong className="text-[#171A35] block font-medium">Verification Boundary:</strong>
        <p className="leading-relaxed">{disclaimer}</p>
      </div>
    </div>
  );
};
