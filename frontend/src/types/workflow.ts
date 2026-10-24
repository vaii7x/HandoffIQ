export type TaskStatus =
  | 'queued'
  | 'running'
  | 'awaiting_review'
  | 'completed'
  | 'failed';

export interface CreateTaskRequest {
  requirement: string;
  framework?: string;
  constraints?: string;
  autoRepair?: boolean;
  demoMode?: boolean;
}

export interface WorkflowStageState {
  stageNumber: number;
  name: string; // 'Research' | 'Validate' | 'Code' | 'Test' | 'Deploy'
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  startedAt?: string;
  completedAt?: string;
  progressPercent: number; // 0 to 100
  detailMessage?: string;
}

export interface TaskResponse {
  taskId: string;
  status: TaskStatus;
  currentStage: number; // 1 to 5
  stages: WorkflowStageState[];
  currentAgent: 'research' | 'coding' | 'deploy';
  message: string;
  activeStatusLine: string;
  originalRequirement?: string;
  generatedFiles?: string[];
  error?: string | null;
  updatedAt: string;
}
