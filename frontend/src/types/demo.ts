export interface DemoRequirement {
  id: string;
  source_id: string;
  title: string;
  description: string;
  category: string;
  authoritative: boolean;
}

export interface DemoHandoffItem {
  id: string;
  requirement_id: string;
  received_text: string;
  status: 'broken' | 'preserved' | 'repaired';
  defect_id?: string | null;
  original_text: string;
}

export interface DemoDiscrepancy {
  requirement_id: string;
  original_requirement: string;
  received_statement: string;
  category: string;
  severity: string;
  explanation: string;
  evidence: string[];
  validator_detected: boolean;
  oracle_detected: boolean;
  is_missed_by_validator: boolean;
}

export interface DemoRepairItem {
  id: string;
  requirement_id: string;
  original_text: string;
  broken_text: string;
  repaired_text: string;
  repair_reason: string;
  status: string;
  diff_before: string;
  diff_after: string;
}

export interface OracleCheck {
  check_id: string;
  requirement_id: string;
  name: string;
  passed: boolean;
  phase: string;
  details: string;
  actual_value: string;
  expected_value: string;
}

export interface DemoValidationResponse {
  validator_detected_count: intNumber;
  oracle_seeded_defect_count: intNumber;
  preserved_count: intNumber;
  discrepancies: DemoDiscrepancy[];
  preserved_requirement: DemoHandoffItem;
  oracle_checks: OracleCheck[];
  all_seeded_defects_detected: boolean;
  missed_defects: string[];
}

type intNumber = number;

export interface DemoRevalidationResponse {
  validator_issues_count: number;
  oracle_passed: boolean;
  resolved_count: number;
  unresolved_count: number;
  all_clear: boolean;
  remaining_issues: DemoDiscrepancy[];
  oracle_checks: OracleCheck[];
  disclaimer: string;
}

export type DemoStep = 1 | 2 | 3 | 4 | 5;

export type DemoStatus =
  | 'idle'
  | 'loading'
  | 'ready'
  | 'validating'
  | 'repairing'
  | 'revalidating'
  | 'error';
