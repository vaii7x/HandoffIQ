import React from 'react';
import { AgentConfig } from '../types/agent';
import { TaskResponse } from '../types/workflow';

interface AgentStatusProps {
  config: AgentConfig;
  task: TaskResponse | null;
}

export const AgentStatus: React.FC<AgentStatusProps> = ({
  config,
  task,
}) => {
  const palette = config.palette;

  // Real or simulated progress
  const stageFraction = task
    ? `${task.currentStage}/5`
    : config.fractionText;

  // Percentage for the bar
  const progressPercent = task
    ? (task.currentStage / 5) * 100
    : config.stageNumber === 1
    ? 40
    : config.stageNumber === 3
    ? 60
    : 100;

  const statusLine =
    task?.activeStatusLine || config.defaultStatus;

  const labelText = config.label;
  const headingText = config.heading;
  const descriptionText = task?.originalRequirement && config.id === 'research'
    ? task.originalRequirement
    : config.supportingText;

  return (
    <div className="relative z-10 w-full max-w-lg mx-auto px-4 mt-2 text-center flex flex-col items-center">
      {/* 1. Agent Subtitle Label */}
      <div
        className="text-[11px] sm:text-xs font-semibold tracking-[0.22em] uppercase transition-colors duration-500 min-w-0 max-w-full truncate"
        style={{ color: palette.muted }}
      >
        {labelText}
      </div>

      {/* 2. Main Heading */}
      <h2 className="text-2xl sm:text-3xl md:text-4xl font-normal tracking-tight text-[#171A35] mt-1 transition-colors duration-500 overflow-wrap-anywhere">
        {headingText}
      </h2>

      {/* Canonical Requirement Label */}
      {task?.originalRequirement && config.id === 'research' && (
        <div className="mt-2 text-[11px] text-[#737895] flex items-center justify-center gap-1.5 font-mono">
          <span className="text-[#737895]/70">Canonical Source:</span>
          <span className="text-[#171A35] font-medium">Verified Goal Contract</span>
        </div>
      )}

      {/* 3. Supporting Description Text */}
      <p
        className="text-xs sm:text-sm mt-2 max-w-md mx-auto leading-relaxed transition-colors duration-500 text-balance text-[#737895]"
        style={{
          overflowWrap: 'anywhere',
        }}
      >
        {descriptionText}
      </p>

      {/* 4. Slim Progress Bar Container */}
      <div className="w-full max-w-[340px] sm:max-w-[400px] mt-6 flex items-center gap-3">
        {/* The Track */}
        <div className="flex-1 h-1.5 bg-[#DFE1F2] rounded-full overflow-hidden p-[1px]">
          {/* Filled Segment */}
          <div
            className="h-full rounded-full transition-all duration-700 ease-out"
            style={{
              width: `${progressPercent}%`,
              backgroundColor: palette.primary,
            }}
          />
        </div>

        {/* Numeric Fraction Indicator */}
        <span
          className="text-xs font-mono font-medium tracking-wider select-none shrink-0"
          style={{
            color: palette.muted,
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {stageFraction}
        </span>
      </div>

      {/* 5. Short Dynamic Status Line */}
      <div className="min-h-[24px] mt-2.5 flex items-center justify-center">
        <span
          className="text-[12px] sm:text-xs font-normal tracking-wide text-[#737895]"
        >
          {statusLine}
        </span>
      </div>

      {/* Generated files indicator for Coding Agent */}
      {config.id === 'coding' && task?.generatedFiles && task.generatedFiles.length > 0 && (
        <div className="mt-2.5 flex flex-wrap justify-center gap-1.5 opacity-80 hover:opacity-100 transition-opacity">
          {task.generatedFiles.map((file, idx) => (
            <span
              key={idx}
              className="text-[11px] font-mono px-2 py-0.5 rounded bg-[#ECECFA] border border-[#DFE1F2] text-[#7664E8] tracking-tight"
            >
              {file.split('/').pop()}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};
