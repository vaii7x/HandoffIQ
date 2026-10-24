import React from 'react';
import { RequirementDiscrepancy } from '../../types/handoff';
import { AgentPalette } from '../../types/agent';
import { StatusBadge, StatusVariant } from '../ui/StatusBadge';

interface ExpandableValidationDetailsProps {
  kind: 'requirement_comparison' | 'discrepancy_list' | 'constraint_risks';
  discrepancies?: RequirementDiscrepancy[];
  palette?: AgentPalette;
}

export const ExpandableValidationDetails: React.FC<
  ExpandableValidationDetailsProps
> = ({ kind, discrepancies = [] }) => {
  if (kind === 'requirement_comparison') {
    return (
      <div className="pt-2 pb-1 text-xs">
        <div className="flex items-center justify-between text-[11px] font-mono text-white/40 pb-1.5 border-b border-white/5">
          <span>REQUIREMENT DOMAIN</span>
          <span>EVALUATION</span>
        </div>
        <div className="divide-y divide-white/5">
          {[
            { domain: 'Core Security & OAuth2 TTL', evaluation: '3 of 3 verified' },
            { domain: 'WebGL 3D Engine Context & Shaders', evaluation: '4 of 4 verified' },
            { domain: 'EventSource / SSE Connection & Fallback', evaluation: '3 of 3 verified' },
            { domain: 'Workflow Stage Transitions & Stepper', evaluation: '2 of 2 verified' },
          ].map((item, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between py-2 text-[12px]"
            >
              <span className="text-white/80">{item.domain}</span>
              <span className="font-mono text-[11px] text-white/50">
                {item.evaluation}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (kind === 'discrepancy_list') {
    return (
      <div className="pt-2 pb-1 divide-y divide-white/10">
        {discrepancies.map((disc) => {
          const badgeVariant: StatusVariant =
            disc.type === 'missing'
              ? 'missing'
              : disc.type === 'removed'
              ? 'removed'
              : disc.type === 'altered'
              ? 'altered'
              : disc.type === 'added'
              ? 'added'
              : 'neutral';

          const formattedRepairText = disc.repairStatus
            .replace(/^Auto-repaired:\s*/i, 'Repaired · ')
            .replace(/^Auto-repaired\s*-\s*/i, 'Repaired · ');

          return (
            <div key={disc.id} className="py-3 text-xs space-y-2.5">
              {/* A. Requirement Header */}
              <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1.5">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-semibold text-white/90">
                    {disc.requirementId}
                  </span>
                  <StatusBadge variant={badgeVariant} />
                </div>
                <div className="text-[11px] text-white/50 font-sans">
                  {formattedRepairText}
                </div>
              </div>

              {/* B. Original vs Received Comparison */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[12px] leading-relaxed pt-1">
                {/* Original Requirement */}
                <div className="space-y-1">
                  <span className="text-[10px] uppercase font-mono tracking-wider text-white/40 block">
                    Original requirement
                  </span>
                  <p className="text-white/70">{disc.originalText}</p>
                </div>

                {/* Received Handoff */}
                <div className="space-y-1 md:border-l md:border-white/10 md:pl-3">
                  <span className="text-[10px] uppercase font-mono tracking-wider text-white/40 block">
                    Received handoff
                  </span>
                  <p className="text-white/85">{disc.receivedText}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  // constraint_risks
  return (
    <div className="pt-2 pb-1 text-xs divide-y divide-white/5">
      <div className="py-2.5 space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-[12px] font-medium text-white/90">
            Semantic Drift Analysis
          </span>
          <span className="text-[11px] font-mono text-white/50">
            0 critical drifts
          </span>
        </div>
        <p className="text-[11px] text-white/55 leading-relaxed">
          Prompt embeddings between Research specifications and Coding contract evaluated at 98.4% cosine similarity threshold.
        </p>
      </div>

      <div className="py-2.5 space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-[12px] font-medium text-white/90">
            Performance Constraint Enforcement
          </span>
          <span className="text-[11px] font-mono text-amber-300/80">
            Throttle applied
          </span>
        </div>
        <p className="text-[11px] text-white/55 leading-relaxed">
          Delta-time loop throttle active on WebGL particle loops to maintain stable 60 FPS on mobile viewports.
        </p>
      </div>
    </div>
  );
};
