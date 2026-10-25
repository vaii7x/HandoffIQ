import React from 'react';
import type { DemoHandoffItem } from '../../types/demo';

interface Step2Props {
  handoffItems: DemoHandoffItem[];
}

export const Step2BrokenHandoff: React.FC<Step2Props> = ({ handoffItems }) => {
  const alteredCount = handoffItems.filter((i) => i.status === 'broken').length;
  const unchangedCount = handoffItems.filter((i) => i.status === 'preserved').length;

  return (
    <div className="w-full max-w-4xl mx-auto space-y-3">
      {/* Concise Header */}
      <div className="flex items-center justify-between pb-2 border-b border-[#DFE1F2]">
        <div>
          <h3 className="text-sm sm:text-base font-semibold text-[#171A35]">
            Downstream Handoff Comparison
          </h3>
          <p className="text-xs text-[#737895]">
            Compare original requirements against the handoff specification received downstream.
          </p>
        </div>
        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="text-[#D9383A] bg-[#FEF6F7] border border-[#FCD6D9] px-2 py-0.5 rounded">
            {alteredCount} altered
          </span>
          <span className="text-[#1E8E5A] bg-[#F2FAF6] border border-[#CEF0DF] px-2 py-0.5 rounded">
            {unchangedCount} unchanged
          </span>
        </div>
      </div>

      {/* Side-by-Side Comparison List */}
      <div className="space-y-2.5 pt-1">
        {handoffItems.map((item) => {
          const isAltered = item.status === 'broken';

          return (
            <div
              key={item.id}
              className={`p-3.5 sm:p-4 rounded-xl border bg-white shadow-xs transition-colors ${
                isAltered
                  ? 'border-[#FCD6D9]'
                  : 'border-[#DFE1F2]'
              }`}
            >
              {/* Card Meta Bar */}
              <div className="flex items-center justify-between gap-2 pb-2 mb-2.5 border-b border-[#DFE1F2]/60">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-[#FAF9FC] text-[#7664E8] border border-[#DFE1F2]">
                    {item.requirement_id}
                  </span>
                </div>

                <div>
                  {isAltered ? (
                    <span className="font-mono text-[11px] font-medium text-[#D9383A] bg-[#FEF6F7] border border-[#FCD6D9] px-2 py-0.5 rounded">
                      Altered
                    </span>
                  ) : (
                    <span className="font-mono text-[11px] font-medium text-[#1E8E5A] bg-[#F2FAF6] border border-[#CEF0DF] px-2 py-0.5 rounded">
                      Unchanged
                    </span>
                  )}
                </div>
              </div>

              {/* Side-by-Side Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                {/* Original requirement */}
                <div className="p-3 rounded-lg bg-[#FAF9FC] border border-[#DFE1F2]/70 space-y-1">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-[#737895] font-medium block">
                    Original requirement
                  </span>
                  <p className="text-[#171A35] leading-relaxed">
                    {item.original_text}
                  </p>
                </div>

                {/* Received handoff */}
                <div
                  className={`p-3 rounded-lg border space-y-1 ${
                    isAltered
                      ? 'bg-[#FFF8F8] border-[#FCD6D9]'
                      : 'bg-[#F2FAF6] border-[#CEF0DF]'
                  }`}
                >
                  <span
                    className={`text-[10px] font-mono uppercase tracking-wider font-medium block ${
                      isAltered ? 'text-[#D9383A]' : 'text-[#1E8E5A]'
                    }`}
                  >
                    Received handoff
                  </span>
                  <p
                    className={`leading-relaxed ${
                      isAltered ? 'text-[#9C1C1E] font-medium' : 'text-[#136C43]'
                    }`}
                  >
                    {item.received_text}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
