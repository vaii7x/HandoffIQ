import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { AgentConfig, AgentPalette, ScreenId } from '../types/agent';
import { WORKFLOW_STAGES } from '../config/agents';

interface WorkflowStepperProps {
  activeStageNumber?: number;
  palette?: AgentPalette;
  onSelectScreen?: (screenId: ScreenId) => void;
  isEntryPage?: boolean;
  // Backwards compatibility for existing AgentPage
  activeConfig?: AgentConfig;
  onSelectAgent?: (agentId: 'research' | 'coding' | 'deploy') => void;
}

export const WorkflowStepper: React.FC<WorkflowStepperProps> = ({
  activeStageNumber,
  onSelectScreen,
  isEntryPage = false,
  activeConfig,
  onSelectAgent,
}) => {
  const currentStageNum = activeStageNumber ?? activeConfig?.stageNumber ?? 1;
  const shouldReduceMotion = useReducedMotion();

  const handleStageClick = (screenId: ScreenId) => {
    if (onSelectScreen) {
      onSelectScreen(screenId);
    } else if (
      onSelectAgent &&
      (screenId === 'research' || screenId === 'coding' || screenId === 'deploy')
    ) {
      onSelectAgent(screenId);
    }
  };

  return (
    <nav
      className={`relative z-20 flex items-center justify-center gap-1 sm:gap-2 px-4 ${
        isEntryPage ? 'py-1 sm:py-1.5 mt-0' : 'py-2 mt-0.5'
      } overflow-x-auto no-scrollbar select-none text-[11px] sm:text-[13px]`}
      aria-label="Workflow Stages"
    >
      {WORKFLOW_STAGES.map((stage, idx) => {
        const isActive = !isEntryPage && stage.number === currentStageNum;
        const isCompleted = !isEntryPage && stage.number < currentStageNum;
        const stageFormatted = stage.number < 10 ? `0${stage.number}` : `${stage.number}`;

        return (
          <React.Fragment key={stage.number}>
            <button
              type="button"
              onClick={() => handleStageClick(stage.screenId)}
              className={`relative group flex items-center gap-1.5 rounded-lg px-2.5 py-1 cursor-pointer transition-colors duration-200 outline-none ${
                isActive
                  ? 'text-[#171A35]'
                  : isCompleted
                  ? 'hover:bg-white/70 text-[#171A35]/80'
                  : 'hover:bg-white/50 text-[#737895]'
              }`}
              title={`Switch to ${stage.name} Stage`}
            >
              {/* Smooth Gliding Active Pill Highlight */}
              {isActive && (
                <motion.div
                  layoutId="activeWorkflowStepPill"
                  className="absolute inset-0 bg-[#ECECFA] border border-[#DFE1F2] rounded-lg shadow-sm -z-0"
                  transition={
                    shouldReduceMotion
                      ? { duration: 0 }
                      : {
                          type: 'spring',
                          stiffness: 400,
                          damping: 32,
                        }
                  }
                />
              )}

              {/* Number Badge */}
              <span
                className={`relative z-10 font-mono text-[11px] px-1.5 py-0.5 rounded transition-all duration-300 ${
                  isActive
                    ? 'bg-[#DADAFA] text-[#7664E8] font-bold'
                    : isCompleted
                    ? 'bg-[#ECECFA]/60 text-[#7664E8]/80 font-medium'
                    : 'text-[#737895] font-normal'
                }`}
              >
                {stageFormatted}
              </span>

              {/* Stage Name */}
              <span
                className={`relative z-10 transition-colors duration-200 text-xs ${
                  isActive
                    ? 'text-[#171A35] font-semibold'
                    : isCompleted
                    ? 'text-[#171A35]/80 font-medium'
                    : 'text-[#737895] group-hover:text-[#171A35] font-normal'
                }`}
              >
                {stage.name}
              </span>
            </button>

            {/* Separator Em-Dash */}
            {idx < WORKFLOW_STAGES.length - 1 && (
              <span className="text-[#DFE1F2] mx-0.5 select-none font-light">—</span>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
};
