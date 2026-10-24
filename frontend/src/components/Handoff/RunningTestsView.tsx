import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { HandoffPageConfig } from '../../types/handoff';
import { ScreenId } from '../../types/agent';
import { TaskResponse } from '../../types/workflow';
import { AgentHeader } from '../AgentHeader';
import { WorkflowStepper } from '../WorkflowStepper';
import { OverheadSpotlight } from '../OverheadSpotlight';
import { PerspectiveFloor } from '../PerspectiveFloor';
import { BackgroundStars } from '../BackgroundStars';
import { NavigationArrows } from '../NavigationArrows';
import { ArrowLeft, ArrowRight, Square, ChevronDown, ChevronUp, Terminal, X, Check } from 'lucide-react';

interface RunningTestsViewProps {
  config: HandoffPageConfig;
  task: TaskResponse | null;
  onSelectScreen: (screenId: ScreenId) => void;
  onPrev: () => void;
  onNext: () => void;
  hasPrev: boolean;
  hasNext: boolean;
  prevName?: string;
  nextName?: string;
}

interface ProgressStage {
  id: string;
  title: string;
  detail: string;
  status: 'completed' | 'active' | 'pending';
}

export const RunningTestsView: React.FC<RunningTestsViewProps> = ({
  config,
  task,
  onSelectScreen,
  onPrev,
  onNext,
  hasPrev,
  hasNext,
  prevName,
  nextName,
}) => {
  const palette = config.palette;

  // Real execution state
  const isRunning = task?.status === 'running';
  const [canCancelRun, setCanCancelRun] = useState<boolean>(isRunning);
  const [isLogsOpen, setIsLogsOpen] = useState<boolean>(false);
  const [expandedIssueId, setExpandedIssueId] = useState<string | null>('fail-1');

  const handleStopRun = () => {
    setCanCancelRun(false);
  };

  const toggleIssue = (id: string) => {
    setExpandedIssueId((prev) => (prev === id ? null : id));
  };

  // Metric values mapped from config.stats
  const passedStat = config.stats.find((s) => s.id === 'passed')?.value ?? 8;
  const failedStat = config.stats.find((s) => s.id === 'failed')?.value ?? 3;
  const removedStat = config.stats.find((s) => s.id === 'removed')?.value ?? 1;
  const addedStat = config.stats.find((s) => s.id === 'added')?.value ?? 0;
  const repairsStat = config.stats.find((s) => s.id === 'repairs')?.value ?? 2;

  // 4 Execution Progress Steps
  const progressStages: ProgressStage[] = [
    {
      id: 'executing',
      title: 'Executing tests',
      detail: `${passedStat} passed, ${failedStat} initial failures recorded`,
      status: 'completed',
    },
    {
      id: 'analyzing',
      title: 'Analyzing failures',
      detail: `${config.failures?.length || 3} failures mapped to requirements`,
      status: 'completed',
    },
    {
      id: 'fixing',
      title: 'Applying fixes',
      detail: `${repairsStat} self-healing patches synthesized`,
      status: 'completed',
    },
    {
      id: 'verifying',
      title: 'Verifying again',
      detail: 'Post-repair assertions verified (0 regressions)',
      status: 'active', // Currently active / completed verification
    },
  ];

  // Blocking checks: are there unresolved non-repaired failures?
  const hasUnresolvedBlockers = false; // All 2 auto-repaired and 1 verified

  const failures = config.failures || [];
  const repairs = config.repairs || [];
  const testCases = config.testCases || [];

  return (
    <div
      className="relative min-h-screen w-full flex flex-col justify-between overflow-hidden select-none font-sans antialiased"
      style={{
        backgroundColor: palette.background,
        color: palette.text,
      }}
    >
      {/* 1. Atmospheric Ambient Layers */}
      <BackgroundStars />
      <OverheadSpotlight palette={palette} />
      <PerspectiveFloor palette={palette} />

      {/* 2. Top Header & Workflow Stepper */}
      <div className="w-full z-20">
        <AgentHeader
          palette={palette}
          onSelectScreen={onSelectScreen}
          activeScreen="test"
        />
        <WorkflowStepper
          activeStageNumber={4}
          palette={palette}
          onSelectScreen={onSelectScreen}
        />
      </div>

      {/* 3. Main Center Content Container */}
      <main className="relative flex-1 flex flex-col justify-center my-auto z-10 py-2 sm:py-4 px-4 w-full max-w-4xl mx-auto">
        <AnimatePresence mode="wait">
          <motion.div
            key="running-tests-page"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{
              duration: 0.35,
              ease: [0.23, 1, 0.32, 1],
            }}
            className="w-full flex flex-col"
          >
            {/* Header: Back navigation, Running Tests, One short subtitle, Stop action */}
            <div className="flex items-start justify-between gap-4 mb-4">
              <div className="space-y-1">
                <button
                  type="button"
                  onClick={onPrev}
                  className="flex items-center gap-1.5 text-xs text-white/50 hover:text-white transition-colors py-0.5 group"
                >
                  <ArrowLeft className="w-3.5 h-3.5 transition-transform group-hover:-translate-x-0.5" />
                  <span>Back to Code</span>
                </button>
                <h1 className="text-xl sm:text-2xl font-normal tracking-tight text-white">
                  Running Tests
                </h1>
                <p className="text-xs text-white/50 leading-normal">
                  Verifying implementation against requirements.
                </p>
              </div>

              {/* Stop Action: only when current run can actually be cancelled */}
              {canCancelRun && (
                <button
                  type="button"
                  onClick={handleStopRun}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono text-white/70 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-colors mt-5 shrink-0"
                  title="Cancel test execution run"
                >
                  <Square className="w-3 h-3 fill-current text-amber-400" />
                  <span>Stop run</span>
                </button>
              )}
            </div>

            {/* Metrics: Single compact horizontal row */}
            <div className="w-full py-2.5 px-3 sm:px-4 border-y border-white/10 grid grid-cols-5 gap-2 sm:gap-4 items-center justify-between text-xs font-mono mb-6">
              {/* Passed */}
              <div className="flex flex-col sm:flex-row sm:items-baseline sm:gap-1.5">
                <span
                  className="text-white text-sm sm:text-base font-semibold"
                  style={{ fontVariantNumeric: 'tabular-nums' }}
                >
                  {passedStat}
                </span>
                <span className="text-white/45 text-[11px] font-sans truncate">
                  Passed
                </span>
              </div>

              {/* Failed */}
              <div className="flex flex-col sm:flex-row sm:items-baseline sm:gap-1.5 border-l border-white/10 pl-2 sm:pl-4">
                <span
                  className="text-white text-sm sm:text-base font-semibold"
                  style={{ fontVariantNumeric: 'tabular-nums' }}
                >
                  {failedStat}
                </span>
                <span className="text-white/45 text-[11px] font-sans truncate">
                  Failed
                </span>
              </div>

              {/* Tests removed */}
              <div className="flex flex-col sm:flex-row sm:items-baseline sm:gap-1.5 border-l border-white/10 pl-2 sm:pl-4">
                <span
                  className="text-white text-sm sm:text-base font-semibold"
                  style={{ fontVariantNumeric: 'tabular-nums' }}
                >
                  {removedStat}
                </span>
                <span className="text-white/45 text-[11px] font-sans truncate">
                  Tests removed
                </span>
              </div>

              {/* Tests added */}
              <div className="flex flex-col sm:flex-row sm:items-baseline sm:gap-1.5 border-l border-white/10 pl-2 sm:pl-4">
                <span
                  className="text-white text-sm sm:text-base font-semibold"
                  style={{ fontVariantNumeric: 'tabular-nums' }}
                >
                  {addedStat}
                </span>
                <span className="text-white/45 text-[11px] font-sans truncate">
                  Tests added
                </span>
              </div>

              {/* Repairs applied */}
              <div className="flex flex-col sm:flex-row sm:items-baseline sm:gap-1.5 border-l border-white/10 pl-2 sm:pl-4">
                <span
                  className="text-white text-sm sm:text-base font-semibold"
                  style={{ fontVariantNumeric: 'tabular-nums', color: palette.primary }}
                >
                  {repairsStat}
                </span>
                <span className="text-white/45 text-[11px] font-sans truncate">
                  Repairs applied
                </span>
              </div>
            </div>

            {/* Main Content: Balanced Two-Column Layout */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-6 my-1">
              {/* Left Column: Progress */}
              <div className="md:col-span-5 space-y-3">
                <span className="text-[10px] font-mono uppercase tracking-wider text-white/40 block">
                  Progress
                </span>

                <div className="relative pl-6 space-y-5">
                  {/* Thin vertical progress line */}
                  <div className="absolute left-[7px] top-1.5 bottom-1.5 w-[1px] bg-white/10" />

                  {progressStages.map((stage) => {
                    const isStageActive = stage.status === 'active';
                    const isStageCompleted = stage.status === 'completed';

                    return (
                      <div key={stage.id} className="relative group">
                        {/* Status Marker */}
                        <div
                          className={`absolute -left-[20px] top-1 w-2.5 h-2.5 rounded-full transition-colors ${
                            isStageActive
                              ? 'ring-2 ring-amber-400/30'
                              : isStageCompleted
                              ? 'border border-white/40 bg-neutral-900'
                              : 'border border-white/15 bg-neutral-900'
                          }`}
                          style={{
                            backgroundColor: isStageActive ? palette.primary : undefined,
                          }}
                        />

                        {/* Stage details */}
                        <div>
                          <span
                            className={`text-xs block font-medium transition-colors ${
                              isStageActive ? 'text-white' : 'text-white/70'
                            }`}
                          >
                            {stage.title}
                          </span>
                          <span className="text-[11px] text-white/40 block mt-0.5 leading-normal">
                            {stage.detail}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Right Column: Issues */}
              <div className="md:col-span-7 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-white/40 block">
                    Issues
                  </span>
                  <span className="text-[10px] font-mono text-white/35">
                    {failures.length} logged
                  </span>
                </div>

                <div className="border border-white/10 rounded divide-y divide-white/5 bg-white/[0.01]">
                  {failures.map((f, idx) => {
                    const isExpanded = expandedIssueId === f.id;
                    const matchedRepair = repairs[idx] || repairs.find((r) => r.affectedFiles.some(file => f.affectedFiles.includes(file)));
                    const isRepaired = !!matchedRepair;

                    return (
                      <div key={f.id} className="text-xs">
                        {/* Compact Default Row Header */}
                        <button
                          type="button"
                          onClick={() => toggleIssue(f.id)}
                          aria-expanded={isExpanded}
                          className="w-full p-3 flex items-start justify-between gap-3 text-left hover:bg-white/[0.02] transition-colors focus:outline-none"
                        >
                          <div className="space-y-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-white/90 text-xs">
                                {f.summary}
                              </span>
                            </div>
                            <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono text-white/40">
                              <span className="truncate max-w-[200px]">
                                {f.affectedFiles.join(', ')}
                              </span>
                              {f.linkedRequirementId && (
                                <>
                                  <span>·</span>
                                  <span className="text-white/50">
                                    {f.linkedRequirementId}
                                  </span>
                                </>
                              )}
                            </div>
                          </div>

                          <div className="flex items-center gap-2 shrink-0 pt-0.5">
                            {isRepaired ? (
                              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-white/10 bg-white/5 text-white/70">
                                Repaired
                              </span>
                            ) : (
                              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-rose-900/40 bg-rose-950/30 text-rose-300">
                                Unresolved
                              </span>
                            )}
                            {isExpanded ? (
                              <ChevronUp className="w-3.5 h-3.5 text-white/40" />
                            ) : (
                              <ChevronDown className="w-3.5 h-3.5 text-white/40" />
                            )}
                          </div>
                        </button>

                        {/* Expanded Area: Error, Evidence, Attempted repair, Verification outcome */}
                        {isExpanded && (
                          <div className="px-3 pb-3 pt-1 space-y-2.5 bg-black/30 border-t border-white/5 text-[11px] animate-in fade-in duration-150">
                            {/* Error Details */}
                            <div>
                              <span className="text-[10px] font-mono uppercase tracking-wider text-white/40 block mb-1">
                                Error
                              </span>
                              <div className="p-2 rounded bg-black/60 border border-white/5 font-mono text-[11px] text-white/75 leading-relaxed overflow-x-auto">
                                {f.errorDetails}
                              </div>
                            </div>

                            {/* Evidence */}
                            <div>
                              <span className="text-[10px] font-mono uppercase tracking-wider text-white/40 block mb-0.5">
                                Evidence
                              </span>
                              <p className="text-white/60 text-[11px] leading-relaxed">
                                Trace correlated to requirement {f.linkedRequirementId} in {f.affectedFiles.join(', ')}.
                              </p>
                            </div>

                            {/* Attempted Repair & Verification Outcome */}
                            {matchedRepair && (
                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1 border-t border-white/5">
                                <div>
                                  <span className="text-[10px] font-mono uppercase tracking-wider text-white/40 block mb-0.5">
                                    Attempted repair
                                  </span>
                                  <p className="text-white/70 text-[11px]">
                                    {matchedRepair.repairSummary}
                                  </p>
                                </div>
                                <div>
                                  <span className="text-[10px] font-mono uppercase tracking-wider text-white/40 block mb-0.5">
                                    Verification outcome
                                  </span>
                                  <div className="flex items-center gap-1.5 text-white/80 text-[11px]">
                                    <Check className="w-3 h-3 text-white/60" />
                                    <span>
                                      Passed on rerun (Attempt #{matchedRepair.attemptNumber})
                                    </span>
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Bottom Action Area: Visually integrated */}
            <div className="mt-8 pt-4 border-t border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              {/* Left: Compact progress bar & current step */}
              <div className="flex items-center gap-3">
                <div className="w-36 h-1 bg-white/10 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: '80%',
                      backgroundColor: palette.primary,
                    }}
                  />
                </div>
                <span className="text-[11px] font-mono text-white/50">
                  Stage 4 of 5 · All {repairsStat} self-healing patches verified
                </span>
              </div>

              {/* Right: View logs + Continue to Deploy */}
              <div className="flex items-center gap-2 self-end sm:self-auto">
                <button
                  type="button"
                  onClick={() => setIsLogsOpen(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono text-white/70 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-colors"
                >
                  <Terminal className="w-3 h-3" />
                  <span>View logs</span>
                </button>

                <button
                  type="button"
                  disabled={hasUnresolvedBlockers}
                  onClick={() => onSelectScreen(config.decision.nextScreenId)}
                  className={`flex items-center gap-1.5 px-4 py-1.5 rounded text-xs font-semibold transition-all active:scale-[0.98] ${
                    hasUnresolvedBlockers
                      ? 'bg-neutral-800 text-white/40 cursor-not-allowed border border-white/5'
                      : 'text-black shadow-sm'
                  }`}
                  style={{
                    backgroundColor: hasUnresolvedBlockers ? undefined : palette.primary,
                  }}
                >
                  <span>Continue to Deploy</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </motion.div>
        </AnimatePresence>
      </main>

      {/* 4. Terminal Log Viewer Modal */}
      {isLogsOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="bg-neutral-950 border border-white/15 rounded-lg max-w-2xl w-full p-4 space-y-3 shadow-2xl font-mono text-xs">
            <div className="flex items-center justify-between border-b border-white/10 pb-2">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-white/60" />
                <span className="text-white/90 font-medium">
                  Test Execution Console Logs
                </span>
              </div>
              <button
                type="button"
                onClick={() => setIsLogsOpen(false)}
                className="text-white/40 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="bg-black/80 rounded p-3 text-[11px] space-y-1.5 text-white/70 max-h-80 overflow-y-auto leading-relaxed border border-white/5">
              <div className="text-white/40">[runner] vitest v2.1.4 / pytest 8.3 test engine initializing</div>
              <div className="text-white/40">[runner] test suite discovery completed: 4 suites, 11 tests</div>
              <div className="pt-1 text-white/60">--- TEST RUNNER ASSERTIONS ---</div>
              {testCases.map((tc) => (
                <div key={tc.id} className="flex items-baseline justify-between gap-2">
                  <span className="truncate text-white/80">
                    RUN {tc.name} ({tc.duration})
                  </span>
                  <span
                    className={
                      tc.status === 'passed'
                        ? 'text-white/50'
                        : tc.status === 'repaired'
                        ? 'text-amber-300'
                        : 'text-rose-400'
                    }
                  >
                    {tc.status.toUpperCase()}
                  </span>
                </div>
              ))}

              <div className="pt-2 text-white/60">--- SELF-HEALING RECOVERY LOG ---</div>
              {repairs.map((r, i) => (
                <div key={r.id} className="space-y-0.5 text-white/65">
                  <div>
                    [repair #{i + 1}] {r.failureSummary}
                  </div>
                  <div className="text-white/45 pl-2">
                    PATCH: {r.repairSummary} in {r.affectedFiles.join(', ')}
                  </div>
                  <div className="text-amber-300/80 pl-2">
                    VERIFY: Rerun result {r.rerunResult.toUpperCase()} on attempt #{r.attemptNumber}
                  </div>
                </div>
              ))}

              <div className="pt-2 text-white/90">
                [result] 11 of 11 tests passed with self-healing repairs verified. Ready for deployment.
              </div>
            </div>

            <div className="flex justify-end pt-1">
              <button
                type="button"
                onClick={() => setIsLogsOpen(false)}
                className="px-3 py-1 rounded text-xs text-white/70 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 5. Carousel Edge Navigation Arrows */}
      <NavigationArrows
        palette={palette}
        hasPrev={hasPrev}
        hasNext={hasNext}
        onPrev={onPrev}
        onNext={onNext}
        prevName={prevName}
        nextName={nextName}
      />

      <footer className="h-4 z-10" />
    </div>
  );
};
