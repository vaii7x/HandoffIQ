import React, { useState, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { HandoffPageConfig } from '../../types/handoff';
import { ScreenId } from '../../types/agent';
import { AgentHeader } from '../AgentHeader';
import { WorkflowStepper } from '../WorkflowStepper';
import { OverheadSpotlight } from '../OverheadSpotlight';
import { PerspectiveFloor } from '../PerspectiveFloor';
import { BackgroundStars } from '../BackgroundStars';
import { HandoffStatistics } from './HandoffStatistics';
import { WorkflowCheckRow } from './WorkflowCheckRow';
import { ExpandableValidationDetails } from './ExpandableValidationDetails';
import { HandoffDecision } from './HandoffDecision';
import { HandoffProgress } from './HandoffProgress';
import { RunningTestsView } from './RunningTestsView';
import { TaskResponse } from '../../types/workflow';
import { apiService } from '../../services/api';
import { computeAuthoritativeValidation } from '../../utils/validationSummary';

interface HandoffPageProps {
  config: HandoffPageConfig;
  task: TaskResponse | null;
  onSelectScreen: (screenId: ScreenId) => void;
  onPrev: () => void;
  onNext: () => void;
  hasPrev: boolean;
  hasNext: boolean;
  prevName?: string;
  nextName?: string;
  hideChrome?: boolean;
  hideBackground?: boolean;
}

export const HandoffPage: React.FC<HandoffPageProps> = ({
  config,
  task,
  onSelectScreen,
  onPrev,
  onNext,
  hasPrev,
  hasNext,
  prevName,
  nextName,
  hideChrome = false,
  hideBackground = false,
}) => {
  // If rendering stage 4 (Running Tests / Coding to Deploy), use the refined minimalist developer interface
  if (config.id === 'test') {
    return (
      <RunningTestsView
        config={config}
        task={task}
        onSelectScreen={onSelectScreen}
        onPrev={onPrev}
        onNext={onNext}
        hasPrev={hasPrev}
        hasNext={hasNext}
        prevName={prevName}
        nextName={nextName}
        hideChrome={hideChrome}
        hideBackground={hideBackground}
      />
    );
  }

  const palette = config.palette;

  // Track task ID to reset state synchronously on task change
  const [currentTaskId, setCurrentTaskId] = useState<string>(task?.taskId || '');
  const [rawHandoffIssues, setRawHandoffIssues] = useState<any[] | null>(null);
  const [loadingHandoff, setLoadingHandoff] = useState<boolean>(true);

  if (task?.taskId && task.taskId !== currentTaskId) {
    setCurrentTaskId(task.taskId);
    setRawHandoffIssues(null);
    setLoadingHandoff(true);
  }

  // Fetch real backend validation issues if available
  useEffect(() => {
    let isSubscribed = true;
    const activeId = task?.taskId;
    if (!activeId || config.id !== 'validate') {
      setLoadingHandoff(false);
      return;
    }

    setLoadingHandoff(true);

    apiService
      .getHandoffs(activeId)
      .then((res) => {
        if (!isSubscribed) return;
        const handoffs = res?.handoffs || [];
        if (handoffs.length > 0) {
          const latest = handoffs[handoffs.length - 1];
          setRawHandoffIssues(Array.isArray(latest.issues) ? latest.issues : []);
        } else {
          setRawHandoffIssues([]);
        }
      })
      .catch((err) => {
        console.warn('Could not fetch handoffs:', err);
        if (isSubscribed) setRawHandoffIssues([]);
      })
      .finally(() => {
        if (isSubscribed) setLoadingHandoff(false);
      });

    return () => {
      isSubscribed = false;
    };
  }, [task?.taskId, config.id]);

  // Single Authoritative Validation Result: every metric, message, status, and progress indicator derives from this!
  const valResult = useMemo(() => {
    return computeAuthoritativeValidation({
      canonicalRequirements: task?.requirements || [],
      rawIssues: rawHandoffIssues || [],
      isLoading: loadingHandoff,
      taskRequest: task?.originalRequirement || '',
    });
  }, [task?.requirements, rawHandoffIssues, loadingHandoff, task?.originalRequirement]);

  // Single expanded row state: defaults to discrepancy list
  const [expandedRowId, setExpandedRowId] = useState<string | null>('req_comparison');

  const toggleRow = (id: string) => {
    setExpandedRowId((prev) => (prev === id ? null : id));
  };

  const progressPercent = (config.stageNumber / 5) * 100;

  // Dynamically constructed check rows using authoritative validation results
  const dynamicCheckRows = useMemo(() => {
    return [
      {
        id: 'req_comparison',
        title: 'Comparing original and received requirements',
        supportingDetail: valResult.reqComparisonSupportingDetail,
        status: (valResult.isLoading ? 'running' : 'completed') as any,
        statusText: valResult.reqComparisonStatusText,
        kind: 'discrepancy_list' as const,
      },
      {
        id: 'constraints_risks',
        title: 'Validating constraints and risks',
        supportingDetail: valResult.constraintsRisksSupportingDetail,
        status: (valResult.isLoading ? 'running' : 'completed') as any,
        statusText: valResult.constraintsRisksStatusText,
        kind: 'constraint_risks' as const,
      },
    ];
  }, [valResult]);

  const effectiveDecision = useMemo(
    () => ({
      ...config.decision,
      label: valResult.hasUnresolvedBlockers ? 'Clarification Required' : 'Ready for coding',
      description: valResult.hasUnresolvedBlockers
        ? `${valResult.totalUnresolved} unresolved discrepancy requires review before proceeding to code generation.`
        : valResult.totalRepaired > 0
        ? `${valResult.totalRepaired} requirement discrepancy resolved with automated repair. Specifications reconciled.`
        : 'All canonical requirements verified compliant. Ready for code generation.',
      isBlocked: valResult.hasUnresolvedBlockers,
    }),
    [config.decision, valResult]
  );

  const validationContent = (
    <div className="w-full max-w-4xl mx-auto flex flex-col items-center">
      {/* Centered Eyebrow & Heading */}
      <div className="text-center max-w-xl mx-auto mb-4">
        <div
          className="text-[11px] sm:text-xs font-semibold tracking-[0.24em] uppercase transition-colors duration-500"
          style={{ color: palette.muted }}
        >
          {config.eyebrow}
        </div>
        <h2 className="text-2xl sm:text-3xl md:text-4xl font-semibold tracking-tight text-[#171A35] mt-1.5">
          {config.heading}
        </h2>
      </div>

      {/* 4. Top Statistics Pills Bar (Unified Authoritative Metrics) */}
      <HandoffStatistics stats={valResult.stats} palette={palette} />

      {/* 5. Validation Check Rows Container (Dynamic real findings) */}
      <div className="w-full max-w-3xl mx-auto mt-4 space-y-2.5">
        {dynamicCheckRows.map((check) => (
          <WorkflowCheckRow
            key={check.id}
            check={check}
            isExpanded={expandedRowId === check.id}
            onToggle={() => toggleRow(check.id)}
            palette={palette}
          >
            {check.kind === 'discrepancy_list' ? (
              valResult.isLoading ? (
                <div className="p-4 text-xs font-mono text-[#737895] text-center">
                  Loading verification data for active task...
                </div>
              ) : valResult.totalDetected === 0 ? (
                <div className="p-4 text-xs font-mono text-[#7664E8] text-center">
                  All {valResult.canonicalCount} canonical requirements verified compliant. No discrepancies detected.
                </div>
              ) : (
                <ExpandableValidationDetails
                  kind="discrepancy_list"
                  discrepancies={valResult.discrepancies}
                  palette={palette}
                />
              )
            ) : (
              <ExpandableValidationDetails
                kind="constraint_risks"
                discrepancies={valResult.discrepancies}
                palette={palette}
              />
            )}
          </WorkflowCheckRow>
        ))}
      </div>

      {/* 6. Handoff Decision Banner & Action */}
      <HandoffDecision
        decision={effectiveDecision}
        palette={palette}
        onContinue={() => onSelectScreen(config.decision.nextScreenId)}
        discrepancies={valResult.discrepancies}
      />

      {/* 7. Bottom Progress Area (Authoritative Truthful Progression) */}
      <HandoffProgress
        stageFraction={config.fractionText}
        progressPercent={progressPercent}
        statusText={valResult.progressStatusText}
        palette={palette}
      />
    </div>
  );

  if (hideChrome) {
    return (
      <div className="w-full flex-1 flex flex-col items-center justify-center my-auto z-10 py-2 sm:py-4 px-2 sm:px-4 select-none">
        {validationContent}
      </div>
    );
  }

  return (
    <div
      className="relative min-h-screen w-full flex flex-col justify-between overflow-hidden transition-colors duration-700 ease-out select-none"
      style={{
        backgroundColor: palette.background,
        color: palette.text,
      }}
    >
      {/* 1. Ambient Background Atmosphere */}
      {!hideBackground && (
        <>
          <BackgroundStars />
          <OverheadSpotlight palette={palette} />
          <PerspectiveFloor palette={palette} />
        </>
      )}

      {/* 2. Top Header & Workflow Stepper */}
      <div className="w-full z-20">
        <AgentHeader
          palette={palette}
          onSelectScreen={onSelectScreen}
          activeScreen={config.id}
        />
        <WorkflowStepper
          activeStageNumber={config.stageNumber}
          palette={palette}
          onSelectScreen={onSelectScreen}
        />
      </div>

      {/* 3. Main Center Content Container */}
      <main className="relative flex-1 flex flex-col items-center justify-center my-auto z-10 py-3 sm:py-6 px-4 w-full max-w-4xl mx-auto">
        <AnimatePresence mode="wait">
          <motion.div
            key={config.id}
            initial={{ opacity: 0, y: 8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 1.02 }}
            transition={{
              duration: 0.4,
              ease: [0.23, 1, 0.32, 1], // Emil Kowalski UI curve
            }}
            className="w-full flex flex-col items-center"
          >
            {validationContent}
          </motion.div>
        </AnimatePresence>
      </main>

      {/* Bottom spacer */}
      <footer className="h-4 z-10" />
    </div>
  );
};
