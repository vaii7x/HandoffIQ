import React from 'react';
import {
  TestCaseResult,
  TestFailureDetail,
  SelfHealingRepair,
} from '../../types/handoff';
import { AgentPalette } from '../../types/agent';
import { StatusBadge } from '../ui/StatusBadge';

interface ExpandableTestingDetailsProps {
  kind: 'test_suite' | 'failure_analysis' | 'self_healing_fixes';
  testCases?: TestCaseResult[];
  failures?: TestFailureDetail[];
  repairs?: SelfHealingRepair[];
  palette?: AgentPalette;
}

export const ExpandableTestingDetails: React.FC<
  ExpandableTestingDetailsProps
> = ({ kind, testCases = [], failures = [], repairs = [] }) => {
  if (kind === 'test_suite') {
    return (
      <div className="pt-2 pb-1 text-xs space-y-2">
        {/* Pale lavender header row matching Image 2 */}
        <div className="flex items-center justify-between text-xs font-semibold text-[#171A35] px-4 py-2.5 bg-[#ECECFA] rounded-xl mb-2 select-none">
          <span>Test Suite & Case</span>
          <span>Result</span>
        </div>
        <div className="space-y-2">
          {testCases.map((tc) => (
            <div
              key={tc.id}
              className="p-3 bg-white hover:bg-[#FAF9FC] border border-[#DFE1F2] rounded-xl transition-all shadow-[0_1px_2px_rgba(23,26,53,0.02)] flex flex-col sm:flex-row sm:items-center justify-between gap-2"
            >
              <div className="space-y-0.5 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-semibold text-[#171A35] truncate">
                    {tc.name}
                  </span>
                  <span className="text-[10px] text-[#737895] font-mono">
                    {tc.tool}
                  </span>
                </div>
                {tc.outputSnippet && (
                  <p className="text-[11px] text-[#737895] font-mono truncate max-w-lg">
                    {tc.outputSnippet}
                  </p>
                )}
              </div>

              <div className="flex items-center gap-3 shrink-0 self-start sm:self-center">
                <span className="text-[10px] font-mono text-[#737895]">
                  {tc.duration}
                </span>
                <StatusBadge
                  variant={
                    tc.status === 'passed'
                      ? 'passed'
                      : tc.status === 'repaired'
                      ? 'repaired'
                      : tc.status === 'failed'
                      ? 'removed'
                      : 'running'
                  }
                  label={
                    tc.status === 'passed'
                      ? 'Passed'
                      : tc.status === 'repaired'
                      ? 'Repaired'
                      : tc.status === 'failed'
                      ? 'Failed'
                      : 'Running'
                  }
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (kind === 'failure_analysis') {
    return (
      <div className="pt-2 pb-1 text-xs space-y-2">
        {failures.map((f) => (
          <div key={f.id} className="p-3.5 bg-white border border-[#DFE1F2] rounded-xl shadow-[0_1px_3px_rgba(23,26,53,0.02)] space-y-2">
            <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-[#171A35]">
                  {f.summary}
                </span>
                <StatusBadge variant="needs_review" label="Failed" />
              </div>
              <span className="font-mono text-[10px] text-[#737895]">
                Requirement: {f.linkedRequirementId}
              </span>
            </div>

            <div className="text-[11px] font-mono text-[#B8721A] bg-[#FFF6E5] p-2.5 rounded-lg border border-[#FFE8BF] leading-relaxed overflow-x-auto">
              {f.errorDetails}
            </div>

            <div className="text-[10px] font-mono text-[#737895]">
              Files: {f.affectedFiles.join(', ')}
            </div>
          </div>
        ))}
      </div>
    );
  }

  // self_healing_fixes
  return (
    <div className="pt-2 pb-1 text-xs space-y-2">
      {repairs.map((r) => (
        <div key={r.id} className="p-3.5 bg-white border border-[#DFE1F2] rounded-xl shadow-[0_1px_3px_rgba(23,26,53,0.02)] space-y-2">
          <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-[#171A35]">
                {r.failureSummary}
              </span>
              <StatusBadge
                variant="repaired"
                label={`Repaired · Attempt #${r.attemptNumber}`}
              />
            </div>
            <span className="font-mono text-[10px] text-[#7664E8] bg-[#ECECFA] px-2 py-0.5 rounded border border-[#DFE1F2]">
              Rerun: {r.rerunResult.toUpperCase()}
            </span>
          </div>

          <p className="text-[11px] text-[#737895] leading-relaxed">
            {r.repairSummary}
          </p>

          <div className="text-[10px] font-mono text-[#737895]">
            Patched: {r.affectedFiles.join(', ')}
          </div>
        </div>
      ))}
    </div>
  );
};
