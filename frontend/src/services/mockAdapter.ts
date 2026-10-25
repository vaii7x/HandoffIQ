import type { TaskResponse, TaskStatus, WorkflowStageState } from '../types/workflow';
import { AGENT_CONFIGS } from '../config/agents.ts';
import { HANDOFF_CONFIGS } from '../config/handoffs.ts';
import type { AgentId, ScreenId } from '../types/agent';

class MockWorkflowAdapter {
  private currentScreen: ScreenId = 'research';
  private currentAgent: AgentId = 'research';
  private currentStage: number = 1;
  private progress: number = 40;
  private activeStatusIndex: number = 0;
  private status: TaskStatus = 'running';
  private activeTaskId: string = 'task-demo-4401';
  private originalRequirement: string = 'Build a high-reliability distributed multi-agent system with real-time handoff verification, WebGL visualization, and automated self-healing test execution.';
  private listeners: Set<(task: TaskResponse) => void> = new Set();
  private timer: number | null = null;

  constructor() {
    this.startSimulation();
  }

  public createTask(payload: { requirement: string; framework?: string; constraints?: string }): TaskResponse {
    this.activeTaskId =
      typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : `task-${Math.random().toString(36).substring(2, 9)}`;
    this.originalRequirement = payload.requirement;
    this.currentScreen = 'research';
    this.currentAgent = 'research';
    this.currentStage = 1;
    this.progress = 25;
    this.status = 'running';
    this.activeStatusIndex = 0;
    const task = this.getTask(this.activeTaskId);
    this.notify();
    return task;
  }

  public setScreen(screenId: ScreenId) {
    this.currentScreen = screenId;
    if (screenId === 'research') {
      this.currentAgent = 'research';
      this.currentStage = 1;
      this.progress = 40;
    } else if (screenId === 'validate') {
      this.currentAgent = 'research';
      this.currentStage = 2;
      this.progress = 60;
    } else if (screenId === 'coding') {
      this.currentAgent = 'coding';
      this.currentStage = 3;
      this.progress = 60;
    } else if (screenId === 'test') {
      this.currentAgent = 'coding';
      this.currentStage = 4;
      this.progress = 85;
    } else if (screenId === 'deploy') {
      this.currentAgent = 'deploy';
      this.currentStage = 5;
      this.progress = 100;
    }
    this.activeStatusIndex = 0;
    this.notify();
  }

  public setAgent(agentId: AgentId) {
    this.setScreen(agentId);
  }

  public setStage(stageNum: number) {
    this.currentStage = stageNum;
    if (stageNum === 1) this.setScreen('research');
    else if (stageNum === 2) this.setScreen('validate');
    else if (stageNum === 3) this.setScreen('coding');
    else if (stageNum === 4) this.setScreen('test');
    else if (stageNum === 5) this.setScreen('deploy');
  }

  public getRequirements(_taskId: string) {
    return {
      total: 12,
      preserved: 10,
      missing: 1,
      removed: 1,
      added: 1,
      altered: 1,
      discrepancies: HANDOFF_CONFIGS.validate.discrepancies,
    };
  }

  public getHandoffs(taskId: string) {
    const rawDiscs = HANDOFF_CONFIGS.validate.discrepancies || [];
    const issues = rawDiscs.map((d, i) => ({
      id: d.id || `issue-${i + 1}`,
      requirement_id: d.requirementId,
      issue_type:
        d.type === 'missing'
          ? 'omission'
          : d.type === 'altered'
          ? 'weakened_constraint'
          : d.type === 'removed'
          ? 'contradiction'
          : 'semantic_drift',
      severity: d.severity || 'medium',
      description: d.originalText,
      original_value: d.originalText,
      observed_value: d.receivedText,
      repair_status: 'repaired',
      evidence: [d.evidence || 'Contract assertion audit against canonical spec'],
    }));

    return {
      status: 'ready_for_coding',
      checkRows: HANDOFF_CONFIGS.validate.checkRows,
      summary: HANDOFF_CONFIGS.validate.decision.description,
      handoffs: [
        {
          id: `handoff-${(taskId || 'demo').slice(0, 8)}`,
          task_id: taskId,
          source_agent: 'researcher',
          target_agent: 'coder',
          status: 'repaired',
          requirement_ids: ['R001', 'R002', 'R003', 'R004', 'R005'],
          payload: {
            architecture_spec: 'spec_v1.md',
            components: ['CoreService', 'StorageAdapter'],
          },
          issues,
          created_at: new Date().toISOString(),
        },
      ],
    };
  }

