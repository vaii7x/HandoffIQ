import React, { useState, useEffect } from 'react';
import { ScreenId, AgentPalette } from '../../types/agent';
import {
  ExperimentConfig,
  ExperimentResult,
} from '../../types/mutationLab';
import { MutationEngine } from '../../services/mutationEngine';
import { MutationLabHeader } from './MutationLabHeader';
import { ExperimentConfigBar } from './ExperimentConfigBar';
import { HandoffSideBySideComparison } from './HandoffSideBySideComparison';
import { DetectionRepairPanel } from './DetectionRepairPanel';
import { BaselineComparisonView } from './BaselineComparisonView';
import { ExperimentHistoryList } from './ExperimentHistoryList';
import { AuditTrailAndExport } from './AuditTrailAndExport';
import { PerspectiveFloor } from '../PerspectiveFloor';
import { BackgroundStars } from '../BackgroundStars';
import { OverheadSpotlight } from '../OverheadSpotlight';
import { AlertTriangle, FlaskConical } from 'lucide-react';

interface MutationLabPageProps {
  onSelectScreen: (screenId: ScreenId) => void;
  palette?: AgentPalette;
}

const DEFAULT_PALETTE: AgentPalette = {
  id: 'research',
  background: '#050A12',
  primary: '#78BFFF',
  secondary: '#377FEA',
  text: '#F4F7FC',
  muted: '#8D9BB0',
  glow: 'rgba(120, 191, 255, 0.45)',
  threeColorPrimary: 0x78bfff,
  threeColorSecondary: 0x377fea,
  threeColorGlow: 0x88ccff,
};

