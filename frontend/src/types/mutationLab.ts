export type MutationType =
  | 'missing'
  | 'altered'
  | 'added'
  | 'contradiction'
  | 'weakened'
  | 'ordering_loss';

export type MutationIntensity = 'subtle' | 'moderate' | 'adversarial';

export type MutationStrategy =
  | 'balanced_blend'
  | 'targeted_boundary'
  | 'semantic_distortion'
  | 'omission_pruning'
  | 'adversarial_injection';

export interface CanonicalRequirement {
  id: string;
  domain: string;
  priority: 'critical' | 'high' | 'medium';
  title: string;
  text: string;
  constraints: string[];
}

export interface MutatedItem {
  id: string;
  targetRequirementId: string;
  mutationType: MutationType;
  severity: 'low' | 'medium' | 'high' | 'critical';
  mutatedText: string;
  diffSummary: string;
  isAdded?: boolean;
}

export type ProposedAction =
  | 'restore'
  | 'repair_constraint'
  | 'reject_addition'
  | 'human_review';

export type RepairStatus =
  | 'detected'
  | 'suggested'
  | 'applied'
  | 'awaiting_human_review';

export interface DetectedDiscrepancy {
  id: string;
  requirementId: string;
  type: MutationType;
  severity: 'low' | 'medium' | 'high' | 'critical';
  evidenceOriginal: string;
  evidenceMutated: string;
  detectionConfidence: number; // e.g. 0.98
  detectionHeuristic: string; // e.g. "Cosine similarity 0.72 < 0.92 threshold"
  proposedAction: ProposedAction;
  proposedRepairText: string;
  repairStatus: RepairStatus;
  postValidationPass: boolean;
}

export interface BaselineMetrics {
  withoutHandoffIQ: {
    preservationRate: number; // percentage (e.g. 40)
    missedRequirements: number;
    unresolvedDiscrepancies: number;
    repairsApplied: number;
    downstreamReworkMinutes: number;
    verificationLatencyMs: number;
    tokenCost: number;
  };
  withHandoffIQ: {
    preservationRate: number; // percentage (e.g. 100)
    missedRequirements: number;
    unresolvedDiscrepancies: number;
    repairsApplied: number;
    downstreamReworkMinutes: number;
    verificationLatencyMs: number;
    tokenCost: number;
  };
}

export interface ExperimentConfig {
  id: string;
  name: string;
  sourceTaskId: string;
  strategy: MutationStrategy;
  intensity: MutationIntensity;
  mutationCount: number;
  enabledMutationTypes: MutationType[];
}

export interface AuditStep {
  step: string;
  timestamp: string;
  detail: string;
  status: 'passed' | 'warning' | 'repaired';
}

export interface ExperimentResult {
  config: ExperimentConfig;
  timestamp: string;
  status: 'completed' | 'awaiting_review' | 'running';
  canonicalRequirements: CanonicalRequirement[];
  mutations: MutatedItem[];
  detectedDiscrepancies: DetectedDiscrepancy[];
  preservationRate: number; // calculated from actual experiment data
  baseline: BaselineMetrics;
  auditTrail: AuditStep[];
}
