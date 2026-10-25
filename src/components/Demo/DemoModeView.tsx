import React, { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft,
  ArrowRight,
  RotateCcw,
  ShieldAlert,
  X,
  Play,
  CheckCircle2,
} from 'lucide-react';
import type { AgentPalette } from '../../types/agent';
import type {
  DemoRequirement,
  DemoHandoffItem,
  DemoRepairItem,
  DemoValidationResponse,
  DemoRevalidationResponse,
  DemoStep,
  DemoStatus,
} from '../../types/demo';
import { demoService } from '../../services/demoService';
import { Step1Requirements } from './Step1Requirements';
import { Step2BrokenHandoff } from './Step2BrokenHandoff';
import { Step3ValidationResults } from './Step3ValidationResults';
import { Step4Repair } from './Step4Repair';
import { Step5Revalidation } from './Step5Revalidation';

interface DemoModeViewProps {
  palette: AgentPalette;
  onExitDemo: () => void;
}

const STEP_LABELS = [
  '01 Requirements',
  '02 Handoff',
  '03 Validation',
  '04 Repairs',
  '05 Revalidation',
];

export const DemoModeView: React.FC<DemoModeViewProps> = ({
  palette,
  onExitDemo,
}) => {
  const [currentStep, setCurrentStep] = useState<DemoStep>(1);
  const [status, setStatus] = useState<DemoStatus>('loading');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Demo Data State
  const [requirements, setRequirements] = useState<DemoRequirement[]>([]);
  const [brokenHandoff, setBrokenHandoff] = useState<DemoHandoffItem[]>([]);
  const [repairs, setRepairs] = useState<DemoRepairItem[]>([]);
  const [validationData, setValidationData] = useState<DemoValidationResponse | null>(null);
  const [revalidationData, setRevalidationData] = useState<DemoRevalidationResponse | null>(null);

  const [isRepaired, setIsRepaired] = useState<boolean>(false);
  const isExecutingRef = useRef<boolean>(false);

  // Initial load
  const loadInitialData = useCallback(async () => {
    setStatus('loading');
    setErrorMessage(null);
    try {
      const [reqs, handoff, reps] = await Promise.all([
        demoService.getRequirements(),
        demoService.getBrokenHandoff(),
        demoService.getRepairs(),
      ]);
      setRequirements(reqs);
      setBrokenHandoff(handoff);
      setRepairs(reps);
      setStatus('ready');
    } catch (err: any) {
      console.error('Failed to load demo fixtures:', err);
      setErrorMessage('Could not load demo fixtures. Please retry or verify connection.');
      setStatus('error');
    }
  }, []);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Step 3: Run Validation
  const handleRunValidation = async () => {
    if (isExecutingRef.current) return;
    isExecutingRef.current = true;
    setStatus('validating');
    setErrorMessage(null);
    try {
      const res = await demoService.validateHandoff();
      setValidationData(res);
      setStatus('ready');
      setCurrentStep(3);
    } catch (err: any) {
      console.error('Validation error:', err);
      setErrorMessage('Validation execution failed. Please retry.');
      setStatus('error');
    } finally {
      isExecutingRef.current = false;
    }
  };

  // Step 4: Apply Repairs
  const handleApplyRepairs = async () => {
    if (isExecutingRef.current) return;
    isExecutingRef.current = true;
    setStatus('repairing');
    setErrorMessage(null);
    try {
      // Simulate patch synthesis delay for presentation feel
      await new Promise((r) => setTimeout(r, 600));
      setIsRepaired(true);
      setStatus('ready');
    } catch (err: any) {
      console.error('Repair error:', err);
      setErrorMessage('Repair patch application failed. Please retry.');
      setStatus('error');
    } finally {
      isExecutingRef.current = false;
    }
  };

  // Step 5: Run Revalidation
  const handleRunRevalidation = async () => {
    if (isExecutingRef.current) return;
    isExecutingRef.current = true;
    setStatus('revalidating');
    setErrorMessage(null);
    try {
      const res = await demoService.revalidateHandoff();
      setRevalidationData(res);
      setStatus('ready');
      setCurrentStep(5);
    } catch (err: any) {
      console.error('Revalidation error:', err);
      setErrorMessage('Revalidation execution failed. Please retry.');
      setStatus('error');
    } finally {
      isExecutingRef.current = false;
    }
  };

  // Reset Demo to initial state
  const handleResetDemo = () => {
    setCurrentStep(1);
    setValidationData(null);
    setRevalidationData(null);
    setIsRepaired(false);
    setErrorMessage(null);
    loadInitialData();
  };

  // Navigation handlers
  const handleNext = () => {
    if (currentStep === 1) {
      setCurrentStep(2);
    } else if (currentStep === 2) {
      handleRunValidation();
    } else if (currentStep === 3) {
      setCurrentStep(4);
    } else if (currentStep === 4) {
      handleRunRevalidation();
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep((prev) => (prev - 1) as DemoStep);
    }
  };

  return (
    <div className="relative min-h-screen w-full flex flex-col justify-between overflow-x-hidden font-sans antialiased text-[#171A35] select-none">
      {/* 1. Presentation Header Bar */}
      <header className="w-full bg-white/80 backdrop-blur-md border-b border-[#DFE1F2] sticky top-0 z-40 px-4 sm:px-6 py-2.5">
        <div className="max-w-5xl mx-auto flex items-center justify-between gap-4">
          {/* Logo & Simulated Demo Badge */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 select-none">
              <h1 className="text-xs sm:text-sm font-semibold tracking-[0.38em] text-[#171A35] uppercase pl-1">
                H A N D O F F I Q
              </h1>
              <span
                className="w-1.5 h-1.5 rounded-full inline-block ml-1"
                style={{
                  backgroundColor: palette.primary,
                  boxShadow: `0 0 6px ${palette.primary}60`,
                }}
              />
            </div>

            <span className="text-[10px] font-mono font-medium tracking-wide text-[#737895] bg-[#FAF9FC] border border-[#DFE1F2] px-2 py-0.5 rounded">
              Simulated Demo
            </span>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleResetDemo}
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-[#737895] hover:text-[#171A35] bg-[#FAF9FC] hover:bg-white border border-[#DFE1F2] transition-all cursor-pointer shadow-xs active:scale-[0.98]"
              title="Reset demo to initial step"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset</span>
            </button>

            <button
              type="button"
              onClick={onExitDemo}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-[#171A35] bg-white hover:bg-[#FAF9FC] border border-[#DFE1F2] transition-all cursor-pointer shadow-xs active:scale-[0.98]"
              title="Return to Live Mode"
            >
              <X className="w-3.5 h-3.5 text-[#737895]" />
              <span>Exit Demo</span>
            </button>
          </div>
        </div>

        {/* 5-Step Presentation Stepper */}
        <nav
          className="max-w-3xl mx-auto pt-2 pb-0.5 flex items-center justify-between gap-1 overflow-x-auto no-scrollbar"
          aria-label="Demo Steps"
        >
          {STEP_LABELS.map((label, idx) => {
            const stepNum = (idx + 1) as DemoStep;
            const isActive = currentStep === stepNum;
            const isCompleted = currentStep > stepNum;

            return (
              <button
                key={stepNum}
                type="button"
                onClick={() => {
                  if (stepNum <= 2 || validationData) {
                    if (stepNum === 3 && !validationData) {
                      handleRunValidation();
                    } else if (stepNum === 5 && !revalidationData) {
                      handleRunRevalidation();
                    } else {
                      setCurrentStep(stepNum);
                    }
                  }
                }}
                className={`relative flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs transition-all cursor-pointer whitespace-nowrap ${
                  isActive
                    ? 'text-[#171A35] font-semibold bg-[#ECECFA] border border-[#DFE1F2]'
                    : isCompleted
                    ? 'text-[#1E8E5A] hover:bg-[#FAF9FC]'
                    : 'text-[#737895] hover:bg-[#FAF9FC]'
                }`}
              >
                {isCompleted ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#1E8E5A]" />
                ) : (
                  <span
                    className={`font-mono text-[11px] ${
                      isActive ? 'text-[#7664E8] font-bold' : 'text-[#737895]'
                    }`}
                  >
                    0{stepNum}
                  </span>
                )}
                <span className="text-[11px] hidden sm:inline">
                  {label.split(' ')[1]}
                </span>
              </button>
            );
          })}
        </nav>
      </header>

      {/* 2. Main Step Content Area */}
      <main className="relative flex-1 flex flex-col items-center justify-start w-full px-3 sm:px-6 py-4 max-w-5xl mx-auto z-10">
        {/* Error Banner */}
        {errorMessage && (
          <div className="w-full mb-3 p-3 rounded-xl bg-[#FEECEE] border border-[#FCD6D9] text-xs text-[#D9383A] flex items-center justify-between gap-2 shadow-xs">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-[#D9383A] shrink-0" />
              <span>{errorMessage}</span>
            </div>
            <button
              type="button"
              onClick={() => setErrorMessage(null)}
              className="text-xs underline text-[#B82B2D]"
            >
              Dismiss
            </button>
          </div>
        )}

        <AnimatePresence mode="wait">
          <motion.div
            key={`step_${currentStep}`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.28, ease: [0.23, 1, 0.32, 1] }}
            className="w-full"
          >
            {currentStep === 1 && <Step1Requirements requirements={requirements} />}
            {currentStep === 2 && <Step2BrokenHandoff handoffItems={brokenHandoff} />}
            {currentStep === 3 && (
              <Step3ValidationResults
                validationData={validationData}
                isValidating={status === 'validating'}
              />
            )}
            {currentStep === 4 && (
              <Step4Repair
                repairs={repairs}
                isRepaired={isRepaired}
                onApplyRepairs={handleApplyRepairs}
                isRepairing={status === 'repairing'}
              />
            )}
            {currentStep === 5 && (
              <Step5Revalidation
                revalidationData={revalidationData}
                isRevalidating={status === 'revalidating'}
                onResetDemo={handleResetDemo}
              />
            )}
          </motion.div>
        </AnimatePresence>
      </main>

      {/* 3. Bottom Navigation Controls Bar */}
      <footer className="w-full bg-white/80 backdrop-blur-md border-t border-[#DFE1F2] sticky bottom-0 z-30 px-4 sm:px-6 py-3">
        <div className="max-w-5xl mx-auto flex items-center justify-between gap-3">
          {/* Back Button */}
          <button
            type="button"
            onClick={handleBack}
            disabled={currentStep === 1 || status === 'validating' || status === 'repairing' || status === 'revalidating'}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-[#737895] hover:text-[#171A35] bg-[#FAF9FC] hover:bg-white border border-[#DFE1F2] transition-all cursor-pointer shadow-xs disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back</span>
          </button>

          {/* Step Context Indicator */}
          <div className="text-center hidden sm:block">
            <span className="text-xs font-mono text-[#737895]">
              Step {currentStep} of 5 · {STEP_LABELS[currentStep - 1]}
            </span>
          </div>

          {/* Next Action Button */}
          <div>
            {currentStep === 1 && (
              <button
                type="button"
                onClick={handleNext}
                className="px-5 py-2 rounded-xl text-xs font-semibold bg-[#7664E8] hover:bg-[#6855DE] text-white transition-all shadow-xs flex items-center gap-1.5 cursor-pointer active:scale-[0.98]"
              >
                <span>Inspect Downstream Handoff</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}

            {currentStep === 2 && (
              <button
                type="button"
                onClick={handleRunValidation}
                disabled={status === 'validating'}
                className="px-5 py-2 rounded-xl text-xs font-semibold bg-[#7664E8] hover:bg-[#6855DE] text-white transition-all shadow-xs flex items-center gap-1.5 cursor-pointer active:scale-[0.98] disabled:opacity-50"
              >
                {status === 'validating' ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Validating…</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5 text-white" />
                    <span>Run Validator</span>
                  </>
                )}
              </button>
            )}

            {currentStep === 3 && (
              <button
                type="button"
                onClick={handleNext}
                className="px-5 py-2 rounded-xl text-xs font-semibold bg-[#7664E8] hover:bg-[#6855DE] text-white transition-all shadow-xs flex items-center gap-1.5 cursor-pointer active:scale-[0.98]"
              >
                <span>Proceed to Repair</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}

            {currentStep === 4 && (
              <button
                type="button"
                onClick={handleRunRevalidation}
                disabled={status === 'revalidating'}
                className="px-5 py-2 rounded-xl text-xs font-semibold bg-[#7664E8] hover:bg-[#6855DE] text-white transition-all shadow-xs flex items-center gap-1.5 cursor-pointer active:scale-[0.98] disabled:opacity-50"
              >
                {status === 'revalidating' ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Revalidating…</span>
                  </>
                ) : (
                  <>
                    <span>Revalidate Specification</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </button>
            )}

            {currentStep === 5 && (
              <button
                type="button"
                onClick={onExitDemo}
                className="px-5 py-2 rounded-xl text-xs font-semibold bg-[#7664E8] hover:bg-[#6855DE] text-white transition-all shadow-xs flex items-center gap-1.5 cursor-pointer active:scale-[0.98]"
              >
                <span>Complete Demo & Return to Live Mode</span>
              </button>
            )}
          </div>
        </div>
      </footer>
    </div>
  );
};
