import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { motion, AnimatePresence, useReducedMotion, Variants } from 'framer-motion';
import { AGENT_CONFIGS } from './config/agents';
import { HANDOFF_CONFIGS } from './config/handoffs';
import { ScreenId, AgentId } from './types/agent';
import { TaskResponse } from './types/workflow';
import { apiService } from './services/api';
import { mockAdapter } from './services/mockAdapter';
import { AgentHeader } from './components/AgentHeader';
import { WorkflowStepper } from './components/WorkflowStepper';
import { AuroraBackground } from './components/AuroraBackground';
import { ParticleSphere } from './components/ParticleSphere/ParticleSphere';
import { AgentPage } from './components/AgentPage';
import { HandoffPage } from './components/Handoff/HandoffPage';
import { RequirementInputPage } from './components/RequirementInput/RequirementInputPage';
import { DemoModeView } from './components/Demo/DemoModeView';

const WORKFLOW_ORDER: ScreenId[] = [
  'input',
  'research',
  'validate',
  'coding',
  'test',
  'deploy',
];

const SCREEN_DISPLAY_NAMES: Record<ScreenId, string> = {
  input: 'Input Goal',
  research: '01 Research',
  validate: '02 Validate',
  coding: '03 Code',
  test: '04 Test',
  deploy: '05 Deploy',
};

