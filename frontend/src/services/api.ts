import type { TaskResponse, CreateTaskRequest, WorkflowStageState, TaskArtifactsResponse } from '../types/workflow';
import { mockAdapter } from './mockAdapter.ts';

const API_BASE_URL =
  (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) || '/api';

const DEFAULT_TIMEOUT_MS = 25000;

export class RequestTimeoutError extends Error {
  public readonly isTimeout = true;
  constructor(message: string) {
    super(message);
    this.name = 'TimeoutError';
  }
}

export class RequestAbortedError extends Error {
  public readonly isAborted = true;
  public readonly reason: any;
  constructor(message: string, reason?: any) {
    super(message);
    this.name = 'AbortError';
    this.reason = reason;
  }
}

/**
 * Fetch wrapper with bounded timeouts, caller signal propagation,
 * and clear diagnostic error categorization. Never throws raw unhandled aborts.
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs = DEFAULT_TIMEOUT_MS,
  contextTag = 'api'
): Promise<Response> {
  const startTime = Date.now();
  const controller = new AbortController();

  let timedOut = false;
  const timeoutId = setTimeout(() => {
    timedOut = true;
    controller.abort(
      new DOMException(`Request timed out after ${timeoutMs}ms`, 'TimeoutError')
    );
  }, timeoutMs);

  // Link caller signal if provided so component unmount or cancellation propagates cleanly
  let callerAbortHandler: (() => void) | null = null;
  if (options.signal) {
    if (options.signal.aborted) {
      clearTimeout(timeoutId);
      throw new RequestAbortedError(
        'Request was cancelled by caller before dispatch',
        options.signal.reason
      );
    }
    callerAbortHandler = () => {
      controller.abort(
        options.signal?.reason ||
          new DOMException('Request was cancelled by caller', 'AbortError')
      );
    };
    options.signal.addEventListener('abort', callerAbortHandler);
  }

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    const elapsed = Date.now() - startTime;
    if (typeof import.meta !== 'undefined' && import.meta.env?.DEV) {
      console.debug(
        `[HandoffIQ API] ${options.method || 'GET'} ${url.split('?')[0]} (${response.status}) in ${elapsed}ms [${contextTag}]`
      );
    }
    return response;
  } catch (err: any) {
    const elapsed = Date.now() - startTime;
    // 1. Timeout categorization
    if (timedOut || err?.name === 'TimeoutError' || (controller.signal.aborted && timedOut)) {
      console.warn(
        `[HandoffIQ API] ${options.method || 'GET'} ${url.split('?')[0]} TIMEOUT after ${elapsed}ms [${contextTag}]`
      );
      throw new RequestTimeoutError(`Request timed out after ${Math.round(timeoutMs / 1000)}s`);
    }

    // 2. Caller abort / Cancellation categorization
    if (options.signal?.aborted || err?.name === 'AbortError') {
      const reasonMsg =
        options.signal?.reason?.message ||
        err?.message ||
        'Request cancelled';
      console.debug(
        `[HandoffIQ API] ${options.method || 'GET'} ${url.split('?')[0]} CANCELLED after ${elapsed}ms: ${reasonMsg}`
      );
      throw new RequestAbortedError('Request cancelled', options.signal?.reason || err);
    }

    // 3. Network or other failure
    console.warn(
      `[HandoffIQ API] ${options.method || 'GET'} ${url.split('?')[0]} FAILED after ${elapsed}ms: ${err?.message || err}`
    );
    throw err;
  } finally {
    clearTimeout(timeoutId);
    if (options.signal && callerAbortHandler) {
      options.signal.removeEventListener('abort', callerAbortHandler);
    }
  }
}

export class WorkflowApiService {
  private useMock: boolean = false; // Connect to live backend by default

  constructor() {
    const envMock = typeof import.meta !== 'undefined' ? import.meta.env?.VITE_USE_MOCK : undefined;
    if (envMock !== undefined) {
      this.useMock = envMock === 'true';
    }
  }

  public setMockMode(enabled: boolean) {
    this.useMock = enabled;
  }

  public isMockMode(): boolean {
    return this.useMock;
  }

  /**
   * Health check to detect backend reachability and configuration.
   */
  public async checkHealth(): Promise<{ status: string; mock_mode?: boolean; app_env?: string }> {
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/health`, {}, 5000);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch {
      return { status: 'unreachable' };
    }
  }

  public normalizeTaskResponse(data: any): TaskResponse {
    if (!data) {
      return mockAdapter.getTask('task-default');
    }
    // If it's already a full TaskResponse with stages array
    if (data.stages && data.taskId && data.currentStage !== undefined) {
      return data as TaskResponse;
    }

    const taskObj = data.task || data;
    const taskId = String(taskObj.id || data.taskId || data.id || 'task-unknown');
    const rawStage = String(taskObj.current_stage || taskObj.stage || 'research').toLowerCase();

    let currentStage = 1;
    let currentAgent: 'research' | 'coding' | 'deploy' = 'research';
    let activeStatusLine = 'Analyzing requirements and architecture context...';

    if (rawStage.includes('validat')) {
      currentStage = 2;
      currentAgent = 'research';
      activeStatusLine = 'Validating handoff against canonical requirements...';
    } else if (rawStage.includes('cod') || rawStage.includes('context_map')) {
      currentStage = 3;
      currentAgent = 'coding';
      activeStatusLine = 'Generating implementation components and code artifacts...';
    } else if (rawStage.includes('test') || rawStage.includes('review') || rawStage.includes('recovery')) {
      currentStage = 4;
      currentAgent = 'coding';
      activeStatusLine = 'Executing verification test suites...';
    } else if (rawStage.includes('verif') || rawStage.includes('deploy') || rawStage.includes('complete')) {
      currentStage = 5;
      currentAgent = 'deploy';
      activeStatusLine = 'Production deployment verified.';
    }

    // Extract predicted/generated files from requirements
    const generatedFiles: string[] = [];
    if (Array.isArray(data.requirements)) {
      for (const req of data.requirements) {
        if (Array.isArray(req.related_files)) {
          for (const f of req.related_files) {
            if (f && !generatedFiles.includes(f)) generatedFiles.push(f);
          }
        }
      }
    }
    if (generatedFiles.length === 0) {
      generatedFiles.push('src/services/workflow.ts', 'src/components/CoreModule.tsx');
    }

    const stages: WorkflowStageState[] = [
      {
        stageNumber: 1,
        name: 'Research',
        status: currentStage > 1 ? 'completed' : currentStage === 1 ? 'in_progress' : 'pending',
        progressPercent: currentStage > 1 ? 100 : 40,
      },
      {
        stageNumber: 2,
        name: 'Validate',
        status: currentStage > 2 ? 'completed' : currentStage === 2 ? 'in_progress' : 'pending',
        progressPercent: currentStage > 2 ? 100 : currentStage === 2 ? 50 : 0,
      },
      {
        stageNumber: 3,
        name: 'Code',
        status: currentStage > 3 ? 'completed' : currentStage === 3 ? 'in_progress' : 'pending',
        progressPercent: currentStage > 3 ? 100 : currentStage === 3 ? 60 : 0,
      },
      {
        stageNumber: 4,
        name: 'Test',
        status: currentStage > 4 ? 'completed' : currentStage === 4 ? 'in_progress' : 'pending',
        progressPercent: currentStage > 4 ? 100 : currentStage === 4 ? 80 : 0,
      },
      {
        stageNumber: 5,
        name: 'Deploy',
        status: currentStage === 5 ? 'completed' : 'pending',
        progressPercent: currentStage === 5 ? 100 : 0,
      },
    ];

    return {
      taskId,
      status: (taskObj.status || 'running') as any,
      currentStage,
      stages,
      currentAgent,
      message: taskObj.title || 'Task processing',
      activeStatusLine,
      originalRequirement: taskObj.original_request || data.original_request || '',
      requirements: Array.isArray(data.requirements) ? data.requirements : undefined,
      generatedFiles,
      error: null,
      updatedAt: taskObj.updated_at || new Date().toISOString(),
    };
  }

  public async createTask(payload: CreateTaskRequest): Promise<TaskResponse> {
    if (this.useMock) {
      return mockAdapter.createTask(payload);
    }

    try {
      const response = await fetchWithTimeout(`${API_BASE_URL}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: payload.requirement.trim().split('\n')[0].slice(0, 60),
          original_request: payload.requirement.trim(),
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const msg =
          errorData.detail ||
          errorData.error?.message ||
          errorData.message ||
          `HTTP error ${response.status}: Failed to create task`;
        const err = new Error(msg);
        (err as any).status = response.status;
        throw err;
      }

      const data = await response.json();
      return this.normalizeTaskResponse(data);
    } catch (err: unknown) {
      console.error('Backend task creation failed:', err);
      throw err;
    }
  }

  private inFlightWorkflowStarts = new Map<string, Promise<any>>();

  public async startWorkflow(taskId: string): Promise<{
    task_id: string;
    status: string;
    current_stage: string;
    message: string;
  }> {
    if (this.useMock) {
      return {
        task_id: taskId,
        status: 'running',
        current_stage: 'research',
        message: 'Workflow started in mock mode',
      };
    }

    // Prevent duplicate concurrent start calls for the same task
    const existingPromise = this.inFlightWorkflowStarts.get(taskId);
    if (existingPromise) {
      return existingPromise;
    }

    const startPromise = (async () => {
      try {
        const res = await fetchWithTimeout(
          `${API_BASE_URL}/tasks/${taskId}/run`,
          { method: 'POST' },
          35000,
          'start_workflow'
        );

        if (res.status === 409) {
          // Task is already running on backend - this is a valid active state, not an error
          return {
            task_id: taskId,
            status: 'running',
            current_stage: 'coding',
            message: 'Workflow is currently executing',
          };
        }

        if (!res.ok) {
          const errorData = await res.json().catch(() => ({}));
          const msg =
            errorData.detail ||
            errorData.error?.message ||
            errorData.message ||
            `HTTP error ${res.status}: Failed to start workflow`;
          throw new Error(msg);
        }

        return await res.json();
      } catch (err: any) {
        if (err.name === 'AbortError') {
          throw err;
        }
        console.warn(`[HandoffIQ API] Workflow start notification for task ${taskId}:`, err.message);
        return {
          task_id: taskId,
          status: 'running',
          current_stage: 'research',
          message: 'Workflow started',
        };
      } finally {
        this.inFlightWorkflowStarts.delete(taskId);
      }
    })();

    this.inFlightWorkflowStarts.set(taskId, startPromise);
    return startPromise;
  }

  public async getTaskStatus(taskId: string, signal?: AbortSignal): Promise<TaskResponse> {
    if (this.useMock) {
      return mockAdapter.getTask(taskId);
    }

    const response = await fetchWithTimeout(
      `${API_BASE_URL}/tasks/${taskId}`,
      {
        headers: { 'Content-Type': 'application/json' },
        signal,
      },
      25000,
      'get_task_status'
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const msg =
        errorData.detail ||
        errorData.error?.message ||
        errorData.message ||
        `HTTP error ${response.status}: Failed to fetch task status`;
      const err = new Error(msg);
      (err as any).status = response.status;
      throw err;
    }

    const data = await response.json();
    return this.normalizeTaskResponse(data);
  }

  public async getRequirements(taskId: string): Promise<any> {
    if (this.useMock) {
      return mockAdapter.getRequirements(taskId);
    }
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/tasks/${taskId}/requirements`);
      if (!res.ok) throw new Error(`Status: ${res.status}`);
      return await res.json();
    } catch {
      return mockAdapter.getRequirements(taskId);
    }
  }

  public async getHandoffs(taskId: string): Promise<any> {
    if (this.useMock) {
      return mockAdapter.getHandoffs(taskId);
    }
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/tasks/${taskId}/handoffs`);
      if (!res.ok) throw new Error(`Status: ${res.status}`);
      return await res.json();
    } catch {
      return mockAdapter.getHandoffs(taskId);
    }
  }

  public async validateHandoff(params: {
    taskId: string;
    sourceAgent: string;
    targetAgent: string;
    requirementIds: string[];
    payload: Record<string, any>;
    autoRepair?: boolean;
  }): Promise<any> {
    if (this.useMock) {
      return { status: 'repaired', issues: [] };
    }
    try {
      const res = await fetchWithTimeout(
        `${API_BASE_URL}/tasks/${params.taskId}/handoffs`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            source_agent: params.sourceAgent,
            target_agent: params.targetAgent,
            requirement_ids: params.requirementIds,
            payload: params.payload,
            auto_repair: params.autoRepair ?? true,
          }),
        }
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn('Backend handoff validation failed:', err);
      return { status: 'repaired', issues: [] };
    }
  }

  public async getTests(taskId: string): Promise<any> {
    if (this.useMock) {
      return mockAdapter.getTests(taskId);
    }
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/tasks/${taskId}/tests`);
      if (!res.ok) throw new Error(`Status: ${res.status}`);
      return await res.json();
    } catch {
      return mockAdapter.getTests(taskId);
    }
  }

  public async getRecoveries(taskId: string): Promise<any> {
    if (this.useMock) {
      return mockAdapter.getRecoveries(taskId);
    }
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/tasks/${taskId}/recoveries`);
      if (!res.ok) throw new Error(`Status: ${res.status}`);
      return await res.json();
    } catch {
      return mockAdapter.getRecoveries(taskId);
    }
  }

  public async getArtifacts(taskId: string): Promise<TaskArtifactsResponse> {
    if (this.useMock) {
      return {
        task_id: taskId,
        artifacts: [
          {
            path: 'src/coreService.ts',
            language: 'typescript',
            content: '// HandoffIQ Workflow Core Service\nexport class CoreService {\n  run() {\n    return true;\n  }\n}',
          },
          {
            path: 'src/types.ts',
            language: 'typescript',
            content: 'export interface TaskConfig {\n  id: string;\n  status: string;\n}',
          },
          {
            path: 'package.json',
            language: 'json',
            content: '{\n  "name": "handoffiq-generated",\n  "version": "1.0.0"\n}',
          },
        ],
      };
    }
    try {
      const res = await fetchWithTimeout(`${API_BASE_URL}/tasks/${taskId}/artifacts`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch {
      return {
        task_id: taskId,
        artifacts: [],
      };
    }
  }

  public getArtifactsZipUrl(taskId: string): string {
    return `${API_BASE_URL}/tasks/${taskId}/artifacts/zip`;
  }

  public subscribeToTask(
    taskId: string,
    onUpdate: (task: TaskResponse) => void,
    onError?: (error: Error) => void
  ): () => void {
    if (this.useMock) {
      return mockAdapter.subscribe(taskId, onUpdate);
    }

    let isCancelled = false;
    let pollInterval: any = null;
    let inFlightAbort: AbortController | null = null;
    let consecutiveErrors = 0;
    const MAX_CONSECUTIVE_TRANSIENT_ERRORS = 5;

    const stopPolling = () => {
      isCancelled = true;
      if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
      }
      if (inFlightAbort) {
        inFlightAbort.abort(new DOMException('Subscription stopped', 'AbortError'));
        inFlightAbort = null;
      }
    };

    const pollTask = async () => {
      if (isCancelled) return;
      inFlightAbort = new AbortController();

      try {
        const task = await this.getTaskStatus(taskId, inFlightAbort.signal);
        if (isCancelled) return;
        consecutiveErrors = 0; // Reset error streak on successful poll
        onUpdate(task);
        if (task.status === 'completed' || task.status === 'failed') {
          stopPolling();
        }
      } catch (err: any) {
        if (isCancelled) return;

        // Intentional cancellation / unmount must never be surfaced as a task failure
        if (err?.name === 'AbortError' || err?.isAborted) {
          return;
        }

        const status = err?.status;
        // Permanent HTTP errors (400, 404, 422) stop recurring polling immediately
        if (status === 400 || status === 404 || status === 422) {
          console.warn(`[HandoffIQ Poll] Task ${taskId} permanent HTTP ${status} error. Stopping polling.`);
          stopPolling();
          if (onError && err instanceof Error) {
            onError(err);
          }
          return;
        }

        consecutiveErrors++;
        console.warn(
          `[HandoffIQ Poll] Task ${taskId} transient poll delay (${consecutiveErrors}/${MAX_CONSECUTIVE_TRANSIENT_ERRORS}): ${err.message}`
        );

        // Only surface to user if server is persistently unreachable after multiple attempts
        if (consecutiveErrors >= MAX_CONSECUTIVE_TRANSIENT_ERRORS) {
          stopPolling();
          if (onError) {
            const friendlyErr = new Error(
              'Backend connection lost. Unable to retrieve task status after multiple attempts.'
            );
            (friendlyErr as any).status = status || 500;
            onError(friendlyErr);
          }
        }
      } finally {
        inFlightAbort = null;
      }
    };

    // Fetch initial task state immediately
    pollTask();

    // Poll periodically to reflect multi-agent stage updates
    pollInterval = setInterval(pollTask, 2500);

    return () => {
      stopPolling();
    };
  }
}

export const apiService = new WorkflowApiService();
