import React, { useState } from 'react';
import { ExperimentResult } from '../../types/mutationLab';
import { Download, ChevronDown, ChevronUp, FileCode, CheckCircle2, AlertTriangle, ShieldCheck } from 'lucide-react';

interface AuditTrailAndExportProps {
  experiment: ExperimentResult;
}

export const AuditTrailAndExport: React.FC<AuditTrailAndExportProps> = ({
  experiment,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  const handleExportJson = () => {
    const dataStr =
      'data:text/json;charset=utf-8,' +
      encodeURIComponent(JSON.stringify(experiment, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    const safeId = experiment.config.id.toLowerCase().replace(/[^a-z0-9_-]/g, '-');
    downloadAnchor.setAttribute(
      'download',
      `handoffiq-mutation-lab-${safeId}-${Date.now()}.json`
    );
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="bg-neutral-950/80 rounded border border-white/10 overflow-hidden">
      {/* Bar with toggle and export action */}
      <div className="px-4 py-3 border-b border-white/10 bg-white/[0.02] flex items-center justify-between">
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-2 text-xs font-mono text-white/90 hover:text-white uppercase transition-colors"
        >
          <FileCode className="w-4 h-4 text-sky-400" />
          <span>Experiment Audit Trail & Forensic Trace</span>
          {isOpen ? (
            <ChevronUp className="w-3.5 h-3.5 text-white/40" />
          ) : (
            <ChevronDown className="w-3.5 h-3.5 text-white/40" />
          )}
        </button>

        <button
          type="button"
          onClick={handleExportJson}
          className="flex items-center gap-1.5 px-3 py-1 rounded text-xs font-medium text-white/90 hover:text-white bg-blue-600/30 hover:bg-blue-600/50 border border-blue-500/40 transition-colors shadow-sm"
          title="Download full forensic evaluation data as JSON"
        >
          <Download className="w-3.5 h-3.5" />
          <span>Export Report (JSON)</span>
        </button>
      </div>

      {/* Expanded Audit Log & Contract Details */}
      {isOpen && (
        <div className="p-4 space-y-4 animate-in fade-in duration-200 text-xs">
          {/* Step-by-step pipeline */}
          <div className="space-y-2">
            <span className="text-[10px] font-mono uppercase tracking-wider text-white/40 block">
              EXECUTION PIPELINE MILESTONES:
            </span>
            <div className="space-y-1.5 font-mono">
              {experiment.auditTrail.map((step, idx) => (
                <div
                  key={idx}
                  className="p-2.5 rounded bg-black/40 border border-white/5 flex items-start justify-between gap-3"
                >
                  <div className="flex items-start gap-2.5">
                    {step.status === 'passed' && (
                      <CheckCircle2 className="w-3.5 h-3.5 text-sky-400 shrink-0 mt-0.5" />
                    )}
                    {step.status === 'warning' && (
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                    )}
                    {step.status === 'repaired' && (
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                    )}

                    <div>
                      <span className="text-white/90 font-medium block">
                        {step.step}
                      </span>
                      <span className="text-[11px] text-white/50 block font-sans">
                        {step.detail}
                      </span>
                    </div>
                  </div>

                  <span className="text-[10px] text-white/40 shrink-0">
                    {step.timestamp}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Configuration Parameters Trace */}
          <div className="pt-2 border-t border-white/5">
            <span className="text-[10px] font-mono uppercase tracking-wider text-white/40 block mb-1.5">
              FORENSIC METADATA:
            </span>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono p-2.5 rounded bg-black/30 border border-white/5">
              <div>
                <span className="text-white/40 block">Experiment ID:</span>
                <span className="text-white/80">{experiment.config.id}</span>
              </div>
              <div>
                <span className="text-white/40 block">Target Source:</span>
                <span className="text-white/80">{experiment.config.sourceTaskId}</span>
              </div>
              <div>
                <span className="text-white/40 block">Strategy:</span>
                <span className="text-white/80">{experiment.config.strategy}</span>
              </div>
              <div>
                <span className="text-white/40 block">Evaluator Model:</span>
                <span className="text-emerald-400">Deterministic HandoffIQ V1.4</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
