import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertCircle, RefreshCw, ArrowRight } from 'lucide-react';
import { AgentConfig, AgentId, ScreenId } from '../types/agent';
import { TaskResponse } from '../types/workflow';
import { apiService } from '../services/api';
import { AgentHeader } from './AgentHeader';
import { WorkflowStepper } from './WorkflowStepper';
import { ParticleSphere } from './ParticleSphere/ParticleSphere';
import { AgentStatus } from './AgentStatus';
import { ResearchSummaryView } from './Research/ResearchSummaryView';
import { CodeOutputViewer } from './Deploy/CodeOutputViewer';
import { OverheadSpotlight } from './OverheadSpotlight';
import { PerspectiveFloor } from './PerspectiveFloor';
import { BackgroundStars } from './BackgroundStars';

interface AgentPageProps {
  config: AgentConfig;
  task: TaskResponse | null;
  onSelectScreen?: (screenId: ScreenId) => void;
  onSelectAgent?: (agentId: AgentId) => void;
  onPrevAgent?: () => void;
  onNextAgent?: () => void;
  onRetry?: () => Promise<void>;
  hasPrev?: boolean;
  hasNext?: boolean;
  prevName?: string;
  nextName?: string;
  hideChrome?: boolean;
  hideBackground?: boolean;
  hideSphere?: boolean;
}

export const AgentPage: React.FC<AgentPageProps> = ({
  config,
  task,
  onSelectScreen,
  onSelectAgent,
  onRetry,
  hideChrome = false,
  hideBackground = false,
  hideSphere = false,
}) => {
  const palette = config.palette;
  const [isRetrying, setIsRetrying] = useState<boolean>(false);

  const handleRetry = async () => {
    if (!task?.taskId || isRetrying) return;
    setIsRetrying(true);
    try {
      if (onRetry) {
        await onRetry();
      } else {
        await apiService.startWorkflow(task.taskId);
      }
    } catch (err) {
      console.warn('Retry workflow error:', err);
    } finally {
      setIsRetrying(false);
    }
  };

  const displayError = useMemo(() => {
    if (!task?.error) return 'Generation failed to complete. Inspect backend logs or retry.';
    const msg = String(task.error);
    if (msg.includes('aborted without reason') || msg.includes('AbortError') || msg.includes('cancelled')) {
      return 'Generation request was interrupted during navigation or connection reset. Click Retry to continue.';
    }
    if (msg.includes('timeout') || msg.includes('timed out')) {
      return 'Generation took longer than expected to respond. Click Retry to resume.';
    }
    if (msg.includes('API_KEY') || msg.includes('authentication') || msg.includes('401') || msg.includes('403')) {
      return 'AI service authentication failed. Please verify API configuration.';
    }
    return msg;
  }, [task?.error]);

  const stageContent = (
    <div className="flex flex-col items-center justify-center w-full">
      {/* Conditional Rendering by Stage */}
      {config.id === 'research' ? (
        <>
          {!hideSphere && <ParticleSphere palette={palette} />}
          <ResearchSummaryView
            task={task}
            palette={palette}
            onContinue={() => onSelectScreen?.('validate')}
          />
        </>
      ) : config.id === 'deploy' ? (
        <CodeOutputViewer
          task={task}
          palette={palette}
          onNewGoal={() => onSelectScreen?.('input')}
        />
      ) : (
        <>
          {!hideSphere && <ParticleSphere palette={palette} />}
          <AgentStatus config={config} task={task} />

          {/* Failure & Error State Handling for Coding Stage */}
          {task?.error || task?.status === 'failed' ? (
            <div className="mt-5 w-full max-w-md mx-auto p-4 bg-red-50/70 border border-red-200/80 rounded-2xl flex flex-col items-center text-center space-y-2 z-20 shadow-sm">
              <div className="flex items-center gap-2 text-red-600 font-semibold text-xs">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>Code Generation Error</span>
              </div>
              <p className="text-xs text-[#737895] leading-relaxed">
                {displayError}
              </p>
              <button
                type="button"
                onClick={handleRetry}
                disabled={isRetrying}
                className="mt-1 flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium text-white bg-[#7664E8] hover:bg-[#6855DE] transition-all shadow-sm active:scale-[0.98] cursor-pointer disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isRetrying ? 'animate-spin' : ''}`} />
                <span>{isRetrying ? 'Retrying Generation...' : 'Retry Generation'}</span>
              </button>
            </div>
          ) : (
            <div className="mt-5 flex flex-col items-center gap-3 z-20">
              {/* Truthful Progress Indicator */}
              {task?.currentStage && task.currentStage >= 4 ? (
                <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#ECECFA] border border-[#DFE1F2] text-xs font-mono text-[#7664E8]">
                  <span className="w-2 h-2 rounded-full bg-[#7664E8]" />
                  <span>Code artifacts ready · Advancing to Testing…</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#ECECFA] border border-[#DFE1F2] text-xs font-mono text-[#7664E8]">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-[#7664E8]" />
                  <span>Generating code artifacts & preparing verification…</span>
                </div>
              )}

              {/* Manual Navigation Fallback */}
              <button
                type="button"
                onClick={() => onSelectScreen?.('test')}
                className="flex items-center gap-1.5 px-5 py-2 rounded-xl text-xs font-medium tracking-wide bg-white hover:bg-[#FAF9FC] border border-[#DFE1F2] text-[#171A35] transition-all shadow-sm active:scale-[0.98] cursor-pointer"
              >
                <span>Skip to Testing</span>
                <ArrowRight className="w-3.5 h-3.5 text-[#737895]" />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );

  if (hideChrome) {
    return <div className="w-full flex flex-col items-center justify-center select-none">{stageContent}</div>;
  }

  return (
    <div
      className="relative min-h-screen w-full flex flex-col justify-between overflow-x-hidden overflow-y-auto transition-colors duration-700 ease-out select-none"
      style={{
        backgroundColor: palette.background,
        color: palette.text,
      }}
    >
      {/* 1. Atmospheric Ambient Layers */}
      {!hideBackground && (
        <>
          <BackgroundStars />
          <OverheadSpotlight palette={palette} />
          <PerspectiveFloor palette={palette} />
        </>
      )}

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

      {/* 3. Hero Visual & Screen Content */}
      <main className="relative flex-1 flex flex-col items-center justify-center my-auto z-10 py-2 sm:py-4">
        <AnimatePresence mode="wait">
          <motion.div
            key={config.id}
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.03 }}
            transition={{
              duration: 0.4,
              ease: [0.23, 1, 0.32, 1], // Emil Kowalski UI ease-out
            }}
            className="flex flex-col items-center justify-center w-full"
          >
            {stageContent}
          </motion.div>
        </AnimatePresence>
      </main>

      {/* Bottom spacer for balance */}
      <footer className="h-6 z-10" />
    </div>
  );
};
