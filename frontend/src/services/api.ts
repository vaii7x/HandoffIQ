import { TaskResponse, CreateTaskRequest } from '../types/workflow';
import { mockAdapter } from './mockAdapter';

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export class WorkflowApiService {
  private useMock: boolean = true; // Defaults to seamless interactive demo mode

  constructor() {
    const envMock = import.meta.env.VITE_USE_MOCK;
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

  public async createTask(payload: CreateTaskRequest): Promise<TaskResponse> {
    if (this.useMock) {
      return mockAdapter.createTask(payload);
    }

    try {
      const response = await fetch(`${API_BASE_URL}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail ||
            errorData.message ||
            `HTTP error ${response.status}: Failed to create task`
        );
      }

      return await response.json();
    } catch (err: any) {
      console.warn('Backend task creation failed:', err);
      throw err;
    }
  }

  public async getTaskStatus(taskId: string): Promise<TaskResponse> {
    if (this.useMock) {
      return mockAdapter.getTask(taskId);
    }

    try {
      const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (err) {
      console.warn('Backend unavailable, falling back to mock adapter:', err);
      return mockAdapter.getTask(taskId);
    }
  }

  public async getRequirements(taskId: string): Promise<any> {
    if (this.useMock) {
      return mockAdapter.getRequirements(taskId);
    }
    try {
      const res = await fetch(`${API_BASE_URL}/tasks/${taskId}/requirements`);
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
      const res = await fetch(`${API_BASE_URL}/tasks/${taskId}/handoffs`);
      if (!res.ok) throw new Error(`Status: ${res.status}`);
      return await res.json();
    } catch {
      return mockAdapter.getHandoffs(taskId);
    }
  }

  public async getTests(taskId: string): Promise<any> {
    if (this.useMock) {
      return mockAdapter.getTests(taskId);
    }
    try {
      const res = await fetch(`${API_BASE_URL}/tasks/${taskId}/tests`);
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
      const res = await fetch(`${API_BASE_URL}/tasks/${taskId}/recoveries`);
      if (!res.ok) throw new Error(`Status: ${res.status}`);
      return await res.json();
    } catch {
      return mockAdapter.getRecoveries(taskId);
    }
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
    let sse: EventSource | null = null;

    try {
      sse = new EventSource(`${API_BASE_URL}/tasks/${taskId}/events`);
      sse.onmessage = (event) => {
        if (!isCancelled) {
          try {
            const data = JSON.parse(event.data);
            onUpdate(data);
          } catch (e) {
            console.error('SSE JSON parse error:', e);
          }
        }
      };
      sse.onerror = (e) => {
        console.warn('SSE connection error, falling back to polling', e);
        sse?.close();
        this.pollTask(taskId, onUpdate, onError);
      };
    } catch (e) {
      this.pollTask(taskId, onUpdate, onError);
    }

    return () => {
      isCancelled = true;
      sse?.close();
    };
  }

  private pollTask(
    taskId: string,
    onUpdate: (task: TaskResponse) => void,
    onError?: (error: Error) => void
  ) {
    const interval = setInterval(async () => {
      try {
        const task = await this.getTaskStatus(taskId);
        onUpdate(task);
        if (task.status === 'completed' || task.status === 'failed') {
          clearInterval(interval);
        }
      } catch (err) {
        if (onError && err instanceof Error) onError(err);
      }
    }, 2500);

    return () => clearInterval(interval);
  }
}

export const apiService = new WorkflowApiService();
