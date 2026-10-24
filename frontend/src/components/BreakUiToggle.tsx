import React, { useState } from 'react';
import { ShieldAlert, RefreshCw, Cpu, Server, FlaskConical } from 'lucide-react';

interface BreakUiToggleProps {
  isWorstCase: boolean;
  onToggleWorstCase: (val: boolean) => void;
  isMockMode: boolean;
  onToggleMockMode: (val: boolean) => void;
  onResetSimulation: () => void;
  onNewGoal?: () => void;
  onOpenLab?: () => void;
}

export const BreakUiToggle: React.FC<BreakUiToggleProps> = ({
  isWorstCase,
  onToggleWorstCase,
  isMockMode,
  onToggleMockMode,
  onResetSimulation,
  onNewGoal,
  onOpenLab,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <aside
      aria-label="Developer & Testing Bar"
      className="fixed bottom-3 right-3 z-40 flex flex-col items-end gap-1.5"
    >
      {isOpen && (
        <div
          className="bg-neutral-900/90 text-neutral-200 border border-white/10 p-2.5 rounded-lg shadow-2xl backdrop-blur-md text-xs flex flex-col gap-2 max-w-xs animate-in fade-in slide-in-from-bottom-2 duration-200"
        >
          <div className="font-semibold text-white/90 border-b border-white/10 pb-1 flex items-center justify-between">
            <span>Dev & Adversarial QA</span>
            <span className="text-[10px] text-white/50 font-mono">break-ui</span>
          </div>

          {/* Break-UI Dataset Segmented Toggle */}
          <div className="flex flex-col gap-1">
            <span className="text-[10px] text-neutral-400">Data Boundary Mode</span>
            <div className="grid grid-cols-2 bg-neutral-800 p-0.5 rounded border border-white/5">
              <button
                type="button"
                onClick={() => onToggleWorstCase(false)}
                className={`py-1 px-2 rounded text-[11px] font-medium transition-colors ${
                  !isWorstCase
                    ? 'bg-neutral-700 text-white shadow-sm'
                    : 'text-neutral-400 hover:text-white'
                }`}
              >
                Demo data
              </button>
              <button
                type="button"
                onClick={() => onToggleWorstCase(true)}
                className={`py-1 px-2 rounded text-[11px] font-medium transition-colors ${
                  isWorstCase
                    ? 'bg-amber-600 text-white shadow-sm'
                    : 'text-neutral-400 hover:text-white'
                }`}
              >
                Worst case
              </button>
            </div>
          </div>

          {/* Backend Connection Adapter Mode */}
          <div className="flex flex-col gap-1">
            <span className="text-[10px] text-neutral-400">Backend Adapter</span>
            <div className="grid grid-cols-2 bg-neutral-800 p-0.5 rounded border border-white/5">
              <button
                type="button"
                onClick={() => onToggleMockMode(true)}
                className={`py-1 px-2 rounded text-[11px] font-medium transition-colors flex items-center justify-center gap-1 ${
                  isMockMode
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-neutral-400 hover:text-white'
                }`}
              >
                <Cpu className="w-3 h-3" /> Mock Sim
              </button>
              <button
                type="button"
                onClick={() => onToggleMockMode(false)}
                className={`py-1 px-2 rounded text-[11px] font-medium transition-colors flex items-center justify-center gap-1 ${
                  !isMockMode
                    ? 'bg-emerald-600 text-white shadow-sm'
                    : 'text-neutral-400 hover:text-white'
                }`}
              >
                <Server className="w-3 h-3" /> Live API
              </button>
            </div>
          </div>

          {/* Action Reset */}
          <button
            type="button"
            onClick={onResetSimulation}
            className="w-full mt-0.5 py-1 px-2 rounded bg-white/5 hover:bg-white/10 text-white/80 border border-white/10 text-[11px] flex items-center justify-center gap-1.5 transition-colors"
          >
            <RefreshCw className="w-3 h-3" /> Cycle Status Phrases
          </button>

          {/* New Workflow Entry */}
          {onNewGoal && (
            <button
              type="button"
              onClick={onNewGoal}
              className="w-full py-1 px-2 rounded bg-blue-500/10 hover:bg-blue-500/20 text-blue-300 border border-blue-500/30 text-[11px] flex items-center justify-center gap-1.5 transition-colors"
            >
              Start New Workflow (Input Page)
            </button>
          )}

          {/* Mutation Lab Direct Link */}
          {onOpenLab && (
            <button
              type="button"
              onClick={onOpenLab}
              className="w-full py-1 px-2 rounded bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[11px] flex items-center justify-center gap-1.5 transition-colors"
            >
              <FlaskConical className="w-3 h-3" /> Open Mutation Lab
            </button>
          )}
        </div>
      )}

      {/* Floating Pill Toggle Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="px-2.5 py-1 rounded-full bg-neutral-900/80 hover:bg-neutral-800 border border-white/15 text-white/70 hover:text-white text-[11px] flex items-center gap-1.5 backdrop-blur-md shadow-lg transition-transform active:scale-95"
      >
        <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
        <span>{isWorstCase ? 'Worst-Case Active' : 'Dev Controls'}</span>
      </button>
    </aside>
  );
};
