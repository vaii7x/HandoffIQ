import { useState, useEffect, useCallback } from 'react';
import { AGENT_CONFIGS } from './config/agents';
import { HANDOFF_CONFIGS } from './config/handoffs';
import { ScreenId, AgentId } from './types/agent';
import { TaskResponse } from './types/workflow';
import { apiService } from './services/api';
import { mockAdapter } from './services/mockAdapter';
import { AgentPage } from './components/AgentPage';
import { HandoffPage } from './components/Handoff/HandoffPage';
import { RequirementInputPage } from './components/RequirementInput/RequirementInputPage';
import { MutationLabPage } from './components/MutationLab/MutationLabPage';
import { BreakUiToggle } from './components/BreakUiToggle';

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
  lab: 'Mutation Lab',
};

export function App() {
  // Read stage/agent and taskId from URL search param if present, or default to 'input'
  const [activeTaskId, setActiveTaskId] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      return params.get('taskId') || 'task-demo-4401';
    }
    return 'task-demo-4401';
  });

  const [activeScreenId, setActiveScreenId] = useState<ScreenId>(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const stageParam = (params.get('stage') || params.get('agent')) as ScreenId;
      if (stageParam && (WORKFLOW_ORDER.includes(stageParam) || stageParam === 'lab')) {
        return stageParam;
      }
    }
    // Default entrypoint is the Requirement Input page
    return 'input';
  });

  const [task, setTask] = useState<TaskResponse | null>(null);
  const [isWorstCase, setIsWorstCase] = useState<boolean>(false);
  const [isMockMode, setIsMockMode] = useState<boolean>(true);

  // Update URL search param and backend adapter when screen changes
  const handleSelectScreen = useCallback((id: ScreenId) => {
    setActiveScreenId(id);
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      url.searchParams.set('stage', id);
      window.history.replaceState({}, '', url.toString());
    }
    mockAdapter.setScreen(id);
  }, []);

  const handleStartWorkflow = useCallback((newTaskId: string, _requirement: string) => {
    setActiveTaskId(newTaskId);
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      url.searchParams.set('taskId', newTaskId);
      url.searchParams.set('stage', 'research');
      window.history.replaceState({}, '', url.toString());
    }
    mockAdapter.setScreen('research');
    setActiveScreenId('research');
  }, []);

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

  // Keyboard navigation (ArrowLeft and ArrowRight)
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

  // Subscribe to task updates via API / Mock adapter
  useEffect(() => {
    apiService.setMockMode(isMockMode);
    const unsubscribe = apiService.subscribeToTask(
      activeTaskId,
      (updatedTask) => {
        setTask(updatedTask);
      },
      (err) => {
        console.error('Task subscription error:', err);
      }
    );

    return () => unsubscribe();
  }, [isMockMode, activeTaskId]);

  const prevName = hasPrev
    ? SCREEN_DISPLAY_NAMES[WORKFLOW_ORDER[currentIndex - 1]]
    : undefined;
  const nextName = hasNext
    ? SCREEN_DISPLAY_NAMES[WORKFLOW_ORDER[currentIndex + 1]]
    : undefined;

  return (
    <div className="relative min-h-screen bg-black text-white font-sans antialiased overflow-hidden">
      {/* 1. Initial Requirement Input Page */}
      {activeScreenId === 'input' && (
        <RequirementInputPage
          palette={AGENT_CONFIGS.research.palette}
          onStartWorkflow={handleStartWorkflow}
          onSelectScreen={handleSelectScreen}
          isMockMode={isMockMode}
          onToggleMockMode={(val) => {
            setIsMockMode(val);
            apiService.setMockMode(val);
          }}
        />
      )}

      {/* 2. Intermediate Handoff Pages (Validate & Test) */}
      {(activeScreenId === 'validate' || activeScreenId === 'test') && (
        <HandoffPage
          key={activeScreenId}
          config={HANDOFF_CONFIGS[activeScreenId as 'validate' | 'test']}
          task={task}
          onSelectScreen={handleSelectScreen}
          onPrev={handlePrev}
          onNext={handleNext}
          hasPrev={hasPrev}
          hasNext={hasNext}
          prevName={prevName}
          nextName={nextName}
        />
      )}

      {/* 3. Main Agent Pages (Research, Coding, Deploy) */}
      {(activeScreenId === 'research' ||
        activeScreenId === 'coding' ||
        activeScreenId === 'deploy') && (
        <AgentPage
          key={activeScreenId}
          config={AGENT_CONFIGS[activeScreenId as AgentId]}
          task={task}
          onSelectScreen={handleSelectScreen}
          onSelectAgent={(agentId) => handleSelectScreen(agentId)}
          onPrevAgent={handlePrev}
          onNextAgent={handleNext}
          hasPrev={hasPrev}
          hasNext={hasNext}
          prevName={prevName}
          nextName={nextName}
          isWorstCase={isWorstCase}
        />
      )}

      {/* 4. Handoff Mutation Lab */}
      {activeScreenId === 'lab' && (
        <MutationLabPage
          onSelectScreen={handleSelectScreen}
          palette={AGENT_CONFIGS.research.palette}
        />
      )}

      {/* Dev-only Adversarial Testing Bar (break-ui skill) */}
      <BreakUiToggle
        isWorstCase={isWorstCase}
        onToggleWorstCase={setIsWorstCase}
        isMockMode={isMockMode}
        onToggleMockMode={(val) => {
          setIsMockMode(val);
          apiService.setMockMode(val);
        }}
        onResetSimulation={() => {
          mockAdapter.setScreen(activeScreenId);
        }}
        onNewGoal={() => handleSelectScreen('input')}
        onOpenLab={() => handleSelectScreen('lab')}
      />
    </div>
  );
}

export default App;
