import { AgentPalette } from './agent';

export type IntermediateStageId = 'validate' | 'test';

export interface StatItem {
  id: string;
  label: string;
  value: string | number;
  highlight?: boolean;
}

export type CheckStatus = 'completed' | 'running' | 'failed' | 'pending';

export interface RequirementDiscrepancy {
  id: string;
  requirementId: string;
  type: 'missing' | 'removed' | 'added' | 'altered' | 'preserved';
  originalText: string;
  receivedText: string;
  repairStatus: string;
  severity?: 'low' | 'medium' | 'high';
}

export interface TestCaseResult {
  id: string;
  name: string;
  tool: string;
  status: 'passed' | 'failed' | 'repaired' | 'running';
  duration: string;
  outputSnippet?: string;
}

export interface TestFailureDetail {
  id: string;
  summary: string;
  linkedRequirementId: string;
  affectedFiles: string[];
  errorDetails: string;
}

export interface SelfHealingRepair {
  id: string;
  failureSummary: string;
  repairSummary: string;
  attemptNumber: number;
  affectedFiles: string[];
  rerunResult: 'passed' | 'running' | 'failed';
}

export interface CheckRowConfig {
  id: string;
  title: string;
  supportingDetail: string;
  status: CheckStatus;
  kind:
    | 'requirement_comparison'
    | 'discrepancy_list'
    | 'constraint_risks'
    | 'test_suite'
    | 'failure_analysis'
    | 'self_healing_fixes';
}

export type HandoffDecisionType =
  | 'ready_for_coding'
  | 'ready_for_deploy'
  | 'needs_review'
  | 'blocked';

export interface HandoffPageConfig {
  id: IntermediateStageId;
  stageNumber: 2 | 4;
  stageName: string;
  fractionText: string;
  eyebrow: string;
  heading: string;
  supportingText: string;
  defaultStatusText: string;
  palette: AgentPalette;
  stats: StatItem[];
  checkRows: CheckRowConfig[];
  decision: {
    type: HandoffDecisionType;
    label: string;
    description: string;
    actionLabel: string;
    nextScreenId: 'coding' | 'deploy';
  };
  discrepancies?: RequirementDiscrepancy[];
  testCases?: TestCaseResult[];
  failures?: TestFailureDetail[];
  repairs?: SelfHealingRepair[];
}
