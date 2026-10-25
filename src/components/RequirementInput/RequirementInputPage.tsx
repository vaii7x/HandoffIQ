import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, AlertCircle, ArrowRight } from 'lucide-react';
import { AgentPalette, ScreenId } from '../../types/agent';
import { AgentHeader } from '../AgentHeader';
import { WorkflowStepper } from '../WorkflowStepper';
import { OverheadSpotlight } from '../OverheadSpotlight';
import { PerspectiveFloor } from '../PerspectiveFloor';
import { BackgroundStars } from '../BackgroundStars';
import { ParticleSphere } from '../ParticleSphere/ParticleSphere';
import { AdvancedOptions, AdvancedConfigState } from './AdvancedOptions';
import { apiService } from '../../services/api';

interface RequirementInputPageProps {
  palette: AgentPalette;
  onStartWorkflow: (taskId: string, requirement: string) => void;
  onSelectScreen?: (screenId: ScreenId) => void;
  isMockMode: boolean;
  onToggleMockMode: (val: boolean) => void;
  onOpenDemo?: () => void;
  hideChrome?: boolean;
  hideBackground?: boolean;
  hideSphere?: boolean;
}

const SAMPLE_TEMPLATES = [
  {
    label: 'AI Reliability Engine',
    text: 'Build a multi-agent AI verification platform with real-time SSE event streaming, automated handoff validation contracts, and self-healing test recovery on Python FastAPI and React Three Fiber.',
  },
  {
    label: 'Real-time WebSocket Hub',
    text: 'Build a high-throughput distributed WebSocket event broker with client reconnection backoff, Redis pub/sub state synchronization, and sub-100ms message delivery guarantees.',
  },
  {
    label: 'Fintech Audit Dashboard',
    text: 'Create a SOC2-compliant transaction audit suite with automated ledger checksum verification, cryptographic event hashing, and role-based access control.',
  },
];

