import React, { useState } from 'react';
import {
  CanonicalRequirement,
  MutatedItem,
  DetectedDiscrepancy,
} from '../../types/mutationLab';
import { StatusBadge, StatusVariant } from '../ui/StatusBadge';
import { Info, Shield, AlertOctagon, CheckCircle2, ChevronRight, X } from 'lucide-react';

interface HandoffSideBySideComparisonProps {
  canonicalRequirements: CanonicalRequirement[];
  mutations: MutatedItem[];
  detectedDiscrepancies: DetectedDiscrepancy[];
}

export const HandoffSideBySideComparison: React.FC<
  HandoffSideBySideComparisonProps
> = ({ canonicalRequirements, mutations, detectedDiscrepancies }) => {
  const [selectedReqId, setSelectedReqId] = useState<string | null>(
    canonicalRequirements[0]?.id || null
  );

  // Map mutated items by requirementId
  const mutationMap = new Map<string, MutatedItem>();
  mutations.forEach((m) => {
    mutationMap.set(m.targetRequirementId, m);
  });

  // Map detected discrepancies by requirementId
  const discrepancyMap = new Map<string, DetectedDiscrepancy>();
  detectedDiscrepancies.forEach((d) => {
    discrepancyMap.set(d.requirementId, d);
  });

  // Find added requirements that don't match any canonical requirement
  const addedMutations = mutations.filter((m) => m.isAdded);

  // Selected item details
  const selectedCanonical = canonicalRequirements.find(
    (r) => r.id === selectedReqId
  );
  const selectedMutation = selectedReqId
    ? mutationMap.get(selectedReqId)
    : undefined;
  const selectedDiscrepancy = selectedReqId
    ? discrepancyMap.get(selectedReqId)
    : undefined;

  const getStatusBadgeVariant = (
    type?: string
  ): StatusVariant => {
    if (!type) return 'passed';
    switch (type) {
      case 'missing':
        return 'missing';
      case 'altered':
        return 'altered';
      case 'weakened':
        return 'altered';
      case 'added':
        return 'added';
      case 'contradiction':
        return 'removed';
      case 'ordering_loss':
        return 'needs_review';
      default:
        return 'passed';
    }
  };

  return (
    <div className="space-y-4">
      {/* 1. Legend Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5 rounded bg-white/[0.02] border border-white/5 text-[11px] font-mono text-white/60">
        <span className="text-white/40 uppercase tracking-wider">Legend:</span>
        <div className="flex flex-wrap items-center gap-3">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-sky-400" />
            <span className="text-white/80">Canonical Spec</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-rose-400" />
            <span className="text-rose-300">Missing / Omitted</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-400" />
            <span className="text-amber-300">Altered Semantics</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-yellow-400" />
            <span className="text-yellow-300">Weakened Constraint</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-purple-400" />
            <span className="text-purple-300">Added / Invented</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-red-400" />
            <span className="text-red-300">Contradiction</span>
          </span>
        </div>
      </div>

      {/* 2. Side-by-Side Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left Column: Immutable Canonical Requirements */}
        <div className="bg-neutral-950/80 rounded border border-blue-900/40 overflow-hidden flex flex-col">
          <div className="px-4 py-3 border-b border-blue-900/30 bg-blue-950/20 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-sky-400" />
              <h2 className="text-xs font-mono font-medium tracking-wide text-sky-200 uppercase">
                Canonical Goal Contract
              </h2>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-950/60 border border-sky-800/40 text-sky-300">
              IMMUTABLE SOURCE OF TRUTH
            </span>
          </div>

          <div className="divide-y divide-white/5 flex-1">
            {canonicalRequirements.map((req) => {
              const isSelected = selectedReqId === req.id;
              const hasMutation = mutationMap.has(req.id);
              const mutation = mutationMap.get(req.id);

              return (
                <div
                  key={req.id}
                  onClick={() => setSelectedReqId(req.id)}
                  className={`p-3.5 cursor-pointer transition-colors ${
                    isSelected
                      ? 'bg-blue-950/30 border-l-2 border-l-sky-400'
                      : 'hover:bg-white/[0.02] border-l-2 border-l-transparent'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-sky-300">
                        {req.id}
                      </span>
                      <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-white/5 text-white/50 border border-white/10">
                        {req.domain}
                      </span>
                    </div>
                    <span
                      className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded ${
                        req.priority === 'critical'
                          ? 'text-rose-300 bg-rose-950/30 border border-rose-800/30'
                          : req.priority === 'high'
                          ? 'text-amber-300 bg-amber-950/30 border border-amber-800/30'
                          : 'text-white/50 bg-white/5 border border-white/10'
                      }`}
                    >
                      {req.priority}
                    </span>
                  </div>

                  <p className="text-xs text-white/85 leading-relaxed font-sans">
                    {req.text}
                  </p>

                  {/* Constraints pills */}
                  {req.constraints && req.constraints.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {req.constraints.map((c, i) => (
                        <span
                          key={i}
                          className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-black/40 text-white/50 border border-white/5"
                        >
                          {c}
                        </span>
                      ))}
                    </div>
                  )}

                  {hasMutation && (
                    <div className="mt-2 text-[10px] font-mono flex items-center gap-1.5 text-amber-400">
                      <ChevronRight className="w-3 h-3" />
                      <span>
                        Mutated in handoff ({mutation?.mutationType})
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Received Agent Handoff (Mutated Context) */}
        <div className="bg-neutral-950/80 rounded border border-amber-900/40 overflow-hidden flex flex-col">
          <div className="px-4 py-3 border-b border-amber-900/30 bg-amber-950/20 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertOctagon className="w-4 h-4 text-amber-400" />
              <h2 className="text-xs font-mono font-medium tracking-wide text-amber-200 uppercase">
                Received Agent Handoff
              </h2>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950/60 border border-amber-800/40 text-amber-300">
              MUTATED PAYLOAD BUNDLE
            </span>
          </div>

          <div className="divide-y divide-white/5 flex-1">
            {/* 1. Mapped Canonical Items */}
            {canonicalRequirements.map((req) => {
              const isSelected = selectedReqId === req.id;
              const mutation = mutationMap.get(req.id);
              const discrepancy = discrepancyMap.get(req.id);

              return (
                <div
                  key={req.id}
                  onClick={() => setSelectedReqId(req.id)}
                  className={`p-3.5 cursor-pointer transition-colors ${
                    isSelected
                      ? 'bg-amber-950/25 border-l-2 border-l-amber-400'
                      : 'hover:bg-white/[0.02] border-l-2 border-l-transparent'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-white/90">
                        {req.id}
                      </span>
                      {mutation ? (
                        <StatusBadge
                          variant={getStatusBadgeVariant(mutation.mutationType)}
                          label={mutation.mutationType.toUpperCase()}
                        />
                      ) : (
                        <StatusBadge variant="passed" label="PRESERVED" />
                      )}
                    </div>

                    {discrepancy && (
                      <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" />
                        <span>Detected</span>
                      </span>
                    )}
                  </div>

                  {/* Mutated Text Content */}
                  {mutation ? (
                    <div className="space-y-1.5">
                      <p
                        className={`text-xs leading-relaxed ${
                          mutation.mutationType === 'missing'
                            ? 'text-rose-400/80 italic font-mono'
                            : mutation.mutationType === 'contradiction'
                            ? 'text-red-300 bg-red-950/20 p-2 rounded border border-red-900/30 font-medium'
                            : 'text-amber-200/90 bg-amber-950/20 p-2 rounded border border-amber-900/20'
                        }`}
                      >
                        {mutation.mutatedText}
                      </p>
                      <div className="text-[11px] text-white/50 font-sans">
                        <span className="text-white/35 font-mono">Shift: </span>
                        {mutation.diffSummary}
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs text-white/70 leading-relaxed font-sans">
                      {req.text}
                    </p>
                  )}
                </div>
              );
            })}

            {/* 2. Added / Unapproved Requirements */}
            {addedMutations.map((added) => {
              const isSelected = selectedReqId === added.targetRequirementId;
              const discrepancy = discrepancyMap.get(added.targetRequirementId);

              return (
                <div
                  key={added.id}
                  onClick={() => setSelectedReqId(added.targetRequirementId)}
                  className={`p-3.5 cursor-pointer bg-purple-950/15 border-l-2 transition-colors ${
                    isSelected ? 'border-l-purple-400 bg-purple-950/30' : 'border-l-purple-600/60'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-purple-300">
                        {added.targetRequirementId}
                      </span>
                      <StatusBadge variant="added" label="INVENTED REQUIREMENT" />
                    </div>
                    {discrepancy && (
                      <span className="text-[10px] font-mono text-purple-400 flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" />
                        <span>Flagged for Rejection</span>
                      </span>
                    )}
                  </div>

                  <p className="text-xs text-purple-200/90 leading-relaxed font-sans bg-purple-950/30 p-2 rounded border border-purple-900/30">
                    {added.mutatedText}
                  </p>
                  <div className="text-[11px] text-white/50 mt-1">
                    <span className="text-white/35 font-mono">Scope violation: </span>
                    {added.diffSummary}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* 3. Deep Discrepancy & Repair Inspector Drawer */}
      {selectedReqId && (
        <div className="bg-neutral-900/90 border border-white/10 rounded p-4 text-xs space-y-3 animate-in fade-in duration-200">
          <div className="flex items-center justify-between border-b border-white/10 pb-2.5">
            <div className="flex items-center gap-2">
              <Info className="w-4 h-4 text-sky-400" />
              <h3 className="font-mono text-xs font-semibold text-white/90">
                DISCREPANCY INSPECTION · {selectedReqId}
              </h3>
              {selectedMutation && (
                <StatusBadge
                  variant={getStatusBadgeVariant(selectedMutation.mutationType)}
                  label={selectedMutation.mutationType.toUpperCase()}
                />
              )}
            </div>
            <button
              type="button"
              onClick={() => setSelectedReqId(null)}
              className="text-white/40 hover:text-white p-1 rounded transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Left: Original Canonical Source */}
            <div className="space-y-1">
              <span className="text-[10px] font-mono uppercase tracking-wider text-sky-400 block">
                Original Canonical Contract
              </span>
              <div className="p-2.5 rounded bg-black/40 border border-white/5 text-white/80 leading-relaxed">
                {selectedCanonical ? (
                  selectedCanonical.text
                ) : (
                  <span className="text-white/40 italic">
                    Not present in canonical specification (Added spec).
                  </span>
                )}
              </div>
            </div>

            {/* Right: Observed in Handoff */}
            <div className="space-y-1">
              <span className="text-[10px] font-mono uppercase tracking-wider text-amber-400 block">
                Observed in Handoff
              </span>
              <div className="p-2.5 rounded bg-black/40 border border-white/5 text-white/80 leading-relaxed">
                {selectedMutation ? (
                  selectedMutation.mutatedText
                ) : (
                  <span className="text-emerald-400 font-mono">
                    Exact match with canonical. No mutation observed.
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Verification Engine Decision & Evidence */}
          {selectedDiscrepancy ? (
            <div className="pt-2 border-t border-white/5 space-y-2">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[11px] font-mono">
                <div>
                  <span className="text-white/40 block">Detection Heuristic:</span>
                  <span className="text-white/80">{selectedDiscrepancy.detectionHeuristic}</span>
                </div>
                <div>
                  <span className="text-white/40 block">Engine Confidence:</span>
                  <span className="text-emerald-400">
                    {(selectedDiscrepancy.detectionConfidence * 100).toFixed(1)}%
                  </span>
                </div>
                <div>
                  <span className="text-white/40 block">Resolution State:</span>
                  <span
                    className={
                      selectedDiscrepancy.repairStatus === 'applied'
                        ? 'text-emerald-400'
                        : 'text-amber-400'
                    }
                  >
                    {selectedDiscrepancy.repairStatus === 'applied'
                      ? 'Auto-Repaired & Verified'
                      : 'Awaiting Human Review'}
                  </span>
                </div>
              </div>

              {/* Proposed Action Note */}
              <div className="p-2 rounded bg-blue-950/20 border border-blue-900/30 flex items-start gap-2">
                <Shield className="w-3.5 h-3.5 text-blue-400 shrink-0 mt-0.5" />
                <div className="text-[11px]">
                  <span className="text-blue-300 font-medium block">
                    Synthesized Repair Action:
                  </span>
                  <span className="text-white/70">
                    {selectedDiscrepancy.proposedRepairText}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-[11px] text-white/50 font-mono pt-1">
              Verification check: Requirement preserved across agent boundary without drift.
            </div>
          )}
        </div>
      )}
    </div>
  );
};
