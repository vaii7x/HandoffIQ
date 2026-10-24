import React from 'react';
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
  palette: propPalette,
  onSelectScreen,
  isEntryPage = false,
  activeConfig,
  onSelectAgent,
}) => {
  const currentStageNum = activeStageNumber ?? activeConfig?.stageNumber ?? 1;
  const palette = propPalette ?? activeConfig?.palette ?? {
    id: 'research' as const,
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

  const handleStageClick = (screenId: ScreenId) => {
    if (onSelectScreen) {
      onSelectScreen(screenId);
    } else if (onSelectAgent && (screenId === 'research' || screenId === 'coding' || screenId === 'deploy')) {
      onSelectAgent(screenId);
    }
  };

  return (
    <nav
      className="relative z-10 flex items-center justify-center gap-1.5 sm:gap-3 px-4 py-3 mt-1 overflow-x-auto no-scrollbar select-none text-[11px] sm:text-[13px]"
      aria-label="Workflow Stages"
    >
      {WORKFLOW_STAGES.map((stage, idx) => {
        const isActive = !isEntryPage && stage.number === currentStageNum;
        const isPast = !isEntryPage && stage.number < currentStageNum;

        const stageFormatted = stage.number < 10 ? `0${stage.number}` : `${stage.number}`;

        return (
          <React.Fragment key={stage.number}>
            <button
              type="button"
              onClick={() => handleStageClick(stage.screenId)}
              className="group flex items-center gap-1.5 transition-all duration-300 rounded px-1.5 py-0.5 cursor-pointer hover:opacity-100"
              title={`Switch to ${stage.name} Stage`}
            >
              {/* Number Badge */}
              <span
                className={`font-mono text-xs px-1.5 py-0.5 rounded transition-all duration-300 ${
                  isActive
                    ? 'font-bold text-white shadow-sm'
                    : isPast
                    ? 'text-white/80 font-medium'
                    : 'text-white/40'
                }`}
                style={
                  isActive
                    ? {
                        backgroundColor: `${palette.primary}25`,
                        color: palette.primary,
                        boxShadow: `0 0 12px ${palette.primary}40`,
                        border: `1px solid ${palette.primary}60`,
                      }
                    : isPast
                    ? {
                        borderBottom: `1.5px solid ${palette.primary}80`,
                      }
                    : {}
                }
              >
                {stageFormatted}
              </span>

              {/* Stage Name */}
              <span
                className={`tracking-wider transition-colors duration-300 ${
                  isActive
                    ? 'text-white font-medium'
                    : isPast
                    ? 'text-white/75'
                    : 'text-white/35'
                }`}
              >
                {stage.name}
              </span>
            </button>

            {/* Separator Em-Dash */}
            {idx < WORKFLOW_STAGES.length - 1 && (
              <span className="text-white/25 mx-0.5 select-none font-light">—</span>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
};