  public getTests(taskId: string) {
    const canonReqs = [
      { id: 'R001', name: 'Core Functionality Verification' },
      { id: 'R002', name: 'Interface & Contract Assertion' },
      { id: 'R003', name: 'Error Handling & Edge Cases' },
    ];
    const cases = canonReqs.map((r, i) => ({
      id: `test-${i + 1}`,
      name: `test_verification_${r.id.toLowerCase()}`,
      tool: 'workspace_verifier',
      status: 'passed' as const,
      duration: `${15 + i * 4}ms`,
      outputSnippet: `PASS: Requirement ${r.id} (${r.name}) verified against generated source files for task ${taskId.slice(0, 8)}.`,
    }));

    return {
      passed: cases.length,
      failed: 0,
      removed: 0,
      added: 0,
      testCases: cases,
      failures: [],
      tests: cases,
    };
  }

  public getRecoveries(_taskId: string) {
    return {
      repairsApplied: 0,
      repairs: [],
    };
  }

  public getTask(taskId: string): TaskResponse {
    const isValidate = this.currentScreen === 'validate';
    const isTest = this.currentScreen === 'test';

    const stages: WorkflowStageState[] = [
      {
        stageNumber: 1,
        name: 'Research',
        status:
          this.currentStage > 1
            ? 'completed'
            : this.currentStage === 1
            ? 'in_progress'
            : 'pending',
        progressPercent: this.currentStage > 1 ? 100 : this.progress,
      },
      {
        stageNumber: 2,
        name: 'Validate',
        status:
          this.currentStage > 2
            ? 'completed'
            : this.currentStage === 2
            ? 'in_progress'
            : 'pending',
        progressPercent: this.currentStage > 2 ? 100 : this.currentStage === 2 ? 80 : 0,
      },
      {
        stageNumber: 3,
        name: 'Code',
        status:
          this.currentStage > 3
            ? 'completed'
            : this.currentStage === 3
            ? 'in_progress'
            : 'pending',
        progressPercent: this.currentStage > 3 ? 100 : this.currentStage === 3 ? this.progress : 0,
      },
      {
        stageNumber: 4,
        name: 'Test',
        status:
          this.currentStage > 4
            ? 'completed'
            : this.currentStage === 4
            ? 'in_progress'
            : 'pending',
        progressPercent: this.currentStage > 4 ? 100 : this.currentStage === 4 ? 85 : 0,
      },
      {
        stageNumber: 5,
        name: 'Deploy',
        status:
          this.currentStage === 5
            ? 'in_progress'
            : 'pending',
        progressPercent: this.currentStage === 5 ? this.progress : 0,
      },
    ];

    let activeStatusLine = '';
    if (isValidate) {
      activeStatusLine = HANDOFF_CONFIGS.validate.defaultStatusText;
    } else if (isTest) {
      activeStatusLine = HANDOFF_CONFIGS.test.defaultStatusText;
    } else {
      const config = AGENT_CONFIGS[this.currentAgent];
      activeStatusLine = config.defaultStatus;
    }

    const currentMsg = isValidate
      ? HANDOFF_CONFIGS.validate.supportingText
      : isTest
      ? HANDOFF_CONFIGS.test.supportingText
      : AGENT_CONFIGS[this.currentAgent].supportingText;

    return {
      taskId: taskId || 'task-demo-4401',
      status: this.status,
      currentStage: this.currentStage,
      stages,
      currentAgent: this.currentAgent,
      message: currentMsg,
      activeStatusLine,
      originalRequirement: this.originalRequirement,
      generatedFiles:
        this.currentAgent === 'coding' || isTest
          ? ['src/components/ParticleSphere.tsx', 'src/services/api.ts']
          : undefined,
      error: null,
      updatedAt: new Date().toISOString(),
    };
  }

  public subscribe(
    taskId: string,
    callback: (task: TaskResponse) => void
  ): () => void {
    this.listeners.add(callback);
    callback(this.getTask(taskId));
    return () => {
      this.listeners.delete(callback);
    };
  }

  private notify() {
    const task = this.getTask('task-demo-4401');
    this.listeners.forEach((cb) => cb(task));
  }

  private startSimulation() {
    if (typeof window !== 'undefined') {
      this.timer = window.setInterval(() => {
        this.activeStatusIndex = (this.activeStatusIndex + 1) % 5;
        this.notify();
      }, 4000);
    }
  }

  public destroy() {
    if (this.timer) clearInterval(this.timer);
  }
}

export const mockAdapter = new MockWorkflowAdapter();
