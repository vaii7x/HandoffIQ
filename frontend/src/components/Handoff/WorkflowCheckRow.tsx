import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckRowConfig } from '../../types/handoff';
import { AgentPalette } from '../../types/agent';
import { Loader2 } from 'lucide-react';
import { StatusBadge, StatusVariant } from '../ui/StatusBadge';

interface WorkflowCheckRowProps {
  check: CheckRowConfig;
  isExpanded: boolean;
  onToggle: () => void;
  palette: AgentPalette;
  children: React.ReactNode;
}

export const WorkflowCheckRow: React.FC<WorkflowCheckRowProps> = ({
  check,
  isExpanded,
  onToggle,
  children,
}) => {
  // Determine honest semantic status
  let badgeVariant: StatusVariant = 'passed';
  let badgeLabel = 'Passed';

  if (check.status === 'running') {
    badgeVariant = 'running';
    badgeLabel = 'Running';
  } else if (
    check.kind === 'discrepancy_list' ||
    check.id === 'discrepancy_detection'
  ) {
    badgeVariant = 'issues_found';
    badgeLabel = 'Issues found';
  } else if (check.kind === 'failure_analysis') {
    badgeVariant = 'needs_review';
    badgeLabel = 'Failures logged';
  } else if (check.kind === 'self_healing_fixes') {
    badgeVariant = 'repaired';
    badgeLabel = 'Repaired';
  }

  return (
    <div className="border-b border-[#DFE1F2] last:border-b-0">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={isExpanded}
        className="w-full py-3.5 px-3 flex items-center justify-between text-left group hover:bg-[#FAF9FC] transition-colors rounded-xl focus:outline-none"
      >
        <div className="flex flex-col sm:flex-row sm:items-baseline sm:gap-3 min-w-0 pr-3">
          {/* Main Visual Anchor: Section Title */}
          <span className="text-sm font-semibold text-[#171A35] group-hover:text-[#7664E8] transition-colors truncate">
            {check.title}
          </span>
          {/* Quieter Supporting Detail */}
          <span className="text-[11px] sm:text-xs text-[#737895] truncate">
            {check.supportingDetail}
          </span>
        </div>

        {/* Right Status */}
        <div className="flex items-center gap-2.5 shrink-0">
          {check.status === 'running' ? (
            <span className="flex items-center gap-1 text-[11px] font-mono text-[#7664E8]">
              <Loader2 className="w-3 h-3 animate-spin" />
              Running
            </span>
          ) : check.statusText ? (
            <span className="text-[11px] font-mono text-[#737895] tracking-tight">
              {check.statusText}
            </span>
          ) : check.kind === 'discrepancy_list' || check.id === 'req_comparison' ? (
            <span className="text-[11px] font-mono text-[#737895] tracking-tight">
              Repaired
            </span>
          ) : (
            <StatusBadge variant={badgeVariant} label={badgeLabel} />
          )}

          <span className="text-xs font-mono text-[#7664E8] select-none hover:underline">
            {isExpanded ? '[-] Hide' : '[+] View'}
          </span>
        </div>
      </button>

      {/* Accordion Expandable Content */}
      <AnimatePresence initial={false}>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{
              duration: 0.2,
              ease: [0.23, 1, 0.32, 1],
            }}
            className="overflow-hidden px-3 pb-3"
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
