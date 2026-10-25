import type { RequirementDiscrepancy, DiscrepancyType, StatItem } from '../types/handoff';

export interface AuthoritativeValidationResult {
  isLoading: boolean;
  canonicalCount: number;
  analyzedCount: number;

  // Discrepancy Totals (clearly defined counting rules)
  totalDetected: number;
  totalRepaired: number;
  totalUnresolved: number;

  // Categorized counts (strictly mutually exclusive: sum === totalDetected)
  missingCount: number;
  removedCount: number;
  alteredCount: number;
  contradictionCount: number;
  addedCount: number;
  otherCount: number;

  // Requirement preservation
  preRepairPreservedCount: number;
  postRepairPreservedCount: number;
  unresolvedRequirementIds: Set<string>;

  // Blocking logic
  hasUnresolvedBlockers: boolean;
  canContinueToCoding: boolean;

  // Check row dynamic summaries
  reqComparisonSupportingDetail: string;
  reqComparisonStatusText: string;
  reqComparisonBadgeVariant: 'passed' | 'repaired' | 'issues_found' | 'running';

  constraintsRisksSupportingDetail: string;
  constraintsRisksStatusText: string;
  constraintsRisksBadgeVariant: 'passed' | 'repaired' | 'needs_review' | 'running';

  // Bottom progress status text
  progressStatusText: string;

  // Statistics items for the top pills bar
  stats: StatItem[];

  // Normalized discrepancies
  discrepancies: RequirementDiscrepancy[];
}

/**
 * Maps a raw backend ValidationIssue to a domain RequirementDiscrepancy.
 */
export function mapBackendIssueToDiscrepancy(iss: any, idx: number): RequirementDiscrepancy {
  const t = String(iss.issue_type || '').toLowerCase();
  let type: DiscrepancyType = 'other';

  // Strict, unambiguous classification precedence:
  // 1. Contradictory requirements: Directly conflicting constraints
  // 2. Missing specs: Canonical requirements omitted from the handoff
  // 3. Removed items: Specs dropped or deprioritized in the handoff
  // 4. Added or unexpected scope: Invented items not present in canonical requirements
  // 5. Altered constraints: Requirements weakened or modified
  // 6. Other issues: Semantic drift, schema errors, suspicious directives, or protocol violations
  if (t === 'contradiction' || t.includes('contradict')) {
    type = 'contradiction';
  } else if (t === 'omission' || t.includes('missing')) {
    type = 'missing';
  } else if (t === 'removed_spec' || t.includes('remov') || t.includes('depriorit') || t.includes('drop')) {
    type = 'removed';
  } else if (t === 'invented_requirement' || t.includes('invent') || t.includes('add') || t.includes('unexpected')) {
    type = 'added';
  } else if (t === 'weakened_constraint' || t.includes('alter') || t.includes('weak')) {
    type = 'altered';
  } else {
    // Semantic drift, schema_error, suspicious_instruction, or protocol violations
    type = 'other';
  }

  const repairStatusStr = String(iss.repair_status || 'unresolved').toLowerCase();
  const isRepaired = repairStatusStr === 'repaired';

  const severityStr = String(iss.severity || 'medium').toLowerCase();
  const severity: 'low' | 'medium' | 'high' | 'critical' =
    severityStr === 'critical'
      ? 'critical'
      : severityStr === 'high'
      ? 'high'
      : severityStr === 'low'
      ? 'low'
      : 'medium';

  return {
    id: String(iss.id || `issue-${idx + 1}`),
    requirementId: String(iss.requirement_id || 'REQ-GENERAL'),
    type,
    originalText: String(iss.original_value || iss.description || 'Canonical requirement specification'),
    receivedText: String(
      iss.observed_value ||
        (isRepaired
          ? 'Restored canonical specification in handoff context'
          : 'Omitted or altered in downstream handoff context')
    ),
    repairStatus: isRepaired ? 'Repaired' : 'Unresolved',
    isRepaired,
    severity,
    evidence: Array.isArray(iss.evidence)
      ? iss.evidence.join('; ')
      : String(iss.evidence || 'Forensic audit against canonical requirement specification'),
    repairDetails: isRepaired
      ? 'Canonical requirement specification restored and verified'
      : 'Discrepancy requires clarification before proceeding to code generation',
    revalidationResult: isRepaired
      ? 'Verified compliant with canonical specification on revalidation'
      : 'Unresolved: pending resolution',
  };
}

/**
 * Computes an authoritative validation result from canonical requirements and classified discrepancies.
 * Guarantees that every metric, message, status, and progress indicator mathematically reconciles.
 */
