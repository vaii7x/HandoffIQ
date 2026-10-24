import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AgentConfig, AgentId, ScreenId } from '../types/agent';
import { TaskResponse } from '../types/workflow';
import { AgentHeader } from './AgentHeader';
import { WorkflowStepper } from './WorkflowStepper';
import { ParticleSphere } from './ParticleSphere/ParticleSphere';
import { AgentStatus } from './AgentStatus';
import { OverheadSpotlight } from './OverheadSpotlight';
import { PerspectiveFloor } from './PerspectiveFloor';
import { BackgroundStars } from './BackgroundStars';
import { NavigationArrows } from './NavigationArrows';

interface AgentPageProps {
  config: AgentConfig;
  task: TaskResponse | null;
  onSelectScreen?: (screenId: ScreenId) => void;
  onSelectAgent?: (agentId: AgentId) => void;
  onPrevAgent: () => void;
  onNextAgent: () => void;
  hasPrev: boolean;
  hasNext: boolean;
  prevName?: string;
  nextName?: string;
  isWorstCase?: boolean;
}

export const AgentPage: React.FC<AgentPageProps> = ({
  config,
  task,
  onSelectScreen,
  onSelectAgent,
  onPrevAgent,
  onNextAgent,
  hasPrev,
  hasNext,
  prevName,
  nextName,
  isWorstCase = false,
}) => {
  const palette = config.palette;

  return (
    <div
      className="relative min-h-screen w-full flex flex-col justify-between overflow-hidden transition-colors duration-700 ease-out select-none"
      style={{
        backgroundColor: palette.background,
        color: palette.text,
      }}
    >
      {/* 1. Atmospheric Ambient Layers */}
      <BackgroundStars />
      <OverheadSpotlight palette={palette} />
      <PerspectiveFloor palette={palette} />

      {/* 2. Top Navigation Structure */}
      <div className="w-full z-20">
        <AgentHeader
          palette={palette}
          onSelectScreen={onSelectScreen}
          activeScreen={config.id}
        />
        <WorkflowStepper
          activeStageNumber={config.stageNumber}
          palette={palette}
          onSelectScreen={(screenId) => {
            if (onSelectScreen) {
              onSelectScreen(screenId);
            } else if (
              onSelectAgent &&
              (screenId === 'research' ||
                screenId === 'coding' ||
                screenId === 'deploy')
            ) {
              onSelectAgent(screenId);
            }
          }}
          activeConfig={config}
          onSelectAgent={onSelectAgent}
        />
      </div>

      {/* 3. Hero Visual — Particle Sphere with smooth transition */}
      <main className="relative flex-1 flex flex-col items-center justify-center my-auto z-10 py-2 sm:py-4">
        <AnimatePresence mode="wait">
          <motion.div
            key={config.id}
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.04 }}
            transition={{
              duration: 0.45,
              ease: [0.23, 1, 0.32, 1], // Emil Kowalski UI ease-out
            }}
            className="flex flex-col items-center justify-center w-full"
          >
            {/* The 3D Particle Sphere */}
            <ParticleSphere palette={palette} />

            {/* Agent Status Block */}
            <AgentStatus
              config={config}
              task={task}
              worstCaseMode={isWorstCase}
            />
          </motion.div>
        </AnimatePresence>
      </main>

      {/* 4. Edge Carousel Navigation Arrows */}
      <NavigationArrows
        palette={palette}
        hasPrev={hasPrev}
        hasNext={hasNext}
        onPrev={onPrevAgent}
        onNext={onNextAgent}
        prevName={prevName}
        nextName={nextName}
      />

      {/* Bottom spacer for balance */}
      <footer className="h-6 z-10" />
    </div>
  );
};
