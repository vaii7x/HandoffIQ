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
    textClass: 'text-[#737895]',
    bgClass: 'bg-[#FAF9FC]',
    borderClass: 'border-[#DFE1F2]',
  },
  removed: {
    label: 'Removed',
    textClass: 'text-[#737895]',
    bgClass: 'bg-[#FAF9FC]',
    borderClass: 'border-[#DFE1F2]',
  },
  altered: {
    label: 'Altered',
    textClass: 'text-[#737895]',
    bgClass: 'bg-[#FAF9FC]',
    borderClass: 'border-[#DFE1F2]',
  },
  added: {
    label: 'Added',
    textClass: 'text-[#737895]',
    bgClass: 'bg-[#FAF9FC]',
    borderClass: 'border-[#DFE1F2]',
  },
  repaired: {
    label: 'Repaired',
    textClass: 'text-[#7664E8]',
    bgClass: 'bg-[#ECECFA]',
    borderClass: 'border-[#DFE1F2]',
  },
  passed: {
    label: 'Passed',
    textClass: 'text-[#7664E8]',
    bgClass: 'bg-[#ECECFA]',
    borderClass: 'border-[#DFE1F2]',
  },
  issues_found: {
    label: 'Issues found',
    textClass: 'text-[#B8721A]',
    bgClass: 'bg-[#FFF6E5]',
    borderClass: 'border-[#FFE8BF]',
  },
  needs_review: {
    label: 'Needs review',
    textClass: 'text-[#B8721A]',
    bgClass: 'bg-[#FFF6E5]',
    borderClass: 'border-[#FFE8BF]',
  },
  running: {
    label: 'Running',
    textClass: 'text-[#7664E8]',
    bgClass: 'bg-[#ECECFA]',
    borderClass: 'border-[#DFE1F2]',
  },
  neutral: {
    label: 'Verified',
    textClass: 'text-[#737895]',
    bgClass: 'bg-white',
    borderClass: 'border-[#DFE1F2]',
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