export function computeAuthoritativeValidation(params: {
  canonicalRequirements: { id: string; source_id?: string; original_text?: string }[];
  rawIssues: any[];
  isLoading: boolean;
  taskRequest?: string;
}): AuthoritativeValidationResult {
  const { canonicalRequirements, rawIssues, isLoading, taskRequest = '' } = params;
  const canonicalCount = canonicalRequirements.length;
  const analyzedCount = canonicalCount;

  // 1. Loading State
  if (isLoading) {
    return {
      isLoading: true,
      canonicalCount,
      analyzedCount,
      totalDetected: 0,
      totalRepaired: 0,
      totalUnresolved: 0,
      missingCount: 0,
      removedCount: 0,
      alteredCount: 0,
      contradictionCount: 0,
      addedCount: 0,
      otherCount: 0,
      preRepairPreservedCount: canonicalCount,
      postRepairPreservedCount: canonicalCount,
      unresolvedRequirementIds: new Set(),
      hasUnresolvedBlockers: false,
      canContinueToCoding: false,
      reqComparisonSupportingDetail: 'Analyzing requirements and handoff context…',
      reqComparisonStatusText: 'Checking',
      reqComparisonBadgeVariant: 'running',
      constraintsRisksSupportingDetail: 'Evaluating security invariants and constraints…',
      constraintsRisksStatusText: 'Checking',
      constraintsRisksBadgeVariant: 'running',
      progressStatusText: 'Stage 2 of 5 · Validating handoff against canonical requirements…',
      stats: [
        { id: 'preserved', label: 'Canonical Reqs Preserved', value: '—', highlight: true },
        { id: 'missing', label: 'Missing Specs', value: '—' },
        { id: 'removed', label: 'Removed Items', value: '—' },
        { id: 'altered', label: 'Altered Constraints', value: '—' },
        { id: 'contradiction', label: 'Contradictory Reqs', value: '—' },
      ],
      discrepancies: [],
    };
  }

  // 2. Map raw issues into normalized discrepancies
  const discrepancies: RequirementDiscrepancy[] = rawIssues.map((iss, idx) =>
    mapBackendIssueToDiscrepancy(iss, idx)
  );

  const totalDetected = discrepancies.length;
  const totalRepaired = discrepancies.filter((d) => d.isRepaired).length;
  const totalUnresolved = totalDetected - totalRepaired;

  // Categorized counts (strictly mutually exclusive)
  let missingCount = 0;
  let removedCount = 0;
  let alteredCount = 0;
  let contradictionCount = 0;
  let addedCount = 0;
  let otherCount = 0;

  for (const d of discrepancies) {
    if (d.type === 'missing') missingCount++;
    else if (d.type === 'removed') removedCount++;
    else if (d.type === 'altered') alteredCount++;
    else if (d.type === 'contradiction') contradictionCount++;
    else if (d.type === 'added') addedCount++;
    else otherCount++;
  }

  // 3. Precise Requirement Preservation Analysis
  const allCompromisedReqIds = new Set<string>();
  const unresolvedRequirementIds = new Set<string>();

  for (const d of discrepancies) {
    if (d.requirementId && d.requirementId !== 'REQ-GENERAL') {
      allCompromisedReqIds.add(d.requirementId);
      if (!d.isRepaired) {
        unresolvedRequirementIds.add(d.requirementId);
      }
    }
  }

  const preRepairPreservedCount = canonicalRequirements.filter(
    (req) => !allCompromisedReqIds.has(req.id) && (!req.source_id || !allCompromisedReqIds.has(req.source_id))
  ).length;

  const postRepairPreservedCount = canonicalRequirements.filter(
    (req) => !unresolvedRequirementIds.has(req.id) && (!req.source_id || !unresolvedRequirementIds.has(req.source_id))
  ).length;

  // 4. Blocking Assessment
  const lowerRequest = taskRequest.toLowerCase();
  const userWantedUI = ['ui', 'frontend', 'gui', 'interface', 'web', 'react', 'view'].some((w) =>
    lowerRequest.includes(w)
  );

  const blockingIssues = discrepancies.filter((d) => {
    if (d.isRepaired) return false;

    // Check if unrequested UI constraint on non-UI task (non-blocking)
    const textCorpus = (d.originalText + ' ' + d.receivedText + ' ' + (d.evidence || '')).toLowerCase();
    const isUnrequestedUI =
      !userWantedUI &&
      ['ui layer', 'ui-layer', 'uimodule', 'graphical ui', 'user interface layer'].some((w) =>
        textCorpus.includes(w)
      );
    if (isUnrequestedUI) return false;

    if (d.severity === 'critical') return true;
    if (d.type === 'contradiction' || d.type === 'missing') return true;
    if (d.severity === 'high') return true;
    if (textCorpus.includes('uncertain') || textCorpus.includes('manual review required') || textCorpus.includes('review required')) return true;
    return false;
  });

  const hasUnresolvedBlockers = blockingIssues.length > 0;
  const canContinueToCoding = !hasUnresolvedBlockers;

  // 5. Dynamic Check Row Summaries
  let reqComparisonSupportingDetail = '';
  let reqComparisonStatusText: 'Passed' | 'Repaired' | 'Issues Found' = 'Passed';
  let reqComparisonBadgeVariant: 'passed' | 'repaired' | 'issues_found' = 'passed';

  if (totalDetected === 0) {
    reqComparisonSupportingDetail = `${analyzedCount} analyzed · 0 discrepancies detected`;
    reqComparisonStatusText = 'Passed';
    reqComparisonBadgeVariant = 'passed';
  } else if (totalUnresolved === 0) {
    reqComparisonSupportingDetail = `${analyzedCount} analyzed · ${totalDetected} discrepancies (${totalRepaired} repaired · 0 unresolved)`;
    reqComparisonStatusText = 'Repaired';
    reqComparisonBadgeVariant = 'repaired';
  } else {
    reqComparisonSupportingDetail = `${analyzedCount} analyzed · ${totalDetected} discrepancies (${totalRepaired} repaired · ${totalUnresolved} unresolved)`;
    reqComparisonStatusText = 'Issues Found';
    reqComparisonBadgeVariant = 'issues_found';
  }

  // Constraint and risk issues
  const riskIssues = discrepancies.filter(
    (d) =>
      d.type === 'altered' ||
      d.type === 'contradiction' ||
      d.type === 'other' ||
      d.severity === 'critical' ||
      d.severity === 'high'
  );
  const riskTotal = riskIssues.length;
  const riskRepaired = riskIssues.filter((i) => i.isRepaired).length;
  const riskUnresolved = riskTotal - riskRepaired;

  let constraintsRisksSupportingDetail = '';
  let constraintsRisksStatusText: 'Passed' | 'Repaired' | 'Review Required' = 'Passed';
  let constraintsRisksBadgeVariant: 'passed' | 'repaired' | 'needs_review' = 'passed';

  if (riskTotal === 0) {
    constraintsRisksSupportingDetail = 'Security and system constraints verified compliant';
    constraintsRisksStatusText = 'Passed';
    constraintsRisksBadgeVariant = 'passed';
  } else if (riskUnresolved === 0) {
    constraintsRisksSupportingDetail = `${riskTotal} constraint/risk issue${
      riskTotal > 1 ? 's' : ''
    } detected (${riskRepaired} repaired · 0 unresolved)`;
    constraintsRisksStatusText = 'Repaired';
    constraintsRisksBadgeVariant = 'repaired';
  } else {
    constraintsRisksSupportingDetail = `${riskTotal} constraint/risk issue${
      riskTotal > 1 ? 's' : ''
    } detected (${riskRepaired} repaired · ${riskUnresolved} unresolved)`;
    constraintsRisksStatusText = 'Review Required';
    constraintsRisksBadgeVariant = 'needs_review';
  }

  // 6. Progress Bar Status Text
  let progressStatusText = '';
  if (totalDetected === 0) {
    progressStatusText = 'Validation complete: all requirements verified compliant';
  } else if (hasUnresolvedBlockers) {
    progressStatusText = `Clarification required: ${totalUnresolved} unresolved discrepancy`;
  } else if (totalUnresolved === 0) {
    progressStatusText = `${totalDetected} discrepancies detected · ${totalRepaired} repaired · 0 unresolved`;
  } else {
    progressStatusText = `Validation complete: specifications reconciled (${totalUnresolved} non-blocking note${
      totalUnresolved > 1 ? 's' : ''
    })`;
  }

  // 7. Stat Items for Top Statistics Bar (Reconciles exactly: sum of category pills === totalDetected)
  const stats: StatItem[] = [
    {
      id: 'preserved',
      label: totalRepaired > 0 ? 'Preserved (Post-Repair)' : 'Canonical Reqs Preserved',
      value: canonicalCount > 0 ? `${postRepairPreservedCount} / ${canonicalCount}` : '—',
      highlight: true,
    },
    { id: 'missing', label: 'Missing Specs', value: missingCount },
    { id: 'removed', label: 'Removed Items', value: removedCount },
    { id: 'altered', label: 'Altered Constraints', value: alteredCount },
    { id: 'contradiction', label: 'Contradictory Reqs', value: contradictionCount },
  ];

  if (addedCount > 0) {
    stats.push({ id: 'added', label: 'Unexpected Scope', value: addedCount });
  }

  if (otherCount > 0) {
    stats.push({ id: 'other', label: 'Other Issues', value: otherCount });
  }

  return {
    isLoading: false,
    canonicalCount,
    analyzedCount,
    totalDetected,
    totalRepaired,
    totalUnresolved,
    missingCount,
    removedCount,
    alteredCount,
    contradictionCount,
    addedCount,
    otherCount,
    preRepairPreservedCount,
    postRepairPreservedCount,
    unresolvedRequirementIds,
    hasUnresolvedBlockers,
    canContinueToCoding,
    reqComparisonSupportingDetail,
    reqComparisonStatusText,
    reqComparisonBadgeVariant,
    constraintsRisksSupportingDetail,
    constraintsRisksStatusText,
    constraintsRisksBadgeVariant,
    progressStatusText,
    stats,
    discrepancies,
  };
}
