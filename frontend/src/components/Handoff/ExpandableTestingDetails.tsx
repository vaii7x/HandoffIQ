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
      <div className="pt-2 pb-1 text-xs">
        <div className="flex items-center justify-between text-[11px] font-mono text-white/40 pb-1.5 border-b border-white/5">
          <span>TEST SUITE & CASE</span>
          <span>RESULT</span>
        </div>
        <div className="divide-y divide-white/5">
          {testCases.map((tc) => (
            <div
              key={tc.id}
              className="py-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
            >
              <div className="space-y-0.5 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[12px] text-white/90 truncate">
                    {tc.name}
                  </span>
                  <span className="text-[10px] text-white/35 font-mono">
                    {tc.tool}
                  </span>
                </div>
                {tc.outputSnippet && (
                  <p className="text-[11px] text-white/50 font-mono truncate max-w-lg">
                    {tc.outputSnippet}
                  </p>
                )}
              </div>

              <div className="flex items-center gap-3 shrink-0 self-start sm:self-center">
                <span className="text-[10px] font-mono text-white/40">
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
      <div className="pt-2 pb-1 text-xs divide-y divide-white/10">
        {failures.map((f) => (
          <div key={f.id} className="py-3 space-y-2">
            <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1">
              <div className="flex items-center gap-2">
                <span className="text-[12px] font-medium text-white/90">
                  {f.summary}
                </span>
                <StatusBadge variant="needs_review" label="Failed" />
              </div>
              <span className="font-mono text-[10px] text-white/40">
                Requirement: {f.linkedRequirementId}
              </span>
            </div>

            <div className="text-[11px] font-mono text-amber-200/80 bg-black/30 p-2.5 rounded border border-white/5 leading-relaxed overflow-x-auto">
              {f.errorDetails}
            </div>

            <div className="text-[10px] font-mono text-white/40">
              Files: {f.affectedFiles.join(', ')}
            </div>
          </div>
        ))}
      </div>
    );
  }

  // self_healing_fixes
  return (
    <div className="pt-2 pb-1 text-xs divide-y divide-white/10">
      {repairs.map((r) => (
        <div key={r.id} className="py-3 space-y-2">
          <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1">
            <div className="flex items-center gap-2">
              <span className="text-[12px] font-medium text-white/90">
                {r.failureSummary}
              </span>
              <StatusBadge
                variant="repaired"
                label={`Repaired · Attempt #${r.attemptNumber}`}
              />
            </div>
            <span className="font-mono text-[10px] text-emerald-400/80">
              Rerun: {r.rerunResult.toUpperCase()}
            </span>
          </div>

          <p className="text-[11px] text-white/70 leading-relaxed">
            {r.repairSummary}
          </p>

          <div className="text-[10px] font-mono text-white/40">
            Patched: {r.affectedFiles.join(', ')}
          </div>
        </div>
      ))}
    </div>
  );
};