export const MutationLabPage: React.FC<MutationLabPageProps> = ({
  onSelectScreen,
  palette = DEFAULT_PALETTE,
}) => {
  // Load pre-seeded history
  const [history, setHistory] = useState<ExperimentResult[]>(() => {
    return MutationEngine.getInitialHistory();
  });

  const [currentExperiment, setCurrentExperiment] = useState<ExperimentResult>(
    () => history[0]
  );

  const [config, setConfig] = useState<ExperimentConfig>(() => ({
    id: `EXP-${Date.now().toString().slice(-4)}`,
    name: 'EXP-4401: Distributed WebGL & Auth Mutation',
    sourceTaskId: 'TASK-4401',
    strategy: 'balanced_blend',
    intensity: 'moderate',
    mutationCount: 3,
    enabledMutationTypes: ['missing', 'altered', 'weakened'],
  }));

  const [isDirty, setIsDirty] = useState<boolean>(false);
  const [showDiscardModal, setShowDiscardModal] = useState<boolean>(false);
  const [isRunning, setIsRunning] = useState<boolean>(false);

  // Sync config when task source changes
  const handleSelectTask = (taskId: string) => {
    if (isDirty) {
      if (
        !window.confirm(
          'Switching task source will reset unsaved experiment configurations. Continue?'
        )
      ) {
        return;
      }
    }
    const newConfig: ExperimentConfig = {
      ...config,
      sourceTaskId: taskId,
      name: `EXP-${taskId.replace('TASK-', '')}: Handoff Integrity Stress Test`,
    };
    setConfig(newConfig);
    setIsDirty(false);

    // Auto-run evaluation for the newly selected task
    const result = MutationEngine.runExperiment(newConfig);
    setCurrentExperiment(result);
  };

  const handleConfigChange = (updated: Partial<ExperimentConfig>) => {
    setConfig((prev) => ({ ...prev, ...updated }));
    setIsDirty(true);
  };

  const handleRunExperiment = () => {
    setIsRunning(true);
    setTimeout(() => {
      const result = MutationEngine.runExperiment(config);
      setCurrentExperiment(result);
      setHistory((prev) => [result, ...prev.slice(0, 9)]);
      setIsRunning(false);
      setIsDirty(false);
    }, 450);
  };

  const handleNewExperiment = () => {
    if (isDirty) {
      setShowDiscardModal(true);
    } else {
      resetToNewExperiment();
    }
  };

  const resetToNewExperiment = () => {
    const freshId = `EXP-${Math.floor(1000 + Math.random() * 9000)}`;
    const freshConfig: ExperimentConfig = {
      id: freshId,
      name: `${freshId}: New Mutation Stress Test`,
      sourceTaskId: config.sourceTaskId,
      strategy: 'balanced_blend',
      intensity: 'subtle',
      mutationCount: 2,
      enabledMutationTypes: ['missing', 'altered'],
    };
    setConfig(freshConfig);
    setIsDirty(false);
    setShowDiscardModal(false);

    const result = MutationEngine.runExperiment(freshConfig);
    setCurrentExperiment(result);
  };

  const handleSelectFromHistory = (exp: ExperimentResult) => {
    setCurrentExperiment(exp);
    setConfig(exp.config);
    setIsDirty(false);
  };

  // Scroll to top on mount
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  return (
    <div className="relative min-h-screen bg-[#050A12] text-white flex flex-col antialiased selection:bg-blue-500/30 selection:text-white">
      {/* Ambient background layers */}
      <BackgroundStars />
      <PerspectiveFloor palette={palette} />
      <OverheadSpotlight palette={palette} />

      {/* 1. Header */}
      <MutationLabHeader
        selectedTaskId={config.sourceTaskId}
        onSelectTask={handleSelectTask}
        onSelectScreen={onSelectScreen}
        status={isRunning ? 'running' : currentExperiment.status}
        onNewExperiment={handleNewExperiment}
      />

      {/* 2. Experiment Configuration Bar */}
      <ExperimentConfigBar
        config={config}
        onChange={handleConfigChange}
        onRun={handleRunExperiment}
        isRunning={isRunning}
      />

      {/* 3. Main Content Container */}
      <main className="relative z-10 flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-8">
        {/* Banner: Experiment Workbench Overview */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-white/10">
          <div className="flex items-center gap-2">
            <FlaskConical className="w-4 h-4 text-amber-400" />
            <h2 className="text-sm font-mono font-medium text-white/90 uppercase tracking-wider">
              Active Evaluation: {currentExperiment.config.name}
            </h2>
          </div>

          <div className="flex items-center gap-3 text-xs font-mono text-white/50">
            <span>Strategy: {currentExperiment.config.strategy}</span>
            <span>·</span>
            <span className="text-amber-300">
              {currentExperiment.mutations.length} Injected Mutations
            </span>
          </div>
        </div>

        {/* 4. Centerpiece: Side-by-Side Canonical vs Mutated Handoff */}
        <section aria-labelledby="side-by-side-heading">
          <HandoffSideBySideComparison
            canonicalRequirements={currentExperiment.canonicalRequirements}
            mutations={currentExperiment.mutations}
            detectedDiscrepancies={currentExperiment.detectedDiscrepancies}
          />
        </section>

        {/* 5. Detection & Automated Repair Panel */}
        <section aria-labelledby="results-panel-heading">
          <DetectionRepairPanel
            preservationRate={currentExperiment.preservationRate}
            detectedDiscrepancies={currentExperiment.detectedDiscrepancies}
            totalCanonicalCount={currentExperiment.canonicalRequirements.length}
            status={currentExperiment.status}
          />
        </section>

        {/* 6. Baseline Comparison: Without vs With HandoffIQ */}
        <section aria-labelledby="baseline-comparison-heading">
          <BaselineComparisonView baseline={currentExperiment.baseline} />
        </section>

        {/* 7. Audit Trail & JSON Export */}
        <section aria-labelledby="audit-trail-heading">
          <AuditTrailAndExport experiment={currentExperiment} />
        </section>

        {/* 8. Experiment History */}
        <section aria-labelledby="experiment-history-heading">
          <ExperimentHistoryList
            history={history}
            onSelectExperiment={handleSelectFromHistory}
            activeExperimentId={currentExperiment.config.id}
          />
        </section>
      </main>

      {/* Discard Confirmation Modal */}
      {showDiscardModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="bg-neutral-900 border border-white/15 rounded-lg max-w-sm w-full p-5 space-y-4 shadow-2xl">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-amber-950/60 border border-amber-800/40 flex items-center justify-center shrink-0">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">
                  Discard Unsaved Changes?
                </h3>
                <p className="text-xs text-white/50 mt-0.5">
                  You have modified mutation settings that haven't been evaluated.
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/10 text-xs font-medium">
              <button
                type="button"
                onClick={() => setShowDiscardModal(false)}
                className="px-3 py-1.5 rounded text-white/70 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={resetToNewExperiment}
                className="px-3 py-1.5 rounded text-white bg-rose-600 hover:bg-rose-500 transition-colors"
              >
                Discard & Reset
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
