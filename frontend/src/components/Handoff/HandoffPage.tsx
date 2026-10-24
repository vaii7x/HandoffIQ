import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { HandoffPageConfig } from '../../types/handoff';
import { ScreenId } from '../../types/agent';
import { AgentHeader } from '../AgentHeader';
import { WorkflowStepper } from '../WorkflowStepper';
import { OverheadSpotlight } from '../OverheadSpotlight';
import { PerspectiveFloor } from '../PerspectiveFloor';
import { BackgroundStars } from '../BackgroundStars';
import { NavigationArrows } from '../NavigationArrows';
import { HandoffStatistics } from './HandoffStatistics';
import { WorkflowCheckRow } from './WorkflowCheckRow';
import { ExpandableValidationDetails } from './ExpandableValidationDetails';
import { ExpandableTestingDetails } from './ExpandableTestingDetails';
import { HandoffDecision } from './HandoffDecision';
import { HandoffProgress } from './HandoffProgress';
import { RunningTestsView } from './RunningTestsView';
import { TaskResponse } from '../../types/workflow';

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
}) => {
  // If rendering stage 4 (Running Tests / Coding -> Deploy), use the refined minimalist developer interface
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
      />
    );
  }

  const palette = config.palette;

  // Single expanded row state: defaults to row 2 (discrepancies / failures) or null
  const [expandedRowId, setExpandedRowId] = useState<string | null>(
    config.checkRows[1]?.id || null
  );

  const toggleRow = (id: string) => {
    setExpandedRowId((prev) => (prev === id ? null : id));
  };

  const progressPercent = (config.stageNumber / 5) * 100;
  const statusLine = task?.activeStatusLine || config.defaultStatusText;

  return (
    <div
      className="relative min-h-screen w-full flex flex-col justify-between overflow-hidden transition-colors duration-700 ease-out select-none"
      style={{
        backgroundColor: palette.background,
        color: palette.text,
      }}
    >
      {/* 1. Ambient Background Atmosphere */}
      <BackgroundStars />
      <OverheadSpotlight palette={palette} />
      <PerspectiveFloor palette={palette} />

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
            {/* Centered Eyebrow, Heading & Supporting text */}
            <div className="text-center max-w-xl mx-auto mb-2">
              <div
                className="text-[11px] sm:text-xs font-semibold tracking-[0.24em] uppercase transition-colors duration-500"
                style={{ color: palette.muted }}
              >
                {config.eyebrow}
              </div>
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-normal tracking-tight text-white mt-1">
                {config.heading}
              </h2>
              <p
                className="text-xs sm:text-sm mt-2 leading-relaxed text-balance"
                style={{ color: palette.muted }}
              >
                {config.supportingText}
              </p>
            </div>

            {/* 4. Compact 5-Statistic Row */}
            <HandoffStatistics stats={config.stats} palette={palette} />

            {/* 5. Three Expandable Check Rows */}
            <div className="w-full max-w-3xl mx-auto bg-white/[0.015] border border-white/10 rounded-lg p-1 sm:p-2 backdrop-blur-sm">
              {config.checkRows.map((check) => (
                <WorkflowCheckRow
                  key={check.id}
                  check={check}
                  isExpanded={expandedRowId === check.id}
                  onToggle={() => toggleRow(check.id)}
                  palette={palette}
                >
                  {config.id === 'validate' ? (
                    <ExpandableValidationDetails
                      kind={
                        check.kind as
                          | 'requirement_comparison'
                          | 'discrepancy_list'
                          | 'constraint_risks'
                      }
                      discrepancies={config.discrepancies}
                      palette={palette}
                    />
                  ) : (
                    <ExpandableTestingDetails
                      kind={
                        check.kind as
                          | 'test_suite'
                          | 'failure_analysis'
                          | 'self_healing_fixes'
                      }
                      testCases={config.testCases}
                      failures={config.failures}
                      repairs={config.repairs}
                      palette={palette}
                    />
                  )}
                </WorkflowCheckRow>
              ))}
            </div>

            {/* 6. Handoff Decision Banner & Action */}
            <HandoffDecision
              decision={config.decision}
              palette={palette}
              onContinue={() => onSelectScreen(config.decision.nextScreenId)}
            />

            {/* 7. Bottom Progress Area */}
            <HandoffProgress
              stageFraction={config.fractionText}
              progressPercent={progressPercent}
              statusText={statusLine}
              palette={palette}
            />
          </motion.div>
        </AnimatePresence>
      </main>

      {/* 8. Carousel Edge Navigation Arrows */}
      <NavigationArrows
        palette={palette}
        hasPrev={hasPrev}
        hasNext={hasNext}
        onPrev={onPrev}
        onNext={onNext}
        prevName={prevName}
        nextName={nextName}
      />

      {/* Bottom spacer */}
      <footer className="h-4 z-10" />
    </div>
  );
};
