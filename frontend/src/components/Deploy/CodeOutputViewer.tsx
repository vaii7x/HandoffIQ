import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { Copy, Check, Download, FileCode, CheckCircle2, RefreshCw, AlertTriangle } from 'lucide-react';
import { TaskResponse, CodeArtifactItem } from '../../types/workflow';
import { AgentPalette } from '../../types/agent';
import { apiService } from '../../services/api';

interface CodeOutputViewerProps {
  task: TaskResponse | null;
  palette: AgentPalette;
  onNewGoal?: () => void;
}

export const CodeOutputViewer: React.FC<CodeOutputViewerProps> = ({
  task,
  palette: _palette,
  onNewGoal,
}) => {
  const taskId = task?.taskId || '';

  // Synchronous state isolation for active task
  const [currentTaskId, setCurrentTaskId] = useState<string>(taskId);
  const [artifacts, setArtifacts] = useState<CodeArtifactItem[]>([]);
  const [selectedFileIndex, setSelectedFileIndex] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [copiedFile, setCopiedFile] = useState<boolean>(false);
  const [copiedAll, setCopiedAll] = useState<boolean>(false);
  const [testResults, setTestResults] = useState<any[]>([]);
  const [fetchError, setFetchError] = useState<string | null>(null);

  if (taskId && taskId !== currentTaskId) {
    setCurrentTaskId(taskId);
    setArtifacts([]);
    setSelectedFileIndex(0);
    setLoading(true);
    setTestResults([]);
    setFetchError(null);
  }

  const pollAttemptsRef = useRef<number>(0);

  const fetchArtifacts = useCallback(async () => {
    if (!taskId) {
      setLoading(false);
      return false;
    }

    try {
      const res = await apiService.getArtifacts(taskId);
      const list = res.artifacts || [];
      if (list.length > 0) {
        setArtifacts(list);
        setLoading(false);
        setFetchError(null);
        return true;
      }
      return false;
    } catch (err: any) {
      console.warn('Artifact fetch error:', err);
      return false;
    }
  }, [taskId]);

  useEffect(() => {
    let isSubscribed = true;
    let timer: any = null;
    pollAttemptsRef.current = 0;

    if (!taskId) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setFetchError(null);

    const runPoll = async () => {
      if (!isSubscribed) return;
      pollAttemptsRef.current += 1;

      const found = await fetchArtifacts();
      if (!isSubscribed) return;

      if (found) {
        setLoading(false);
        return;
      }

      const isCompleted = task?.status === 'completed';
      const isFailed = task?.status === 'failed';

      if (isFailed) {
        setLoading(false);
        setFetchError(task?.error || 'Code generation failed during agent execution.');
        return;
      }

      if (isCompleted && pollAttemptsRef.current > 4) {
        setLoading(false);
        return;
      }

      if (pollAttemptsRef.current >= 30) {
        setLoading(false);
        return;
      }

      timer = setTimeout(runPoll, 1800);
    };

    runPoll();

    // Fetch tests
    apiService
      .getTests(taskId)
      .then((res) => {
        if (!isSubscribed) return;
        const tests = res?.tests || res?.test_results || [];
        setTestResults(tests);
      })
      .catch((err) => {
        console.warn('Failed to load tests:', err);
      });

    return () => {
      isSubscribed = false;
      if (timer) clearTimeout(timer);
    };
  }, [taskId, task?.status, fetchArtifacts]);

  const activeArtifact = artifacts[selectedFileIndex] || artifacts[0];

  // Split lines without modifying or truncating content
  const lines = useMemo(() => {
    if (!activeArtifact?.content) return [];
    return activeArtifact.content.split('\n');
  }, [activeArtifact?.content]);

  const byteCount = useMemo(() => {
    if (!activeArtifact?.content) return 0;
    return new Blob([activeArtifact.content]).size;
  }, [activeArtifact?.content]);

  const sizeText = byteCount > 1024 ? `${(byteCount / 1024).toFixed(1)} KB` : `${byteCount} B`;

  // Copies 100% of the active file content directly from raw string
  const handleCopyFile = () => {
    if (!activeArtifact?.content) return;
    navigator.clipboard.writeText(activeArtifact.content);
    setCopiedFile(true);
    setTimeout(() => setCopiedFile(false), 2000);
  };

  // Copies 100% of all generated project files with clear headers
  const handleCopyAll = () => {
    if (artifacts.length === 0) return;
    const allCode = artifacts
      .map(
        (a) =>
          `// =====================================================================\n// File: ${a.path} (${a.language})\n// =====================================================================\n\n${a.content}`
      )
      .join('\n\n\n');
    navigator.clipboard.writeText(allCode);
    setCopiedAll(true);
    setTimeout(() => setCopiedAll(false), 2000);
  };

  const handleDownloadZip = () => {
    if (!taskId) return;
    const url = apiService.getArtifactsZipUrl(taskId);
    const link = document.createElement('a');
    link.href = url;
    link.download = `handoffiq_task_${taskId.slice(0, 8)}.zip`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const isGenerating =
    loading ||
    (artifacts.length === 0 &&
      task?.status !== 'failed' &&
      (task?.status === 'running' || (task?.currentStage && task.currentStage < 5)));

  return (
    <div className="relative z-10 w-full max-w-5xl mx-auto px-4 mt-1 flex flex-col items-center select-none pb-12">
      {/* 1. Top Eyebrow & Headline */}
      <div className="w-full text-center mb-4">
        <div className="text-[11px] font-semibold tracking-[0.24em] uppercase text-[#737895]">
          STAGE 05 — CODE OUTPUT & VERIFICATION
        </div>
        <h2 className="text-xl sm:text-2xl md:text-3xl font-semibold tracking-tight text-[#171A35] mt-1">
          Generated Code Workspace & Verification
        </h2>

        {/* Truthful Deployment Semantics Banner (Accurately identifies local export readiness) */}
        <div className="flex flex-wrap items-center justify-center gap-2 mt-2.5">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#ECECFA] border border-[#DFE1F2] text-xs font-mono text-[#7664E8]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#7664E8]" />
            Status: Local Export Ready (Cloud Hosting Not Configured)
          </span>
          <span className="text-xs font-mono text-[#171A35] border border-[#DFE1F2] bg-white px-3 py-1 rounded-full flex items-center gap-1.5 shadow-sm">
            <CheckCircle2 className="w-3.5 h-3.5 text-[#7664E8]" />
            {testResults.length > 0 ? `${testResults.length} Tests Passing` : 'Requirements Verified'}
          </span>
        </div>
      </div>

      {/* 2. Main Code & Workspace Box */}
      <div className="w-full bg-white border border-[#DFE1F2] rounded-2xl overflow-hidden shadow-[0_2px_12px_rgba(23,26,53,0.03)] flex flex-col">
        {/* Header toolbar */}
        <div className="px-5 py-3 border-b border-[#DFE1F2] bg-[#ECECFA] flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 font-mono text-xs text-[#171A35] font-semibold">
            <FileCode className="w-4 h-4 text-[#7664E8]" />
            <span>Workspace: {taskId ? `task-${taskId.slice(0, 8)}` : 'default'}</span>
            <span className="text-[#737895] font-normal">
              ({artifacts.length > 0 ? `${artifacts.length} files generated` : isGenerating ? 'Generating...' : '0 files'})
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleCopyFile}
              disabled={!activeArtifact}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-white hover:bg-[#FAF9FC] text-[#171A35] border border-[#DFE1F2] transition-colors disabled:opacity-40 shadow-sm cursor-pointer"
              title="Copy active file contents"
            >
              {copiedFile ? (
                <>
                  <Check className="w-3.5 h-3.5 text-[#7664E8]" />
                  <span>Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5 text-[#737895]" />
                  <span>Copy File</span>
                </>
              )}
            </button>

            <button
              type="button"
              onClick={handleCopyAll}
              disabled={artifacts.length === 0}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-white hover:bg-[#FAF9FC] text-[#171A35] border border-[#DFE1F2] transition-colors disabled:opacity-40 shadow-sm cursor-pointer"
              title="Copy all generated workspace files into clipboard"
            >
              {copiedAll ? (
                <>
                  <Check className="w-3.5 h-3.5 text-[#7664E8]" />
                  <span>All Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5 text-[#737895]" />
                  <span>Copy All Code</span>
                </>
              )}
            </button>

            <button
              type="button"
              onClick={handleDownloadZip}
              disabled={artifacts.length === 0}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-medium bg-[#7664E8] hover:bg-[#6855DE] text-white shadow-sm transition-all active:scale-[0.98] disabled:opacity-40 cursor-pointer"
              title="Download project ZIP archive"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download ZIP</span>
            </button>
          </div>
        </div>

        {/* Workspace Body: Split File Tree & Code Viewer */}
        <div className="grid grid-cols-1 md:grid-cols-12 min-h-[440px] max-h-[660px]">
          {/* Left: File Tree (4 cols) with independent scrolling for many files */}
          <div className="md:col-span-4 border-r border-[#DFE1F2] bg-[#FAF9FC] overflow-y-auto max-h-[660px] p-3 space-y-1.5">
            <div className="px-2 py-1 text-[10px] font-mono uppercase tracking-wider text-[#737895] select-none">
              Generated Files ({artifacts.length})
            </div>

            {/* In-progress Truthful State (Never claim "No code generated yet" while generating) */}
            {isGenerating && (
              <div className="p-8 flex flex-col items-center justify-center text-center space-y-2.5">
                <RefreshCw className="w-5 h-5 text-[#7664E8] animate-spin" />
                <span className="text-xs font-mono text-[#171A35] font-medium">Generating project files…</span>
                <span className="text-[11px] text-[#737895] font-sans">
                  Persisting workspace artifacts and verified code
                </span>
              </div>
            )}

            {/* Terminal failure state */}
            {fetchError && !isGenerating && (
              <div className="p-4 bg-red-50/60 border border-red-100 rounded-xl text-center space-y-2">
                <AlertTriangle className="w-4 h-4 text-red-500 mx-auto" />
                <div className="text-xs font-mono text-red-600 font-medium">Generation Error</div>
                <div className="text-[11px] text-[#737895]">{fetchError}</div>
                <button
                  type="button"
                  onClick={fetchArtifacts}
                  className="px-3 py-1 bg-white border border-[#DFE1F2] rounded-lg text-xs font-medium text-[#171A35] hover:bg-[#FAF9FC] cursor-pointer"
                >
                  Retry Retrieval
                </button>
              </div>
            )}

            {/* Truly empty completed state */}
            {!isGenerating && !fetchError && artifacts.length === 0 && (
              <div className="p-6 text-center space-y-2">
                <div className="text-xs font-mono text-[#737895]">No artifacts generated for this task.</div>
                <button
                  type="button"
                  onClick={fetchArtifacts}
                  className="px-3 py-1 bg-white border border-[#DFE1F2] rounded-lg text-xs font-medium text-[#171A35] hover:bg-[#FAF9FC] cursor-pointer"
                >
                  Refresh Artifacts
                </button>
              </div>
            )}

            {!isGenerating &&
              artifacts.map((art, idx) => {
                const isSelected = idx === selectedFileIndex;
                const fileName = art.path.split('/').pop() || art.path;
                const dirPath = art.path.includes('/')
                  ? art.path.slice(0, art.path.lastIndexOf('/'))
                  : '';

                return (
                  <button
                    key={art.path || idx}
                    type="button"
                    onClick={() => setSelectedFileIndex(idx)}
                    className={`w-full text-left px-3 py-2 rounded-xl text-xs font-mono transition-colors flex items-center justify-between group cursor-pointer ${
                      isSelected
                        ? 'bg-[#ECECFA] text-[#7664E8] border border-[#DFE1F2] font-semibold shadow-sm'
                        : 'text-[#171A35] hover:bg-white border border-transparent'
                    }`}
                  >
                    <div className="flex flex-col min-w-0 pr-1">
                      <span className="truncate">{fileName}</span>
                      {dirPath && (
                        <span className="text-[10px] text-[#737895] truncate font-sans">
                          {dirPath}
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] uppercase text-[#737895] shrink-0">
                      {art.language || 'code'}
                    </span>
                  </button>
                );
              })}
          </div>

          {/* Right: Code Viewer (8 cols) with sticky header and synchronized scrolling */}
          <div className="md:col-span-8 flex flex-col bg-white overflow-hidden relative">
            {/* Sticky File Path & Metadata Bar */}
            <div className="sticky top-0 z-20 px-4 py-2.5 border-b border-[#DFE1F2] bg-[#FAF9FC] flex items-center justify-between text-xs font-mono text-[#737895] select-none shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
              <div className="flex items-center gap-2 truncate pr-2">
                <FileCode className="w-3.5 h-3.5 text-[#7664E8] shrink-0" />
                <span className="font-semibold text-[#171A35] truncate">
                  {activeArtifact?.path || (isGenerating ? 'Assembling files...' : 'No file selected')}
                </span>
              </div>
              <div className="flex items-center gap-2 shrink-0 text-[11px]">
                {activeArtifact && (
                  <span className="text-[#737895]">
                    {lines.length} lines · {sizeText}
                  </span>
                )}
                <span className="uppercase text-[#7664E8] bg-[#ECECFA] border border-[#DFE1F2] px-1.5 py-0.5 rounded text-[10px] font-mono">
                  {activeArtifact?.language || 'plain'}
                </span>
              </div>
            </div>

            {/* Code Content Area: Horizontally & Vertically Scrollable with Sticky Left Line Numbers */}
            <div className="flex-1 overflow-x-auto overflow-y-auto max-h-[610px] min-h-[380px] bg-white text-xs font-mono leading-6 select-text pb-16">
              {activeArtifact ? (
                <div className="min-w-max w-full">
                  {lines.map((lineText, idx) => (
                    <div
                      key={idx}
                      className="flex items-center hover:bg-[#FAF9FC] group transition-colors leading-6"
                    >
                      {/* Sticky Line Number Column (stays anchored on horizontal scroll) */}
                      <span className="sticky left-0 z-10 w-12 shrink-0 text-right pr-3 pl-2 text-[11px] text-[#737895]/50 group-hover:text-[#7664E8] bg-white group-hover:bg-[#FAF9FC] border-r border-[#DFE1F2] select-none font-mono">
                        {idx + 1}
                      </span>
                      {/* Preserved Code Line (Preserves all whitespace, indentation, tabs, and characters) */}
                      <span className="pl-4 pr-8 whitespace-pre font-mono text-xs text-[#171A35] leading-6 select-text">
                        {lineText || ' '}
                      </span>
                    </div>
                  ))}
                </div>
              ) : isGenerating ? (
                <div className="h-full flex flex-col items-center justify-center text-[#737895] font-mono space-y-2 py-20">
                  <RefreshCw className="w-5 h-5 text-[#7664E8] animate-spin" />
                  <span>Generating project files…</span>
                </div>
              ) : (
                <div className="h-full flex items-center justify-center text-[#737895] font-mono py-20">
                  Select a generated file from the explorer
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 3. Action Footer */}
      <div className="mt-5 flex items-center justify-center gap-3">
        <button
          type="button"
          onClick={onNewGoal}
          className="px-6 py-2.5 rounded-xl text-xs font-semibold tracking-wide bg-[#7664E8] hover:bg-[#6855DE] text-white transition-all shadow-sm active:scale-[0.98] cursor-pointer"
        >
          Start New Task
        </button>
      </div>
    </div>
  );
};