export const RequirementInputPage: React.FC<RequirementInputPageProps> = ({
  palette,
  onStartWorkflow,
  onSelectScreen,
  isMockMode,
  onToggleMockMode,
  onOpenDemo,
  hideChrome = false,
  hideBackground = false,
  hideSphere = false,
}) => {
  const [requirement, setRequirement] = useState('');
  const [isAdvancedOpen, setIsAdvancedOpen] = useState(false);
  const [advancedConfig, setAdvancedConfig] = useState<AdvancedConfigState>({
    framework: 'React / TypeScript',
    constraints: '',
    autoRepair: true,
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const charCount = requirement.trim().length;

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const cleanReq = requirement.trim();
    if (!cleanReq) {
      setErrorMessage('Please enter a project description or task goal before starting the workflow.');
      return;
    }
    if (cleanReq.length < 15) {
      setErrorMessage('Please provide a bit more detail (at least 15 characters) so HandoffIQ can extract verifiable requirements.');
      return;
    }
    if (isSubmitting) return;

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const task = await apiService.createTask({
        requirement: cleanReq,
        framework: advancedConfig.framework,
        constraints: advancedConfig.constraints || undefined,
        autoRepair: advancedConfig.autoRepair,
        demoMode: isMockMode,
      });

      // Navigate into the actual workflow with the created task
      onStartWorkflow(task.taskId, cleanReq);
    } catch (err: any) {
      console.error('Failed to create task:', err);
      setErrorMessage(
        err.message ||
          'Could not connect to the backend server. Switch to Demo Mode or ensure FastAPI is running.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const mainFormContent = (
    <div className="relative flex-1 flex flex-col items-center justify-start z-10 pt-1 pb-3 sm:pt-2 sm:pb-4 px-3 sm:px-4 w-full max-w-2xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 12, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{
          duration: 0.45,
          ease: [0.23, 1, 0.32, 1], // Emil Kowalski UI curve
        }}
        className="w-full flex flex-col items-center"
      >
        {/* Main Heading & Subtitle */}
        <div className="text-center max-w-xl mx-auto mb-3 sm:mb-4">
          <h2 className="text-xl sm:text-2xl md:text-3xl font-normal tracking-tight text-[#171A35]">
            What do you want to build?
          </h2>
          <p
            className="text-xs sm:text-[13px] mt-1 sm:mt-1.5 leading-relaxed text-balance text-[#737895]"
          >
            Describe your goal. HandoffIQ will preserve your requirements,
            validate every agent handoff, and verify the implementation
            before completion.
          </p>
        </div>

        {/* Useful Validation / Error Banner */}
        <AnimatePresence>
          {errorMessage && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="w-full mb-3 p-3 rounded-xl bg-[#FEECEE] border border-[#FCD6D9] text-xs text-[#D9383A] flex items-start gap-2.5 shadow-sm"
            >
              <AlertCircle className="w-4 h-4 text-[#D9383A] shrink-0 mt-0.5" />
              <div className="flex-1 space-y-1">
                <p>{errorMessage}</p>
                {isMockMode === false && (
                  <button
                    type="button"
                    onClick={() => {
                      onToggleMockMode(true);
                      setErrorMessage(null);
                    }}
                    className="text-[11px] underline text-[#B82B2D] hover:text-[#171A35]"
                  >
                    Switch to Demo Mode to proceed without backend
                  </button>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Form Surface */}
        <form
          onSubmit={handleSubmit}
          className="w-full bg-white border border-[#DFE1F2] rounded-2xl p-4 sm:p-5 space-y-2.5 sm:space-y-3 shadow-[0_2px_16px_rgba(23,26,53,0.04)]"
        >
          {/* Multiline Requirement Text Area */}
          <div className="relative">
            <textarea
              value={requirement}
              onChange={(e) => {
                setRequirement(e.target.value);
                if (errorMessage) setErrorMessage(null);
              }}
              placeholder="Describe the application you want to build, the features it needs, the technologies or constraints to follow, and what a successful result looks like..."
              rows={4}
              disabled={isSubmitting}
              className="w-full bg-[#FAF9FC] border border-[#DFE1F2] rounded-xl p-3 sm:p-3.5 text-sm text-[#171A35] placeholder:text-[#737895]/60 focus:outline-none focus:border-[#7664E8] focus:ring-1 focus:ring-[#7664E8]/40 transition-all resize-y min-h-[110px] sm:min-h-[125px] md:min-h-[135px] leading-relaxed font-sans"
            />

            {/* Character Count & Length Validation Feedback */}
            <div className="flex items-center justify-between text-[11px] text-[#737895] mt-1 px-0.5 select-none font-mono">
              <span>
                {charCount === 0 ? (
                  <span className="text-[#737895]/60">Describe your task above</span>
                ) : charCount < 15 ? (
                  <span className="text-[#B8721A]">
                    Minimum 15 characters ({charCount}/15)
                  </span>
                ) : (
                  <span className="text-[#7664E8] font-medium">Input ready</span>
                )}
              </span>
              <span>{charCount} characters</span>
            </div>
          </div>

          {/* Quick Inspiration Templates */}
          <div className="flex flex-wrap items-center gap-1.5 pt-0.5 text-[11px]">
            <span className="text-[#737895] mr-1 font-mono text-[10px]">
              Templates:
            </span>
            {SAMPLE_TEMPLATES.map((tmpl, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  setRequirement(tmpl.text);
                  if (errorMessage) setErrorMessage(null);
                }}
                className="px-2.5 py-1 rounded-lg bg-[#FAF9FC] hover:bg-white border border-[#DFE1F2] text-[#737895] hover:text-[#171A35] transition-all text-[11px] shadow-sm"
              >
                {tmpl.label}
              </button>
            ))}
          </div>

          {/* Collapsible Advanced Options */}
          <AdvancedOptions
            isOpen={isAdvancedOpen}
            onToggle={() => setIsAdvancedOpen(!isAdvancedOpen)}
            config={advancedConfig}
            onChange={(updated) =>
              setAdvancedConfig((prev) => ({ ...prev, ...updated }))
            }
            palette={palette}
            isMockMode={isMockMode}
            onToggleMockMode={onToggleMockMode}
          />

          {/* Bottom Actions Row (No arrow icons) */}
          <div className="pt-2.5 sm:pt-3 flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-[#DFE1F2]">
            <span className="text-[11px] text-[#737895] text-center sm:text-left">
              Original text is preserved throughout all agent transitions.
            </span>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full sm:w-auto px-6 py-2.5 rounded-xl text-xs font-semibold tracking-wide flex items-center justify-center gap-2 transition-all duration-200 bg-[#7664E8] hover:bg-[#6855DE] text-white active:scale-[0.98] shadow-sm cursor-pointer disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Preparing workflow…</span>
                </>
              ) : (
                <span>Start Workflow</span>
              )}
            </button>
          </div>
        </form>

        {/* Dedicated Demo Mode Entry Point Card */}
        <div className="w-full mt-3 p-3.5 sm:p-4 rounded-xl bg-white border border-[#DFE1F2] shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-[#171A35]">Demo Mode</span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium tracking-wide bg-[#FAF9FC] text-[#737895] border border-[#DFE1F2]">
                Simulated Demo
              </span>
            </div>
            <p className="text-xs text-[#737895]">
              Explore how HandoffIQ detects and repairs broken agent handoffs.
            </p>
          </div>
          {onOpenDemo && (
            <button
              type="button"
              onClick={onOpenDemo}
              className="w-full sm:w-auto px-4 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all duration-200 bg-[#FAF9FC] hover:bg-[#ECECFA] text-[#7664E8] border border-[#DFE1F2] hover:border-[#7664E8]/40 active:scale-[0.98] shadow-xs cursor-pointer flex items-center justify-center gap-1.5 shrink-0"
            >
              <span>Start Demo</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </motion.div>
    </div>
  );

  if (hideChrome) {
    return <div className="w-full flex-1 flex flex-col items-center justify-start select-none">{mainFormContent}</div>;
  }

  return (
    <div
      className="relative min-h-screen w-full flex flex-col justify-between overflow-hidden transition-colors duration-700 ease-out select-none"
      style={{
        backgroundColor: palette.background,
        color: palette.text,
      }}
    >
      {/* 1. Atmospheric Ambient Layers with subtle glowing sphere */}
      {!hideBackground && (
        <>
          <BackgroundStars />
          <OverheadSpotlight palette={palette} />
          <PerspectiveFloor palette={palette} />
        </>
      )}

      {!hideSphere && (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none opacity-20 scale-75 sm:scale-90 z-0">
          <ParticleSphere palette={palette} />
        </div>
      )}

      {/* 2. Top Header & Compact Workflow Stepper (Entry Stage: Task Input) */}
      <div className="w-full z-20">
        <AgentHeader
          palette={palette}
          onSelectScreen={onSelectScreen}
          activeScreen="input"
        />
        <div className="flex flex-col items-center">
          <span
            className="text-[10px] font-semibold tracking-[0.28em] uppercase transition-colors pt-1"
            style={{ color: palette.muted }}
          >
            TASK SPECIFICATION
          </span>
          <WorkflowStepper
            activeStageNumber={0}
            palette={palette}
            isEntryPage={true}
            onSelectScreen={onSelectScreen}
          />
        </div>
      </div>

      {mainFormContent}

      {/* Bottom spacer */}
      <footer className="h-3 sm:h-4 z-10" />
    </div>
  );
};
