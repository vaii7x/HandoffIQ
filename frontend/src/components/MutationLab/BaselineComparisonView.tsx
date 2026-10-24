import React, { useState } from 'react';
import { BaselineMetrics } from '../../types/mutationLab';
import { BarChart3, ShieldAlert, Zap } from 'lucide-react';

interface BaselineComparisonViewProps {
  baseline: BaselineMetrics;
}

export const BaselineComparisonView: React.FC<BaselineComparisonViewProps> = ({
  baseline,
}) => {
  const [activeTab, setActiveTab] = useState<'both' | 'without' | 'with'>('both');

  const { withoutHandoffIQ: raw, withHandoffIQ: hiq } = baseline;

  const preservationDelta = hiq.preservationRate - raw.preservationRate;
  const missedDelta = raw.missedRequirements - hiq.missedRequirements;
  const reworkDelta = raw.downstreamReworkMinutes - hiq.downstreamReworkMinutes;

  return (
    <div className="bg-neutral-950/80 rounded border border-white/10 overflow-hidden space-y-4">
      {/* 1. Header with View Toggle & Disclaimer */}
      <div className="px-4 py-3.5 border-b border-white/10 bg-white/[0.02] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-sky-400" />
            <h2 className="text-xs font-mono font-medium tracking-wide text-white/90 uppercase">
              Baseline Comparison · Without vs. With HandoffIQ
            </h2>
          </div>
          <p className="text-[11px] text-white/50 mt-0.5">
            Evaluating downstream impact of raw prompt handoffs versus contract-validated boundaries.
          </p>
        </div>

        {/* View Filter Pill */}
        <div className="flex items-center gap-2">
          <div className="grid grid-cols-3 bg-neutral-900 p-0.5 rounded border border-white/15 text-[11px] font-mono">
            <button
              type="button"
              onClick={() => setActiveTab('both')}
              className={`px-2 py-0.5 rounded transition-colors ${
                activeTab === 'both' ? 'bg-white/15 text-white' : 'text-white/40 hover:text-white/80'
              }`}
            >
              Side-by-Side
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('without')}
              className={`px-2 py-0.5 rounded transition-colors ${
                activeTab === 'without' ? 'bg-white/15 text-white' : 'text-white/40 hover:text-white/80'
              }`}
            >
              Without HandoffIQ
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('with')}
              className={`px-2 py-0.5 rounded transition-colors ${
                activeTab === 'with' ? 'bg-white/15 text-white' : 'text-white/40 hover:text-white/80'
              }`}
            >
              With HandoffIQ
            </button>
          </div>
        </div>
      </div>

      {/* 2. Visual Preservation Rate Mini-Chart */}
      <div className="px-4 grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Without HandoffIQ Card */}
        {(activeTab === 'both' || activeTab === 'without') && (
          <div className="p-3.5 rounded bg-rose-950/10 border border-rose-900/30 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-mono text-rose-300 font-semibold flex items-center gap-1.5">
                <ShieldAlert className="w-3.5 h-3.5" />
                Raw Agent Handoff (Unprotected)
              </span>
              <span className="font-mono text-base font-bold text-rose-300" style={{ fontVariantNumeric: 'tabular-nums' }}>
                {raw.preservationRate}% preserved
              </span>
            </div>
            {/* Visual Bar */}
            <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
              <div
                className="h-full bg-rose-500 rounded-full transition-all duration-500"
                style={{ width: `${raw.preservationRate}%` }}
              />
            </div>
            <p className="text-[11px] text-white/50 leading-relaxed">
              Omissions and boundary distortions pass silently to Coding Agent, causing regressions.
            </p>
          </div>
        )}

        {/* With HandoffIQ Card */}
        {(activeTab === 'both' || activeTab === 'with') && (
          <div className="p-3.5 rounded bg-blue-950/15 border border-blue-900/40 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-mono text-sky-300 font-semibold flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5" />
                HandoffIQ Contract Enforcement
              </span>
              <span className="font-mono text-base font-bold text-sky-300" style={{ fontVariantNumeric: 'tabular-nums' }}>
                {hiq.preservationRate}% preserved
              </span>
            </div>
            {/* Visual Bar */}
            <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
              <div
                className="h-full bg-sky-400 rounded-full transition-all duration-500"
                style={{ width: `${hiq.preservationRate}%` }}
              />
            </div>
            <p className="text-[11px] text-white/50 leading-relaxed">
              Discrepancies intercepted at gate; safe auto-repairs restore canonical specifications.
            </p>
          </div>
        )}
      </div>

      {/* 3. Detailed Metrics Comparison Table */}
      <div className="px-4 pb-4">
        <div className="border border-white/10 rounded overflow-hidden text-xs">
          <div className="bg-black/50 px-3 py-2 border-b border-white/10 text-[11px] font-mono text-white/40 grid grid-cols-12 gap-2">
            <span className="col-span-5">BENCHMARK METRIC</span>
            <span className="col-span-2 text-rose-300/80">WITHOUT HANDOFFIQ</span>
            <span className="col-span-2 text-sky-300/80">WITH HANDOFFIQ</span>
            <span className="col-span-3 text-right">MEASURED DELTA</span>
          </div>

          <div className="divide-y divide-white/5 bg-neutral-950/40 font-mono">
            {/* Row 1: Preservation Rate */}
            <div className="px-3 py-2.5 grid grid-cols-12 gap-2 items-center">
              <span className="col-span-5 text-white/80 font-sans">
                Requirement Preservation Rate
              </span>
              <span className="col-span-2 text-rose-400">
                {raw.preservationRate}%
              </span>
              <span className="col-span-2 text-emerald-400 font-semibold">
                {hiq.preservationRate}%
              </span>
              <span className="col-span-3 text-right text-emerald-400">
                +{preservationDelta}% recovery
              </span>
            </div>

            {/* Row 2: Missed Requirements */}
            <div className="px-3 py-2.5 grid grid-cols-12 gap-2 items-center">
              <span className="col-span-5 text-white/80 font-sans">
                Leaked / Missed Requirements
              </span>
              <span className="col-span-2 text-rose-400">
                {raw.missedRequirements} requirements
              </span>
              <span className="col-span-2 text-emerald-400">
                {hiq.missedRequirements}
              </span>
              <span className="col-span-3 text-right text-emerald-400">
                -{missedDelta} omissions stopped
              </span>
            </div>

            {/* Row 3: Unresolved Discrepancies */}
            <div className="px-3 py-2.5 grid grid-cols-12 gap-2 items-center">
              <span className="col-span-5 text-white/80 font-sans">
                Unresolved Inconsistencies
              </span>
              <span className="col-span-2 text-rose-400">
                {raw.unresolvedDiscrepancies} passed downstream
              </span>
              <span className="col-span-2 text-white/80">
                {hiq.unresolvedDiscrepancies} (gated for review)
              </span>
              <span className="col-span-3 text-right text-sky-400">
                100% boundary contained
              </span>
            </div>

            {/* Row 4: Automated Repairs */}
            <div className="px-3 py-2.5 grid grid-cols-12 gap-2 items-center">
              <span className="col-span-5 text-white/80 font-sans">
                Self-Healing Auto-Repairs Applied
              </span>
              <span className="col-span-2 text-white/40">
                0 (no repair harness)
              </span>
              <span className="col-span-2 text-emerald-400">
                {hiq.repairsApplied} auto-restored
              </span>
              <span className="col-span-3 text-right text-emerald-400">
                +{hiq.repairsApplied} self-healed
              </span>
            </div>

            {/* Row 5: Downstream Developer Rework */}
            <div className="px-3 py-2.5 grid grid-cols-12 gap-2 items-center">
              <span className="col-span-5 text-white/80 font-sans">
                Estimated Downstream Debug/Rework Time
              </span>
              <span className="col-span-2 text-rose-400">
                ~{raw.downstreamReworkMinutes} mins
              </span>
              <span className="col-span-2 text-emerald-400 font-semibold">
                ~{hiq.downstreamReworkMinutes} mins
              </span>
              <span className="col-span-3 text-right text-emerald-400">
                -{reworkDelta} mins saved
              </span>
            </div>

            {/* Row 6: Verification Overhead */}
            <div className="px-3 py-2.5 grid grid-cols-12 gap-2 items-center">
              <span className="col-span-5 text-white/80 font-sans">
                Verification Gate Latency Overhead
              </span>
              <span className="col-span-2 text-white/50">
                0 ms (no check)
              </span>
              <span className="col-span-2 text-white/80">
                +{hiq.verificationLatencyMs} ms
              </span>
              <span className="col-span-3 text-right text-white/40">
                Sub-second gate
              </span>
            </div>

            {/* Row 7: Token Cost */}
            <div className="px-3 py-2.5 grid grid-cols-12 gap-2 items-center">
              <span className="col-span-5 text-white/80 font-sans">
                Verification Token & Computation Cost
              </span>
              <span className="col-span-2 text-white/50">
                $0.000
              </span>
              <span className="col-span-2 text-white/80">
                ${hiq.tokenCost.toFixed(4)}
              </span>
              <span className="col-span-3 text-right text-white/40">
                Minimal overhead
              </span>
            </div>
          </div>
        </div>

        {/* Honest Disclaimer Label */}
        <div className="mt-2.5 flex items-center justify-between text-[10px] font-mono text-white/40 px-1">
          <span>* Latency and token cost metrics calculated from deterministic simulation model.</span>
          <span className="px-2 py-0.5 rounded bg-white/5 border border-white/10 text-white/60">
            SIMULATED BENCHMARK HEURISTICS
          </span>
        </div>
      </div>
    </div>
  );
};