export function App() {
  // Read stage/agent and taskId from URL search param if present
  const [activeTaskId, setActiveTaskId] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const paramId = params.get('taskId');
      if (paramId) return paramId;
      const stageParam = params.get('stage') || params.get('agent');
      if (stageParam && stageParam !== 'input') {
        return localStorage.getItem('handoffiq_active_task_id') || '';
      }
    }
    return '';
  });

  const [activeScreenId, setActiveScreenId] = useState<ScreenId>(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const stageParam = (params.get('stage') || params.get('agent')) as string;
      if (stageParam && WORKFLOW_ORDER.includes(stageParam as ScreenId)) {
        return stageParam as ScreenId;
      }
      // Cleanly redirect legacy/removed Mutation Lab route to handoff validation
      if (stageParam === 'lab') {
        const url = new URL(window.location.href);
        url.searchParams.set('stage', 'validate');
        window.history.replaceState({}, '', url.toString());
        return 'validate';
      }
    }
    // The root route '/' always displays the Task Input page immediately
    return 'input';
  });

  const [task, setTask] = useState<TaskResponse | null>(null);
  const [isMockMode, setIsMockMode] = useState<boolean>(() => {
    return import.meta.env.VITE_USE_MOCK === 'true';
  });
  const [isDemoMode, setIsDemoMode] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      return params.get('mode') === 'demo';
    }
    return false;
  });

  const handleOpenDemo = useCallback(() => {
    setIsDemoMode(true);
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      url.searchParams.set('mode', 'demo');
      window.history.replaceState({}, '', url.toString());
    }
  }, []);

  const handleExitDemo = useCallback(() => {
    setIsDemoMode(false);
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      url.searchParams.delete('mode');
      window.history.replaceState({}, '', url.toString());
    }
  }, []);

  // Track validation and coding data readiness for active task
  const [validationDataReady, setValidationDataReady] = useState<boolean>(false);
  const [codingDataReady, setCodingDataReady] = useState<boolean>(false);

  // Update URL search param and backend adapter when screen changes
  const handleSelectScreen = useCallback((id: ScreenId) => {
    setActiveScreenId(id);
    if (id === 'input') {
      // Clean URL and synchronously wipe active task state when returning to input
      setActiveTaskId('');
      setTask(null);
      setValidationDataReady(false);
      setCodingDataReady(false);
      localStorage.removeItem('handoffiq_active_task_id');
      if (typeof window !== 'undefined') {
        const url = new URL(window.location.href);
        url.search = '';
        window.history.replaceState({}, '', url.pathname);
      }
    } else if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      url.searchParams.set('stage', id);
      window.history.replaceState({}, '', url.toString());
    }
    mockAdapter.setScreen(id);
  }, []);

  // Start time and progression guards per task
  const researchStartTimesRef = useRef<Record<string, number>>({});
  const hasAutoAdvancedRef = useRef<Record<string, boolean>>({});
  const codingStartTimesRef = useRef<Record<string, number>>({});
  const hasAutoAdvancedCodingRef = useRef<Record<string, boolean>>({});

  const handleStartWorkflow = useCallback((newTaskId: string, _requirement: string) => {
    setActiveTaskId(newTaskId);
    setTask(null); // Synchronously clear previous task state to prevent any data leak
    setValidationDataReady(false);
    setCodingDataReady(false);
    researchStartTimesRef.current[newTaskId] = Date.now();
    hasAutoAdvancedRef.current[newTaskId] = false;
    codingStartTimesRef.current = {};
    hasAutoAdvancedCodingRef.current = {};

    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      url.searchParams.set('taskId', newTaskId);
      url.searchParams.set('stage', 'research');
      window.history.replaceState({}, '', url.toString());
      localStorage.setItem('handoffiq_active_task_id', newTaskId);
    }

    // Trigger real backend workflow execution
    apiService.startWorkflow(newTaskId).catch((err) => {
      console.warn('Backend workflow start notification:', err);
    });
    mockAdapter.setScreen('research');
    setActiveScreenId('research');
  }, []);

  const handleRetryWorkflow = useCallback(async () => {
    if (!activeTaskId) return;

    // Reset error state synchronously
    setTask((prev) =>
      prev
        ? {
            ...prev,
            status: 'running',
            error: undefined,
            activeStatusLine: 'Retrying code generation and verification…',
          }
        : null
    );
    setCodingDataReady(false);
    codingStartTimesRef.current[activeTaskId] = Date.now();
    hasAutoAdvancedCodingRef.current[activeTaskId] = false;

    try {
      await apiService.startWorkflow(activeTaskId);
      const refreshed = await apiService.getTaskStatus(activeTaskId);
      setTask(refreshed);
    } catch (err: any) {
      console.warn('Retry workflow notification:', err);
      setTask((prev) =>
        prev
          ? {
              ...prev,
              status: 'failed',
              error: err?.message || 'Retry attempt failed. Inspect backend logs.',
              activeStatusLine: 'Generation retry failed.',
            }
          : null
      );
    }
  }, [activeTaskId]);

  const currentIndex = WORKFLOW_ORDER.indexOf(activeScreenId);
  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex < WORKFLOW_ORDER.length - 1;

  const handlePrev = useCallback(() => {
    if (hasPrev) {
      handleSelectScreen(WORKFLOW_ORDER[currentIndex - 1]);
    }
  }, [currentIndex, hasPrev, handleSelectScreen]);

  const handleNext = useCallback(() => {
    if (hasNext) {
      handleSelectScreen(WORKFLOW_ORDER[currentIndex + 1]);
    }
  }, [currentIndex, hasNext, handleSelectScreen]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }
      if (e.key === 'ArrowLeft') {
        handlePrev();
      } else if (e.key === 'ArrowRight') {
        handleNext();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handlePrev, handleNext]);

  // Subscribe to task updates via API / Mock adapter when an active task is present
  // Note: Only depends on [isMockMode, activeTaskId] so navigation across screens does not tear down polling
  useEffect(() => {
    apiService.setMockMode(isMockMode);
    if (!activeTaskId || activeScreenId === 'input') {
      return;
    }

    const unsubscribe = apiService.subscribeToTask(
      activeTaskId,
      (updatedTask) => {
        // Strict task isolation: discard any update not matching activeTaskId
        if (updatedTask.taskId !== activeTaskId && !activeTaskId.includes(updatedTask.taskId)) {
          return;
        }
        setTask(updatedTask);

        // If the task ID resolved to a canonical stored UUID, update activeTaskId and sync URL/storage
        if (updatedTask.taskId && updatedTask.taskId !== activeTaskId) {
          setActiveTaskId(updatedTask.taskId);
          localStorage.setItem('handoffiq_active_task_id', updatedTask.taskId);
          if (typeof window !== 'undefined') {
            const url = new URL(window.location.href);
            url.searchParams.set('taskId', updatedTask.taskId);
            window.history.replaceState({}, '', url.toString());
          }
        }
      },
      (err) => {
        console.error('Task subscription error:', err);
        setTask((prev) => {
          if (!prev) return null;
          return {
            ...prev,
            taskId: activeTaskId,
            status: 'failed',
            currentStage: prev.currentStage || 1,
            message: 'Task Retrieval Failed',
            activeStatusLine: err.message || 'Could not retrieve task from backend.',
            error: err.message || 'Task retrieval failure',
            updatedAt: new Date().toISOString(),
          };
        });
      }
    );

    return () => unsubscribe();
  }, [isMockMode, activeTaskId]);

  useEffect(() => {
    if (activeScreenId === 'research' && activeTaskId) {
      if (!researchStartTimesRef.current[activeTaskId]) {
        researchStartTimesRef.current[activeTaskId] = Date.now();
      }
    }
  }, [activeScreenId, activeTaskId]);

  // Check backend handoff validation data readiness before allowing transition to Validation
  useEffect(() => {
    let isSubscribed = true;
    if (activeScreenId !== 'research' || !activeTaskId || !task) {
      return;
    }

    // Only inspect when task matches activeTaskId and has extracted requirements
    if (task.taskId !== activeTaskId) {
      return;
    }

    const hasValidRequirements =
      Array.isArray(task.requirements) && task.requirements.length > 0;

    if (!hasValidRequirements) {
      return;
    }

    let pollTimer: any = null;

    const checkHandoffReadiness = async () => {
      try {
        const res = await apiService.getHandoffs(activeTaskId);
        if (!isSubscribed) return;
        const handoffs = res?.handoffs || [];
        if (handoffs.length > 0 || task.currentStage >= 2) {
          setValidationDataReady(true);
          return;
        }
        pollTimer = setTimeout(checkHandoffReadiness, 1000);
      } catch (err) {
        if (!isSubscribed) return;
        console.warn('Handoff readiness poll retry:', err);
        pollTimer = setTimeout(checkHandoffReadiness, 1500);
      }
    };

    checkHandoffReadiness();

    return () => {
      isSubscribed = false;
      if (pollTimer) clearTimeout(pollTimer);
    };
  }, [activeScreenId, activeTaskId, task?.requirements?.length, task?.currentStage]);

  // Auto-progression from Research to Validation ONLY when real validation data is verified
  // Preserves minimum 4-second research display time from the start of Research stage
  useEffect(() => {
    if (activeScreenId !== 'research' || !activeTaskId || !task) {
      return;
    }

    // Verify task matches activeTaskId to avoid stale previous task state
    if (task.taskId !== activeTaskId) {
      return;
    }

    // Do not navigate if extraction failed or error exists
    if (task.error || task.status === 'failed') {
      return;
    }

    // STRICT REQUIREMENT: Only navigate after validation data is confirmed ready
    if (!validationDataReady) {
      return;
    }

    if (hasAutoAdvancedRef.current[activeTaskId]) {
      return;
    }

    const startTime = researchStartTimesRef.current[activeTaskId] || Date.now();
    const elapsed = Date.now() - startTime;
    const remainingDelay = Math.max(0, 4000 - elapsed);

    hasAutoAdvancedRef.current[activeTaskId] = true;

    const timer = setTimeout(() => {
      if (activeScreenId === 'research') {
        handleSelectScreen('validate');
      }
    }, remainingDelay);

    return () => clearTimeout(timer);
  }, [activeScreenId, activeTaskId, task, validationDataReady, handleSelectScreen]);

  // Track coding screen entry timestamp per task
  useEffect(() => {
    if (activeScreenId === 'coding' && activeTaskId) {
      if (!codingStartTimesRef.current[activeTaskId]) {
        codingStartTimesRef.current[activeTaskId] = Date.now();
      }
    }
  }, [activeScreenId, activeTaskId]);

  // Check code generation artifacts readiness before permitting transition to Testing
  useEffect(() => {
    let isSubscribed = true;
    if (activeScreenId !== 'coding' || !activeTaskId || !task) {
      return;
    }
    if (task.taskId !== activeTaskId) {
      return;
    }

    let pollTimer: any = null;

    const checkCodingReadiness = async () => {
      try {
        const res = await apiService.getArtifacts(activeTaskId);
        if (!isSubscribed) return;
        const artifacts = res?.artifacts || [];
        if (artifacts.length > 0 || task.currentStage >= 4 || task.status === 'completed') {
          setCodingDataReady(true);
          return;
        }
        pollTimer = setTimeout(checkCodingReadiness, 1000);
      } catch (err) {
        if (!isSubscribed) return;
        console.warn('Artifact readiness poll retry:', err);
        pollTimer = setTimeout(checkCodingReadiness, 1500);
      }
    };

    checkCodingReadiness();

    return () => {
      isSubscribed = false;
      if (pollTimer) clearTimeout(pollTimer);
    };
  }, [activeScreenId, activeTaskId, task?.currentStage, task?.status]);

  // Auto-advance from Coding to Testing ONLY when artifacts are verified
  // Preserves minimum 4-second display duration from entering Coding stage
  useEffect(() => {
    if (activeScreenId !== 'coding' || !activeTaskId || !task) {
      return;
    }
    if (task.taskId !== activeTaskId) {
      return;
    }
    // Never advance if generation failed or error occurred
    if (task.error || task.status === 'failed') {
      return;
    }
    // STRICT REQUIREMENT: Only navigate after real code generation is verified ready
    if (!codingDataReady) {
      return;
    }
    if (hasAutoAdvancedCodingRef.current[activeTaskId]) {
      return;
    }

    const startTime = codingStartTimesRef.current[activeTaskId] || Date.now();
    const elapsed = Date.now() - startTime;
    const remainingDelay = Math.max(0, 4000 - elapsed);

    hasAutoAdvancedCodingRef.current[activeTaskId] = true;

    const timer = setTimeout(() => {
      if (activeScreenId === 'coding') {
        handleSelectScreen('test');
      }
    }, remainingDelay);

    return () => clearTimeout(timer);
  }, [activeScreenId, activeTaskId, task, codingDataReady, handleSelectScreen]);

  const prefersReducedMotion = useReducedMotion() ?? false;

  // Genuine Milestone Shimmer Trigger
  const [activeMilestone, setActiveMilestone] = useState<string | null>(null);

  useEffect(() => {
    if (validationDataReady) {
      setActiveMilestone('validation_ready');
      const timer = setTimeout(() => setActiveMilestone(null), 1400);
      return () => clearTimeout(timer);
    }
  }, [validationDataReady]);

  useEffect(() => {
    if (codingDataReady) {
      setActiveMilestone('coding_ready');
      const timer = setTimeout(() => setActiveMilestone(null), 1400);
      return () => clearTimeout(timer);
    }
  }, [codingDataReady]);

  useEffect(() => {
    if (task?.status === 'completed') {
      setActiveMilestone('completed');
      const timer = setTimeout(() => setActiveMilestone(null), 1400);
      return () => clearTimeout(timer);
    }
  }, [task?.status]);

  const currentPalette = useMemo(() => {
    switch (activeScreenId) {
      case 'validate':
        return HANDOFF_CONFIGS.validate.palette;
      case 'coding':
        return AGENT_CONFIGS.coding.palette;
      case 'test':
        return HANDOFF_CONFIGS.test.palette;
      case 'deploy':
        return AGENT_CONFIGS.deploy.palette;
      case 'research':
      case 'input':
      default:
        return AGENT_CONFIGS.research.palette;
    }
  }, [activeScreenId]);

  const currentStageNumber = useMemo(() => {
    switch (activeScreenId) {
      case 'research':
        return 1;
      case 'validate':
        return 2;
      case 'coding':
        return 3;
      case 'test':
        return 4;
      case 'deploy':
        return 5;
      case 'input':
      default:
        return 0;
    }
  }, [activeScreenId]);

  const stageTransitionVariants: Variants = {
    initial: (reduced: boolean) => ({
      opacity: 0,
      y: reduced ? 0 : 14,
    }),
    animate: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.38,
        ease: [0.23, 1, 0.32, 1],
      },
    },
    exit: (reduced: boolean) => ({
      opacity: 0,
      y: reduced ? 0 : -10,
      transition: {
        duration: 0.18,
        ease: [0.23, 1, 0.32, 1],
      },
    }),
  };

  const prevName = hasPrev
    ? SCREEN_DISPLAY_NAMES[WORKFLOW_ORDER[currentIndex - 1]]
    : undefined;
  const nextName = hasNext
    ? SCREEN_DISPLAY_NAMES[WORKFLOW_ORDER[currentIndex + 1]]
    : undefined;

  const isSphereHeroStage = activeScreenId === 'research' || activeScreenId === 'coding';

  if (isDemoMode) {
    return (
      <div className="relative min-h-screen bg-[#FAF9FC] text-[#171A35] font-sans antialiased overflow-x-hidden flex flex-col justify-between select-none">
        <AuroraBackground stage="validate" milestone={null} />
        <DemoModeView palette={currentPalette} onExitDemo={handleExitDemo} />
      </div>
    );
  }

  return (
    <div className="relative min-h-screen bg-[#FAF9FC] text-[#171A35] font-sans antialiased overflow-x-hidden flex flex-col justify-between select-none">
      {/* 1. Layer 1 & 2: Persistent Flowing Aurora Background & Ambient Radiance */}
      <AuroraBackground stage={activeScreenId} milestone={activeMilestone} />

      {/* 2. Layer 4: Persistent Top Navigation Shell */}
      <div className="w-full z-30 shrink-0">
        <AgentHeader
          palette={currentPalette}
          onSelectScreen={handleSelectScreen}
          activeScreen={activeScreenId}
        />
        <WorkflowStepper
          activeStageNumber={currentStageNumber}
          palette={currentPalette}
          onSelectScreen={handleSelectScreen}
          isEntryPage={activeScreenId === 'input'}
        />
      </div>

      {/* 3. Layer 3: Persistent Central Particle Sphere with Stage Transition Accent */}
      <div
        className={`w-full transition-all duration-500 ease-out flex items-center justify-center ${
          isSphereHeroStage
            ? 'relative z-10 opacity-100 py-1'
            : activeScreenId === 'input'
            ? 'relative z-10 opacity-90 py-0.5 sm:py-1'
            : 'h-0 opacity-0 overflow-hidden pointer-events-none'
        }`}
        aria-hidden={!isSphereHeroStage && activeScreenId !== 'input'}
      >
        <motion.div
          key={`sphere_accent_${activeScreenId}`}
          initial={{
            scale: prefersReducedMotion ? 1 : 0.97,
            filter: prefersReducedMotion ? 'none' : 'brightness(1.08)',
          }}
          animate={{ scale: 1, filter: 'brightness(1.0)' }}
          transition={{ duration: 0.45, ease: [0.23, 1, 0.32, 1] }}
          className="pointer-events-none"
        >
          <ParticleSphere
            palette={currentPalette}
            compact={activeScreenId === 'input'}
          />
        </motion.div>
      </div>

      {/* 4. Layer 4: Smooth Stage Content Transitions (AnimatePresence) */}
      <main className={`relative flex-1 flex flex-col items-center justify-start w-full z-20 px-2 sm:px-4 ${activeScreenId === 'input' ? 'py-1 sm:py-1.5' : 'py-2'}`}>
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={`${activeScreenId}_${activeTaskId || 'none'}`}
            custom={prefersReducedMotion}
            variants={stageTransitionVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            className={`w-full flex-1 flex flex-col items-center ${activeScreenId === 'input' ? 'justify-start' : 'justify-center'}`}
          >
            {/* 1. Initial Task Input Page (Default on root '/') */}
            {activeScreenId === 'input' && (
              <RequirementInputPage
                palette={currentPalette}
                onStartWorkflow={handleStartWorkflow}
                onSelectScreen={handleSelectScreen}
                isMockMode={isMockMode}
                onToggleMockMode={(val) => {
                  setIsMockMode(val);
                  apiService.setMockMode(val);
                }}
                onOpenDemo={handleOpenDemo}
                hideChrome={true}
                hideBackground={true}
                hideSphere={true}
              />
            )}

            {/* 2. Intermediate Handoff Pages (Validate & Test) */}
            {(activeScreenId === 'validate' || activeScreenId === 'test') && (
              <HandoffPage
                config={HANDOFF_CONFIGS[activeScreenId as 'validate' | 'test']}
                task={task}
                onSelectScreen={handleSelectScreen}
                onPrev={handlePrev}
                onNext={handleNext}
                hasPrev={hasPrev}
                hasNext={hasNext}
                prevName={prevName}
                nextName={nextName}
                hideChrome={true}
                hideBackground={true}
              />
            )}

            {/* 3. Main Agent Pages (Research, Coding, Deploy) */}
            {(activeScreenId === 'research' ||
              activeScreenId === 'coding' ||
              activeScreenId === 'deploy') && (
              <AgentPage
                config={AGENT_CONFIGS[activeScreenId as AgentId]}
                task={task}
                onSelectScreen={handleSelectScreen}
                onSelectAgent={(agentId) => handleSelectScreen(agentId)}
                onPrevAgent={handlePrev}
                onNextAgent={handleNext}
                onRetry={handleRetryWorkflow}
                hasPrev={hasPrev}
                hasNext={hasNext}
                prevName={prevName}
                nextName={nextName}
                hideChrome={true}
                hideBackground={true}
                hideSphere={true}
              />
            )}
          </motion.div>
        </AnimatePresence>
      </main>

      {/* Subtle bottom footer bar */}
      <footer className={`z-10 ${activeScreenId === 'input' ? 'h-2 sm:h-3' : 'h-4'}`} />
    </div>
  );
}

export default App;
