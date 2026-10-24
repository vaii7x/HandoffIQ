import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowRight, Loader2, AlertCircle } from 'lucide-react';
import { AgentPalette, ScreenId } from '../../types/agent';
import { AgentHeader } from '../AgentHeader';
import { WorkflowStepper } from '../WorkflowStepper';
import { OverheadSpotlight } from '../OverheadSpotlight';
import { PerspectiveFloor } from '../PerspectiveFloor';
import { BackgroundStars } from '../BackgroundStars';
import { AdvancedOptions, AdvancedConfigState } from './AdvancedOptions';
import { apiService } from '../../services/api';

interface RequirementInputPageProps {
  palette: AgentPalette;
  onStartWorkflow: (taskId: string, requirement: string) => void;
  onSelectScreen?: (screenId: ScreenId) => void;
  isMockMode: boolean;
  onToggleMockMode: (val: boolean) => void;
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

  const charCount = requirement.length;
  const isMinValid = charCount >= 15;

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!isMinValid || isSubmitting) return;

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const task = await apiService.createTask({
        requirement: requirement.trim(),
        framework: advancedConfig.framework,
        constraints: advancedConfig.constraints || undefined,
        autoRepair: advancedConfig.autoRepair,
        demoMode: isMockMode,
      });

      // Navigate to the Research Agent with the created task
      onStartWorkflow(task.taskId, requirement.trim());
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

      {/* 2. Top Header & Workflow Stepper (Entry Page: 0 stages completed) */}
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
            AGENTIC WORKFLOW
          </span>
          <WorkflowStepper
            activeStageNumber={0}
            palette={palette}
            isEntryPage={true}
            onSelectScreen={onSelectScreen}
          />
        </div>
      </div>

      {/* 3. Main Centered Requirement Input Container */}
      <main className="relative flex-1 flex flex-col items-center justify-center my-auto z-10 py-4 sm:py-8 px-4 w-full max-w-2xl mx-auto">
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
          <div className="text-center max-w-xl mx-auto mb-6">
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-normal tracking-tight text-white">
              What do you want to build?
            </h2>
            <p
              className="text-xs sm:text-sm mt-2.5 leading-relaxed text-balance"
              style={{ color: palette.muted }}
            >
              Describe your goal. HandoffIQ will preserve your requirements,
              validate every agent handoff, and verify the implementation
              before completion.
            </p>
          </div>

          {/* Error Banner */}
          <AnimatePresence>
            {errorMessage && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="w-full mb-4 p-3 rounded bg-red-950/40 border border-red-500/30 text-xs text-red-200 flex items-start gap-2.5"
              >
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <div className="flex-1 space-y-1">
                  <p>{errorMessage}</p>
                  {isMockMode === false && (
                    <button
                      type="button"
                      onClick={() => {
                        onToggleMockMode(true);
                        setErrorMessage(null);
                      }}
                      className="text-[11px] underline text-red-300 hover:text-white"
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
            className="w-full bg-[#080E1A]/80 border border-white/10 rounded-lg p-4 sm:p-5 space-y-3"
          >
            {/* Multiline Requirement Text Area */}
            <div className="relative">
              <textarea
                value={requirement}
                onChange={(e) => setRequirement(e.target.value)}
                placeholder="Describe the application you want to build, the features it needs, the technologies or constraints to follow, and what a successful result looks like..."
                rows={6}
                disabled={isSubmitting}
                className="w-full bg-black/40 border border-white/10 rounded p-3.5 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-blue-400/60 focus:ring-1 focus:ring-blue-400/40 transition-all resize-y min-h-[160px] sm:min-h-[190px] leading-relaxed selection:bg-blue-500/30 font-sans"
              />

              {/* Character Count & Length Validation Feedback */}
              <div className="flex items-center justify-between text-[11px] text-white/40 mt-1.5 px-0.5 select-none font-mono">
                <span>
                  {charCount < 15 ? (
                    <span className="text-white/40">
                      Minimum 15 characters ({charCount}/15)
                    </span>
                  ) : (
                    <span className="text-white/60">Input ready</span>
                  )}
                </span>
                <span>{charCount} characters</span>
              </div>
            </div>

            {/* Quick Inspiration Chips */}
            <div className="flex flex-wrap items-center gap-1.5 pt-1 text-[11px]">
              <span className="text-white/40 mr-1 font-mono text-[10px]">
                Templates:
              </span>
              {SAMPLE_TEMPLATES.map((tmpl, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setRequirement(tmpl.text)}
                  className="px-2 py-0.5 rounded bg-white/[0.03] hover:bg-white/[0.08] border border-white/5 hover:border-white/15 text-white/60 hover:text-white transition-all text-[11px]"
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

            {/* Bottom Actions Row */}
            <div className="pt-3 flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-white/10">
              <span className="text-[11px] text-white/40 text-center sm:text-left">
                Original text is preserved throughout all agent transitions.
              </span>

              <button
                type="submit"
                disabled={!isMinValid || isSubmitting}
                className={`w-full sm:w-auto px-4 py-2 rounded text-xs font-medium tracking-wide flex items-center justify-center gap-2 transition-all duration-200 ${
                  !isMinValid || isSubmitting
                    ? 'opacity-40 cursor-not-allowed bg-white/10 text-white/50'
                    : 'bg-[#377FEA] hover:bg-[#2B6FD8] text-white active:scale-[0.98] cursor-pointer'
                }`}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Preparing workflow…</span>
                  </>
                ) : (
                  <>
                    <span>Start workflow</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </button>
            </div>
          </form>
        </motion.div>
      </main>

      {/* Bottom spacer */}
      <footer className="h-6 z-10" />
    </div>
  );
};
