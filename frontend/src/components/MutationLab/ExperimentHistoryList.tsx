import React from 'react';
import { ExperimentResult } from '../../types/mutationLab';
import { History, RotateCcw, CheckCircle2, AlertTriangle } from 'lucide-react';

interface ExperimentHistoryListProps {
  history: ExperimentResult[];
  onSelectExperiment: (exp: ExperimentResult) => void;
  activeExperimentId?: string;
}

export const ExperimentHistoryList: React.FC<ExperimentHistoryListProps> = ({
  history,
  onSelectExperiment,
  activeExperimentId,
}) => {
  return (
    <div className="bg-neutral-950/80 rounded border border-white/10 overflow-hidden">
      <div className="px-4 py-3 border-b border-white/10 bg-white/[0.02] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-sky-400" />
          <h2 className="text-xs font-mono font-medium tracking-wide text-white/90 uppercase">
            Experiment History & Benchmarks
          </h2>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 border border-white/10 text-white/50">
          SESSION STORAGE · LOCALLY EVALUATED
        </span>
      </div>

      <div className="divide-y divide-white/5 max-h-72 overflow-y-auto">
        {history.length === 0 ? (
          <div className="p-6 text-center text-white/40 font-mono text-xs">
            No previous experiments recorded in this session.
          </div>
        ) : (
          history.map((exp) => {
            const isActive = activeExperimentId === exp.config.id;
            const dateStr = new Date(exp.timestamp).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
            });

            return (
              <div
                key={exp.config.id + exp.timestamp}
                className={`p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-colors ${
                  isActive ? 'bg-blue-950/20 border-l-2 border-l-sky-400' : 'hover:bg-white/[0.02]'
                }`}
              >
                <div className="space-y-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-semibold text-white/90 truncate">
                      {exp.config.name}
                    </span>
                    <span className="text-[10px] font-mono text-white/40">
                      {dateStr}
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 text-[11px] text-white/50 font-mono">
                    <span>Source: {exp.config.sourceTaskId}</span>
                    <span>·</span>
                    <span>Intensity: {exp.config.intensity}</span>
                    <span>·</span>
                    <span>{exp.mutations.length} mutations</span>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  {/* Preservation Result */}
                  <div className="text-right">
                    <span className="text-[10px] font-mono text-white/40 block leading-tight">
                      Preservation
                    </span>
                    <span
                      className="text-sm font-mono font-bold"
                      style={{
                        color: exp.preservationRate >= 90 ? '#34D399' : '#FBBF24',
                        fontVariantNumeric: 'tabular-nums',
                      }}
                    >
                      {exp.preservationRate}%
                    </span>
                  </div>

                  {/* Status */}
                  <div>
                    {exp.status === 'completed' ? (
                      <span className="flex items-center gap-1 text-[10px] font-mono text-emerald-400 bg-emerald-950/40 border border-emerald-800/40 px-2 py-0.5 rounded">
                        <CheckCircle2 className="w-3 h-3" />
                        Complete
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-[10px] font-mono text-amber-300 bg-amber-950/40 border border-amber-800/40 px-2 py-0.5 rounded">
                        <AlertTriangle className="w-3 h-3" />
                        Review
                      </span>
                    )}
                  </div>

                  {/* Reopen Button */}
                  <button
                    type="button"
                    onClick={() => onSelectExperiment(exp)}
                    className="flex items-center gap-1 px-2.5 py-1 rounded text-xs font-mono text-white/80 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-colors"
                  >
                    <RotateCcw className="w-3 h-3" />
                    <span>Reopen</span>
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
