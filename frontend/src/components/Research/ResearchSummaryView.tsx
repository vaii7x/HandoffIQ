import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { TaskResponse } from '../../types/workflow';
import { AgentPalette } from '../../types/agent';
import { apiService } from '../../services/api';

export interface CanonicalRequirement {
  id: string;
  source_id?: string;
  original_text: string;
  description: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  status?: string;
  related_files?: string[];
  related_test_ids?: string[];
}

interface ResearchSummaryViewProps {
  task: TaskResponse | null;
  palette: AgentPalette;
  onContinue?: () => void;
}

export const ResearchSummaryView: React.FC<ResearchSummaryViewProps> = ({
  task,
  palette: _palette,
  onContinue: _onContinue,
}) => {
  const [requirements, setRequirements] = useState<CanonicalRequirement[]>(() => {
    return (task?.requirements as CanonicalRequirement[]) || [];
  });
  const [loading, setLoading] = useState<boolean>(() => {
    return !(task?.requirements && task.requirements.length > 0);
  });
  const [expandedId, setExpandedId] = useState<string | null>(() => {
    return task?.requirements?.[0]?.id || null;
  });

  const taskId = task?.taskId || '';

  // Synchronize immediately if task.requirements updates from parent
  useEffect(() => {
    if (task?.requirements && task.requirements.length > 0) {
      setRequirements(task.requirements);
      setLoading(false);
      if (!expandedId) setExpandedId(task.requirements[0].id);
    }
  }, [task?.requirements, expandedId]);

  useEffect(() => {
    let isSubscribed = true;
    if (!taskId) {
      setLoading(false);
      return;
    }

    // Only set loading true if we have no requirements yet
    if (requirements.length === 0) {
      setLoading(true);
    }

    apiService
      .getRequirements(taskId)
      .then((res) => {
        if (!isSubscribed) return;
        const reqList = res?.requirements || [];
        if (reqList.length > 0) {
          setRequirements(reqList);
          if (!expandedId) {
            setExpandedId(reqList[0].id);
          }
        }
      })
      .catch((err) => {
        console.warn('Could not fetch requirements:', err);
      })
      .finally(() => {
        if (isSubscribed) setLoading(false);
      });

    return () => {
      isSubscribed = false;
    };
  }, [taskId]);

  const toggleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  const taskSummary =
    'System architecture planned and decomposed into atomic, verifiable specification contracts.';

  const priorityColor = (p: string) => {
    switch (p?.toLowerCase()) {
      case 'critical':
        return 'text-[#D9383A] border-[#FCD6D9] bg-[#FEECEE]';
      case 'high':
        return 'text-[#B8721A] border-[#FFE8BF] bg-[#FFF6E5]';
      case 'medium':
        return 'text-[#7664E8] border-[#DFE1F2] bg-[#ECECFA]';
      default:
        return 'text-[#737895] border-[#DFE1F2] bg-[#FAF9FC]';
    }
  };

  return (
    <div className="relative z-10 w-full max-w-3xl mx-auto px-4 mt-1 flex flex-col items-center">
      {/* 1. Header & Summary matching reference Image 1 */}
      <div className="w-full text-center mb-4">
        <div className="text-[11px] font-semibold tracking-[0.24em] uppercase text-[#737895]">
          AGENT 01 — RESEARCH & SPECIFICATION
        </div>
        <h2 className="text-xl sm:text-2xl md:text-3xl font-medium tracking-tight text-[#171A35] mt-2 max-w-2xl mx-auto leading-snug">
          Analyzing your goal, extracting canonical requirements, and structuring technical context.
        </h2>
        <p className="text-xs text-[#737895] mt-2 max-w-lg mx-auto leading-relaxed">
          {taskSummary}
        </p>

        {/* Count & Verification Status Badges */}
        <div className="flex items-center justify-center gap-2 mt-3">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white border border-[#DFE1F2] text-xs font-mono text-[#171A35] shadow-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-[#7664E8] animate-pulse" />
            {loading ? 'Analyzing specifications...' : `${requirements.length} Canonical Requirements Extracted`}
          </span>
          {!loading && requirements.length > 0 && (
            <span className="text-xs font-mono text-[#7664E8] bg-[#ECECFA] border border-[#DFE1F2] px-3 py-1 rounded-full">
              Advancing to Validation
            </span>
          )}
        </div>
      </div>

      {/* 2. Structured Requirements Table Matching Reference Image 2 */}
      <div className="w-full bg-white border border-[#DFE1F2] rounded-2xl p-3.5 sm:p-5 shadow-[0_2px_12px_rgba(23,26,53,0.03)]">
        {/* Pale lavender header row with rounded corners */}
        <div className="bg-[#ECECFA] rounded-xl px-4 py-2.5 mb-2.5 flex items-center justify-between text-xs font-semibold text-[#171A35] select-none">
          <div className="flex items-center gap-3">
            <span className="w-16">ID</span>
            <span>Canonical Requirement</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="hidden sm:inline">Priority</span>
            <span>Details</span>
          </div>
        </div>

        {/* Individual rows with rounded containers */}
        <div className="space-y-2 max-h-[300px] overflow-y-auto pr-0.5">
          {loading && (
            <div className="py-8 text-center text-xs font-mono text-[#737895]">
              Extracting atomic requirements from goal specification...
            </div>
          )}

          {!loading && requirements.length === 0 && (
            <div className="py-8 text-center text-xs font-mono text-[#737895]">
              No canonical requirements extracted yet.
            </div>
          )}

          {!loading &&
            requirements.map((req) => {
              const isExpanded = expandedId === req.id;
              return (
                <div
                  key={req.id}
                  className="bg-white hover:bg-[#FAF9FC] border border-[#DFE1F2] rounded-xl transition-all shadow-[0_1px_2px_rgba(23,26,53,0.02)] overflow-hidden"
                >
                  <button
                    type="button"
                    onClick={() => toggleExpand(req.id)}
                    className="w-full text-left px-4 py-3 flex items-center justify-between gap-3 focus:outline-none"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      {/* Stable ID (Source ID if available, otherwise Canonical ID) */}
                      <span
                        className="font-mono text-xs font-semibold text-[#171A35] shrink-0 w-16"
                        title={req.source_id ? `Source: ${req.source_id} (${req.id})` : req.id}
                      >
                        {req.source_id || req.id}
                      </span>
                      {/* Priority Chip */}
                      <span
                        className={`text-[9px] font-mono uppercase px-2 py-0.5 rounded border shrink-0 ${priorityColor(
                          req.priority
                        )}`}
                      >
                        {req.priority || 'medium'}
                      </span>
                      {/* Title */}
                      <span className="text-xs text-[#171A35] truncate font-sans font-medium">
                        {req.original_text}
                      </span>
                    </div>

                    <span className="text-xs font-mono text-[#7664E8] shrink-0 select-none hover:underline">
                      {isExpanded ? '[-] Hide' : '[+] View'}
                    </span>
                  </button>

                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden px-4 pb-3 pt-2 border-t border-[#DFE1F2] bg-[#FAF9FC] text-xs"
                      >
                        {req.source_id && (
                          <div className="flex items-center gap-2 mb-2 text-[11px] font-mono">
                            <span className="px-2 py-0.5 rounded bg-[#ECECFA] text-[#7664E8] font-semibold border border-[#DFE1F2]">
                              Source ID: {req.source_id}
                            </span>
                            <span className="text-[#737895]">
                              Canonical ID: {req.id}
                            </span>
                          </div>
                        )}

                        {req.description && (
                          <div className="mb-2 text-[#171A35] leading-relaxed font-sans">
                            {req.description.replace(/^\[Source:\s*[^\]]+\]\s*/, '')}
                          </div>
                        )}

                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 pt-1 text-[11px] font-mono text-[#737895]">
                          {req.related_files && req.related_files.length > 0 && (
                            <div className="flex items-center gap-1">
                              <span className="text-[#737895]/70">Target:</span>
                              <span className="text-[#171A35] font-medium">
                                {req.related_files.join(', ')}
                              </span>
                            </div>
                          )}
                          {req.related_test_ids && req.related_test_ids.length > 0 && (
                            <div className="flex items-center gap-1">
                              <span className="text-[#737895]/70">Test IDs:</span>
                              <span className="text-[#171A35] font-medium">
                                {req.related_test_ids.join(', ')}
                              </span>
                            </div>
                          )}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
        </div>
      </div>
    </div>
  );
};
