import React from 'react';
import { CheckCircle2 } from 'lucide-react';
import type { DemoRequirement } from '../../types/demo';

interface Step1Props {
  requirements: DemoRequirement[];
}

export const Step1Requirements: React.FC<Step1Props> = ({ requirements }) => {
  return (
    <div className="w-full max-w-4xl mx-auto space-y-3">
      {/* Concise Header */}
      <div className="flex items-center justify-between pb-2 border-b border-[#DFE1F2]">
        <div>
          <h3 className="text-sm sm:text-base font-semibold text-[#171A35]">
            Canonical Requirements
          </h3>
          <p className="text-xs text-[#737895]">
            Authoritative specifications defining target system invariants.
          </p>
        </div>
        <span className="font-mono text-xs text-[#737895] bg-[#FAF9FC] border border-[#DFE1F2] px-2.5 py-0.5 rounded-md">
          {requirements.length} specifications
        </span>
      </div>

      {/* Grid of Canonical Requirements */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
        {requirements.map((req) => (
          <div
            key={req.id}
            className="p-3.5 sm:p-4 rounded-xl bg-white border border-[#DFE1F2] shadow-xs flex flex-col justify-between space-y-2.5"
          >
            <div className="space-y-1.5">
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-[#FAF9FC] text-[#7664E8] border border-[#DFE1F2]">
                  {req.source_id}
                </span>
                <span className="text-[10px] font-mono uppercase tracking-wider text-[#737895]">
                  {req.category}
                </span>
              </div>
              <h4 className="text-xs sm:text-sm font-semibold text-[#171A35]">
                {req.title}
              </h4>
              <p className="text-xs text-[#171A35]/80 leading-relaxed font-sans">
                {req.description}
              </p>
            </div>

            <div className="pt-2 border-t border-[#DFE1F2]/60 flex items-center justify-between text-[11px]">
              <span className="flex items-center gap-1 font-medium text-[#1E8E5A]">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#1E8E5A]" />
                Authoritative
              </span>
              <span className="text-[#737895] font-mono text-[10px]">
                {req.id}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
