import React from 'react';

export type StatusVariant =
  | 'missing'
  | 'removed'
  | 'altered'
  | 'added'
  | 'repaired'
  | 'passed'
  | 'issues_found'
  | 'needs_review'
  | 'running'
  | 'neutral';

interface StatusBadgeProps {
  variant: StatusVariant;
  label?: string;
  className?: string;
}

const VARIANT_STYLES: Record<
  StatusVariant,
  { label: string; textClass: string; bgClass: string; borderClass: string }
> = {
  missing: {
    label: 'Missing',
    textClass: 'text-sky-300',
    bgClass: 'bg-sky-950/40',
    borderClass: 'border-sky-800/40',
  },
  removed: {
    label: 'Removed',
    textClass: 'text-rose-300',
    bgClass: 'bg-rose-950/40',
    borderClass: 'border-rose-800/40',
  },
  altered: {
    label: 'Altered',
    textClass: 'text-amber-300',
    bgClass: 'bg-amber-950/40',
    borderClass: 'border-amber-800/40',
  },
  added: {
    label: 'Added',
    textClass: 'text-purple-300',
    bgClass: 'bg-purple-950/40',
    borderClass: 'border-purple-800/40',
  },
  repaired: {
    label: 'Repaired',
    textClass: 'text-emerald-300',
    bgClass: 'bg-emerald-950/30',
    borderClass: 'border-emerald-800/30',
  },
  passed: {
    label: 'Passed',
    textClass: 'text-white/70',
    bgClass: 'bg-white/[0.04]',
    borderClass: 'border-white/10',
  },
  issues_found: {
    label: 'Issues found',
    textClass: 'text-amber-300',
    bgClass: 'bg-amber-950/40',
    borderClass: 'border-amber-800/40',
  },
  needs_review: {
    label: 'Needs review',
    textClass: 'text-orange-300',
    bgClass: 'bg-orange-950/40',
    borderClass: 'border-orange-800/40',
  },
  running: {
    label: 'Running',
    textClass: 'text-sky-300',
    bgClass: 'bg-sky-950/40',
    borderClass: 'border-sky-800/40',
  },
  neutral: {
    label: 'Verified',
    textClass: 'text-white/60',
    bgClass: 'bg-white/[0.03]',
    borderClass: 'border-white/10',
  },
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  variant,
  label,
  className = '',
}) => {
  const config = VARIANT_STYLES[variant] || VARIANT_STYLES.neutral;
  const displayLabel = label || config.label;

  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-mono tracking-tight border ${config.bgClass} ${config.textClass} ${config.borderClass} ${className}`}
    >
      {displayLabel}
    </span>
  );
};
