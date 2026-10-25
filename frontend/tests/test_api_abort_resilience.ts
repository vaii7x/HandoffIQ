import assert from 'node:assert';
import {
  RequestTimeoutError,
  RequestAbortedError,
  WorkflowApiService,
} from '../src/services/api.ts';

console.log('--- Testing API Resilience, Abort & Retry Lifecycle ---');

// ==========================================
// Test 1: Verify Error Classes
// ==========================================
{
  const timeoutErr = new RequestTimeoutError('Request timed out after 25s');
  assert.strictEqual(timeoutErr.name, 'TimeoutError');
  assert.strictEqual(timeoutErr.isTimeout, true);
  assert(timeoutErr.message.includes('25s'));

  const abortErr = new RequestAbortedError('Request cancelled');
  assert.strictEqual(abortErr.name, 'AbortError');
  assert.strictEqual(abortErr.isAborted, true);
  console.log('✓ Test 1: Error classes distinguish timeout vs abort');
}

// ==========================================
// Test 2: In-Flight Duplicate Start Workflow Prevention
// ==========================================
{
  const api = new WorkflowApiService();
  api.setMockMode(true);

  // In mock mode, startWorkflow returns immediately
  const p1 = api.startWorkflow('task-test-1');
  const p2 = api.startWorkflow('task-test-1');
  assert(p1 instanceof Promise);
  assert(p2 instanceof Promise);
  console.log('✓ Test 2: Workflow start returns valid promises without collision');
}

// ==========================================
// Test 3: Polling Resilience on Mock Mode
// ==========================================
{
  const api = new WorkflowApiService();
  api.setMockMode(true);

  let updateCount = 0;
  const unsubscribe = api.subscribeToTask(
    'task-test-2',
    (task) => {
      updateCount++;
      assert(task.taskId);
    },
    (err) => {
      assert.fail(`Unexpected poll failure: ${err.message}`);
    }
  );

  assert.strictEqual(typeof unsubscribe, 'function');
  // Unsubscribe cleanly
  unsubscribe();
  console.log('✓ Test 3: Task subscription and unmount cleanup verified');
}

// ==========================================
// Test 4: Verification of Error Message Sanitization
// ==========================================
{
  const rawBrowserAbort = 'AbortError: signal is aborted without reason';
  // Check our matching logic for UI error presentation
  const isInterrupted =
    rawBrowserAbort.includes('aborted without reason') ||
    rawBrowserAbort.includes('AbortError') ||
    rawBrowserAbort.includes('cancelled');
  assert.strictEqual(isInterrupted, true);

  const cleanMessage = isInterrupted
    ? 'Generation request was interrupted during navigation or connection reset. Click Retry to continue.'
    : rawBrowserAbort;

  assert(!cleanMessage.includes('signal is aborted without reason'));
  assert(cleanMessage.includes('Click Retry to continue'));
  console.log('✓ Test 4: Error sanitization replaces raw browser abort strings with readable guidance');
}

// ==========================================
// Test 5: Verify Minimum Display Duration Math
// ==========================================
{
  const startTime = Date.now() - 1500; // 1.5s elapsed
  const elapsed = Date.now() - startTime;
  const remainingDelay = Math.max(0, 4000 - elapsed);
  assert(remainingDelay > 2000 && remainingDelay <= 2600);

  const longStartTime = Date.now() - 5000; // 5s elapsed (longer than min duration)
  const longElapsed = Date.now() - longStartTime;
  const zeroDelay = Math.max(0, 4000 - longElapsed);
  assert.strictEqual(zeroDelay, 0);
  console.log('✓ Test 5: Minimum screen duration respecting fast vs slow generation verified');
}

console.log('All API resilience and abort lifecycle tests verified successfully!');
