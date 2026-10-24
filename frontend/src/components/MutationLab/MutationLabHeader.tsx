import React from 'react';
import { ArrowLeft, PlusCircle, AlertTriangle, CheckCircle2, Clock } from 'lucide-react';
import { ScreenId } from '../../types/agent';
import { CANONICAL_TASK_SOURCES, TaskSourceOption } from '../../services/mutationEngine';

interface MutationLabHeaderProps {
  selectedTaskId: string;
  onSelectTask: (taskId: string) => void;
  onSelectScreen: (screenId: ScreenId) => void;
  status: 'idle' | 'running' | 'completed' | 'awaiting_review';
  onNewExperiment: () => void;
}

export const MutationLabHeader: React.FC<MutationLabHeaderProps> = ({
  selectedTaskId,
  onSelectTask,
  onSelectScreen,
  status,
  onNewExperiment,
}) => {
  return (
    <header className="border-b border-white/10 bg-black/40 backdrop-blur-md sticky top-0 z-30 px-4 py-3 sm:px-6">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Left: Return to Workflow + Branding */}
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={() => onSelectScreen('research')}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono text-white/70 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-colors"
            title="Return to 5-stage agent workflow"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Workflow</span>
          </button>

          <div className="h-4 w-[1px] bg-white/10 hidden sm:block" />

          <div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono tracking-[0.25em] text-white/40 uppercase">
                HANDOFFIQ
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                LAB
              </span>
            </div>
            <h1 className="text-base sm:text-lg font-medium text-white tracking-tight flex items-center gap-2">
              Handoff Mutation Lab
            </h1>
            <p className="text-[11px] text-white/50 hidden sm:block">
              Break the handoff. Measure what survives.
            </p>
          </div>
        </div>

        {/* Center / Right: Task Selector, Status Badge, New Experiment */}
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          {/* Canonical Task / Source Selector */}
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-white/40 font-mono text-[11px] hidden lg:inline">Source:</span>
            <select
              value={selectedTaskId}
              onChange={(e) => onSelectTask(e.target.value)}
              className="bg-neutral-900 border border-white/15 text-white/90 text-xs rounded px-2.5 py-1 focus:outline-none focus:border-blue-400 font-mono max-w-[260px] truncate"
            >
              {CANONICAL_TASK_SOURCES.map((source: TaskSourceOption) => (
                <option key={source.taskId} value={source.taskId}>
                  {source.taskId} · {source.name.split(':')[1]?.trim() || source.name}
                </option>
              ))}
            </select>
          </div>

          {/* Status Indicator */}
          <div className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono border">
            {status === 'running' && (
              <span className="flex items-center gap-1 text-sky-300 bg-sky-950/40 border-sky-800/40 px-1.5 py-0.5 rounded border">
                <Clock className="w-3 h-3 animate-spin" />
                Simulating
              </span>
            )}
            {status === 'completed' && (
              <span className="flex items-center gap-1 text-emerald-300 bg-emerald-950/40 border-emerald-800/40 px-1.5 py-0.5 rounded border">
                <CheckCircle2 className="w-3 h-3" />
                Validated
              </span>
            )}
            {status === 'awaiting_review' && (
              <span className="flex items-center gap-1 text-amber-300 bg-amber-950/40 border-amber-800/40 px-1.5 py-0.5 rounded border">
                <AlertTriangle className="w-3 h-3" />
                Review Needed
              </span>
            )}
            {status === 'idle' && (
              <span className="text-white/50 bg-white/5 border-white/10 px-1.5 py-0.5 rounded border">
                Workbench Idle
              </span>
            )}
          </div>

          {/* New Experiment Button */}
          <button
            type="button"
            onClick={onNewExperiment}
            className="flex items-center gap-1.5 px-3 py-1 rounded text-xs font-medium text-white/90 hover:text-white bg-white/10 hover:bg-white/15 border border-white/20 transition-all active:scale-[0.98]"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>New Experiment</span>
          </button>
        </div>
      </div>
    </header>
  );
};
