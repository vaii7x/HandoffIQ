import type {
  DemoRequirement,
  DemoHandoffItem,
  DemoRepairItem,
  DemoValidationResponse,
  DemoRevalidationResponse,
  OracleCheck,
} from '../types/demo';

const API_BASE_URL =
  (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) || '/api';

export const LOCAL_DEMO_REQUIREMENTS: DemoRequirement[] = [
  {
    id: 'R001',
    source_id: 'R1',
    title: 'Patient Medical Record Privacy',
    description: 'Patients may access only their own medical records.',
    category: 'Authorization & Privacy',
    authoritative: true,
  },
  {
    id: 'R002',
    source_id: 'R2',
    title: 'Cryptographic Password Hashing',
    description: 'Passwords must be securely hashed and never stored in plaintext.',
    category: 'Authentication Security',
    authoritative: true,
  },
  {
    id: 'R003',
    source_id: 'R3',
    title: 'Non-Negative Inventory Invariant',
    description: 'Inventory must never become negative during concurrent dispensing.',
    category: 'Inventory Invariants',
    authoritative: true,
  },
  {
    id: 'R004',
    source_id: 'R4',
    title: 'Atomic Dispensing Transaction',
    description: 'Dispensing must be atomic: inventory updates and dispensing records either both commit or both roll back.',
    category: 'Transaction Atomicity',
    authoritative: true,
  },
  {
    id: 'R005',
    source_id: 'R5',
    title: 'Payment Idempotency Protection',
    description: 'Repeated payment requests with the same idempotency key must not charge a patient twice.',
    category: 'Billing Idempotency',
    authoritative: true,
  },
  {
    id: 'R006',
    source_id: 'R6',
    title: 'Expired Medication Restriction (Negative Control)',
    description: 'Expired medication must never be dispensed.',
    category: 'Dispensing Safety',
    authoritative: true,
  },
];

export const LOCAL_DEMO_BROKEN_HANDOFF: DemoHandoffItem[] = [
  {
    id: 'D1',
    requirement_id: 'R1',
    defect_id: 'D1',
    status: 'broken',
    received_text: "Patients may access any patient's records if they know the record ID.",
    original_text: 'Patients may access only their own medical records.',
  },
  {
    id: 'D2',
    requirement_id: 'R2',
    defect_id: 'D2',
    status: 'broken',
    received_text: 'Passwords are stored in plaintext.',
    original_text: 'Passwords must be securely hashed and never stored in plaintext.',
  },
  {
    id: 'D3',
    requirement_id: 'R3',
    defect_id: 'D3',
    status: 'broken',
    received_text: 'Inventory is decremented without concurrency protection.',
    original_text: 'Inventory must never become negative during concurrent dispensing.',
  },
  {
    id: 'D4',
    requirement_id: 'R4',
    defect_id: 'D4',
    status: 'broken',
    received_text: 'Inventory changes remain even if writing the dispensing record fails.',
    original_text: 'Dispensing must be atomic: inventory updates and dispensing records either both commit or both roll back.',
  },
  {
    id: 'D5',
    requirement_id: 'R5',
    defect_id: 'D5',
    status: 'broken',
    received_text: 'Payment retries can create duplicate charges.',
    original_text: 'Repeated payment requests with the same idempotency key must not charge a patient twice.',
  },
  {
    id: 'R6',
    requirement_id: 'R6',
    defect_id: null,
    status: 'preserved',
    received_text: 'Expired medication must never be dispensed.',
    original_text: 'Expired medication must never be dispensed.',
  },
];

export const LOCAL_DEMO_REPAIRS: DemoRepairItem[] = [
  {
    id: 'REP-1',
    requirement_id: 'R1',
    original_text: 'Patients may access only their own medical records.',
    broken_text: "Patients may access any patient's records if they know the record ID.",
    repaired_text:
      'Patients may access only their own medical records. Cross-patient access by record ID is strictly forbidden.',
    repair_reason:
      'Restored strict patient authorization boundary and prohibited cross-patient ID traversal.',
    status: 'repaired',
    diff_before: "- Patients may access any patient's records if they know the record ID.",
    diff_after:
      '+ Patients may access only their own medical records. Cross-patient access by record ID is strictly forbidden.',
  },
  {
    id: 'REP-2',
    requirement_id: 'R2',
    original_text: 'Passwords must be securely hashed and never stored in plaintext.',
    broken_text: 'Passwords are stored in plaintext.',
    repaired_text:
      'Passwords must be securely hashed using bcrypt/argon2 and never stored in plaintext.',
    repair_reason:
      'Enforced cryptographic hashing requirement and eradicated plaintext credential storage.',
    status: 'repaired',
    diff_before: '- Passwords are stored in plaintext.',
    diff_after:
      '+ Passwords must be securely hashed using bcrypt/argon2 and never stored in plaintext.',
  },
  {
    id: 'REP-3',
    requirement_id: 'R3',
    original_text: 'Inventory must never become negative during concurrent dispensing.',
    broken_text: 'Inventory is decremented without concurrency protection.',
    repaired_text:
      'Inventory must never become negative during concurrent dispensing, enforced with database row locks or optimistic concurrency.',
    repair_reason:
      'Restored concurrency protection lock to enforce non-negative stock invariant during parallel dispensing.',
    status: 'repaired',
    diff_before: '- Inventory is decremented without concurrency protection.',
    diff_after:
      '+ Inventory must never become negative during concurrent dispensing, enforced with database row locks or optimistic concurrency.',
  },
  {
    id: 'REP-4',
    requirement_id: 'R4',
    original_text:
      'Dispensing must be atomic: inventory updates and dispensing records either both commit or both roll back.',
    broken_text: 'Inventory changes remain even if writing the dispensing record fails.',
    repaired_text:
      'Dispensing must be atomic: inventory updates and dispensing records must execute within a database transaction that fully rolls back on any step failure.',
    repair_reason:
      'Enforced atomic transaction boundary, ensuring complete rollback upon dispensing record failure.',
    status: 'repaired',
    diff_before: '- Inventory changes remain even if writing the dispensing record fails.',
    diff_after:
      '+ Dispensing must be atomic: inventory updates and dispensing records must execute within a database transaction that fully rolls back on any step failure.',
  },
  {
    id: 'REP-5',
    requirement_id: 'R5',
    original_text:
      'Repeated payment requests with the same idempotency key must not charge a patient twice.',
    broken_text: 'Payment retries can create duplicate charges.',
    repaired_text:
      'Repeated payment requests with the same idempotency key must verify existing payment status and never charge a patient twice.',
    repair_reason:
      'Restored idempotency verification to guarantee idempotent payment capture without duplicate charges.',
    status: 'repaired',
    diff_before: '- Payment retries can create duplicate charges.',
    diff_after:
      '+ Repeated payment requests with the same idempotency key must verify existing payment status and never charge a patient twice.',
  },
];

export function runLocalOracleChecks(
  items: DemoHandoffItem[],
  phase: 'broken_inspection' | 'revalidation'
): OracleCheck[] {
  const map: Record<string, string> = {};
  items.forEach((i) => {
    map[i.requirement_id] = i.received_text;
  });

  if (phase === 'broken_inspection') {
    return [
      {
        check_id: 'ORACLE-D1',
        requirement_id: 'R1',
        name: 'Seeded Defect D1: Cross-Patient Record Access',
        passed:
          map['R1']?.toLowerCase().includes('any patient') &&
          map['R1']?.toLowerCase().includes('record id'),
        phase,
        details: 'Asserts downstream text permits accessing other patient records by record ID.',
        actual_value: map['R1'] || '',
        expected_value: "Patients may access any patient's records if they know the record ID.",
      },
      {
        check_id: 'ORACLE-D2',
        requirement_id: 'R2',
        name: 'Seeded Defect D2: Plaintext Password Storage',
        passed: map['R2']?.toLowerCase().includes('plaintext') || false,
        phase,
        details: 'Asserts downstream text specifies storing passwords in plaintext.',
        actual_value: map['R2'] || '',
        expected_value: 'Passwords are stored in plaintext.',
      },
      {
        check_id: 'ORACLE-D3',
        requirement_id: 'R3',
        name: 'Seeded Defect D3: Negative Stock Concurrency Hazard',
        passed:
          map['R3']?.toLowerCase().includes('without concurrency protection') || false,
        phase,
        details:
          'Asserts downstream text decrements inventory without concurrency protection.',
        actual_value: map['R3'] || '',
        expected_value:
          'Inventory is decremented without concurrency protection.',
      },
      {
        check_id: 'ORACLE-D4',
        requirement_id: 'R4',
        name: 'Seeded Defect D4: Partial Transaction Failure',
        passed:
          map['R4']?.toLowerCase().includes('changes remain') &&
          map['R4']?.toLowerCase().includes('fails'),
        phase,
        details:
          'Asserts downstream text leaves partial changes when record writing fails.',
        actual_value: map['R4'] || '',
        expected_value:
          'Inventory changes remain even if writing the dispensing record fails.',
      },
      {
        check_id: 'ORACLE-D5',
        requirement_id: 'R5',
        name: 'Seeded Defect D5: Duplicate Payment Retries',
        passed: map['R5']?.toLowerCase().includes('duplicate charges') || false,
        phase,
        details:
          'Asserts downstream text permits retries to create duplicate payment charges.',
        actual_value: map['R5'] || '',
        expected_value: 'Payment retries can create duplicate charges.',
      },
      {
        check_id: 'ORACLE-R6-CONTROL',
        requirement_id: 'R6',
        name: 'Negative Control R6: Preserved Expiration Rule',
        passed:
          map['R6']?.toLowerCase().includes('expired medication must never be dispensed') &&
          map['R6']?.toLowerCase().includes('never'),
        phase,
        details: 'Asserts requirement R6 was preserved without modification or corruption.',
        actual_value: map['R6'] || '',
        expected_value: 'Expired medication must never be dispensed.',
      },
    ];
  } else {
    return [
      {
        check_id: 'ORACLE-REVALIDATE-R1',
        requirement_id: 'R1',
        name: 'Oracle Assertion: Patient Authorization Restored',
        passed:
          map['R1']?.toLowerCase().includes('only their own') &&
          map['R1']?.toLowerCase().includes('forbidden'),
        phase,
        details: 'Asserts R1 enforces patient isolation and forbids cross-patient record access.',
        actual_value: map['R1'] || '',
        expected_value:
          'Patients may access only their own medical records. Cross-patient access by record ID is strictly forbidden.',
      },
      {
        check_id: 'ORACLE-REVALIDATE-R2',
        requirement_id: 'R2',
        name: 'Oracle Assertion: Cryptographic Hashing Restored',
        passed:
          map['R2']?.toLowerCase().includes('securely hashed') &&
          map['R2']?.toLowerCase().includes('never stored in plaintext'),
        phase,
        details: 'Asserts R2 mandates secure hashing and forbids plaintext password storage.',
        actual_value: map['R2'] || '',
        expected_value:
          'Passwords must be securely hashed using bcrypt/argon2 and never stored in plaintext.',
      },
      {
        check_id: 'ORACLE-REVALIDATE-R3',
        requirement_id: 'R3',
        name: 'Oracle Assertion: Inventory Concurrency Restored',
        passed:
          map['R3']?.toLowerCase().includes('never become negative') &&
          (map['R3']?.toLowerCase().includes('locks') ||
            map['R3']?.toLowerCase().includes('concurrency')),
        phase,
        details: 'Asserts R3 enforces non-negative inventory via concurrency protection.',
        actual_value: map['R3'] || '',
        expected_value:
          'Inventory must never become negative during concurrent dispensing, enforced with database row locks or optimistic concurrency.',
      },
      {
        check_id: 'ORACLE-REVALIDATE-R4',
        requirement_id: 'R4',
        name: 'Oracle Assertion: Dispensing Atomicity Restored',
        passed:
          map['R4']?.toLowerCase().includes('atomic') &&
          map['R4']?.toLowerCase().includes('rolls back'),
        phase,
        details: 'Asserts R4 enforces complete transaction rollback on failure.',
        actual_value: map['R4'] || '',
        expected_value:
          'Dispensing must be atomic: inventory updates and dispensing records must execute within a database transaction that fully rolls back on any step failure.',
      },
      {
        check_id: 'ORACLE-REVALIDATE-R5',
        requirement_id: 'R5',
        name: 'Oracle Assertion: Payment Idempotency Restored',
        passed:
          map['R5']?.toLowerCase().includes('idempotency') &&
          map['R5']?.toLowerCase().includes('never charge a patient twice'),
        phase,
        details: 'Asserts R5 prevents duplicate payment captures upon retry.',
        actual_value: map['R5'] || '',
        expected_value:
          'Repeated payment requests with the same idempotency key must verify existing payment status and never charge a patient twice.',
      },
      {
        check_id: 'ORACLE-REVALIDATE-R6',
        requirement_id: 'R6',
        name: 'Oracle Assertion: Negative Control R6 Still Intact',
        passed: map['R6']?.toLowerCase().includes('expired medication must never be dispensed'),
        phase,
        details: 'Asserts R6 remains unaltered and compliant through the repair cycle.',
        actual_value: map['R6'] || '',
        expected_value: 'Expired medication must never be dispensed.',
      },
    ];
  }
}

export const demoService = {
  async getRequirements(): Promise<DemoRequirement[]> {
    try {
      const res = await fetch(`${API_BASE_URL}/demo/requirements`);
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Fallback to local
    }
    return LOCAL_DEMO_REQUIREMENTS;
  },

  async getBrokenHandoff(): Promise<DemoHandoffItem[]> {
    try {
      const res = await fetch(`${API_BASE_URL}/demo/broken-handoff`);
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Fallback
    }
    return LOCAL_DEMO_BROKEN_HANDOFF;
  },

  async validateHandoff(): Promise<DemoValidationResponse> {
    try {
      const res = await fetch(`${API_BASE_URL}/demo/validate`, { method: 'POST' });
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Fallback
    }

    // Local deterministic validation response
    const oracleChecks = runLocalOracleChecks(LOCAL_DEMO_BROKEN_HANDOFF, 'broken_inspection');
    return {
      validator_detected_count: 5,
      oracle_seeded_defect_count: 5,
      preserved_count: 1,
      all_seeded_defects_detected: true,
      missed_defects: [],
      preserved_requirement: LOCAL_DEMO_BROKEN_HANDOFF.find((i) => i.requirement_id === 'R6')!,
      discrepancies: [
        {
          requirement_id: 'R1',
          original_requirement: 'Patients may access only their own medical records.',
          received_statement: "Patients may access any patient's records if they know the record ID.",
          category: 'Authorization & Privacy',
          severity: 'critical',
          explanation:
            "Privacy and patient record isolation violation on requirement R1: Downstream handoff permits cross-patient record access or weakens patient data isolation.",
          evidence: ["Downstream specification: Patients may access any patient's records if they know the record ID."],
          validator_detected: true,
          oracle_detected: true,
          is_missed_by_validator: false,
        },
        {
          requirement_id: 'R2',
          original_requirement: 'Passwords must be securely hashed and never stored in plaintext.',
          received_statement: 'Passwords are stored in plaintext.',
          category: 'Authentication Security',
          severity: 'critical',
          explanation:
            'Security constraint weakened on requirement R2: Passwords are stored in plaintext or without cryptographic hashing.',
          evidence: ['Downstream specification: Passwords are stored in plaintext.'],
          validator_detected: true,
          oracle_detected: true,
          is_missed_by_validator: false,
        },
        {
          requirement_id: 'R3',
          original_requirement: 'Inventory must never become negative during concurrent dispensing.',
          received_statement: 'Inventory is decremented without concurrency protection.',
          category: 'Inventory Invariants',
          severity: 'critical',
          explanation:
            'Inventory invariant contradiction on requirement R3: Inventory quantities must never become negative under concurrent dispensing operations.',
          evidence: ['Downstream specification: Inventory is decremented without concurrency protection.'],
          validator_detected: true,
          oracle_detected: true,
          is_missed_by_validator: false,
        },
        {
          requirement_id: 'R4',
          original_requirement:
            'Dispensing must be atomic: inventory updates and dispensing records either both commit or both roll back.',
          received_statement: 'Inventory changes remain even if writing the dispensing record fails.',
          category: 'Transaction Atomicity',
          severity: 'critical',
          explanation:
            'Atomicity violation on requirement R4: Dispensing must be atomic; partial changes remaining upon step failure violate transaction integrity.',
          evidence: ['Downstream specification: Inventory changes remain even if writing the dispensing record fails.'],
          validator_detected: true,
          oracle_detected: true,
          is_missed_by_validator: false,
        },
        {
          requirement_id: 'R5',
          original_requirement:
            'Repeated payment requests with the same idempotency key must not charge a patient twice.',
          received_statement: 'Payment retries can create duplicate charges.',
          category: 'Billing Idempotency',
          severity: 'critical',
          explanation:
            'Payment idempotency contradiction on requirement R5: Payment retries with identical idempotency keys must prevent duplicate charges.',
          evidence: ['Downstream specification: Payment retries can create duplicate charges.'],
          validator_detected: true,
          oracle_detected: true,
          is_missed_by_validator: false,
        },
      ],
      oracle_checks: oracleChecks,
    };
  },

  async getRepairs(): Promise<DemoRepairItem[]> {
    try {
      const res = await fetch(`${API_BASE_URL}/demo/repairs`);
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Fallback
    }
    return LOCAL_DEMO_REPAIRS;
  },

  async revalidateHandoff(): Promise<DemoRevalidationResponse> {
    try {
      const res = await fetch(`${API_BASE_URL}/demo/revalidate`, { method: 'POST' });
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Fallback
    }

    const repairedItems: DemoHandoffItem[] = LOCAL_DEMO_BROKEN_HANDOFF.map((item) => {
      const rep = LOCAL_DEMO_REPAIRS.find((r) => r.requirement_id === item.requirement_id);
      if (rep) {
        return {
          ...item,
          status: 'repaired',
          received_text: rep.repaired_text,
        };
      }
      return item;
    });

    const oracleChecks = runLocalOracleChecks(repairedItems, 'revalidation');
    const oracleAllPassed = oracleChecks.every((c) => c.passed);

    return {
      validator_issues_count: 0,
      oracle_passed: oracleAllPassed,
      resolved_count: 5,
      unresolved_count: 0,
      all_clear: oracleAllPassed,
      remaining_issues: [],
      oracle_checks: oracleChecks,
      disclaimer:
        'Note: A corrected specification does not prove the generated code implements it. Downstream implementation requires automated testing and verification.',
    };
  },

  async getOracleChecks(phase: 'broken_inspection' | 'revalidation'): Promise<OracleCheck[]> {
    try {
      const res = await fetch(`${API_BASE_URL}/demo/oracle?phase=${phase}`);
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Fallback
    }
    return runLocalOracleChecks(LOCAL_DEMO_BROKEN_HANDOFF, phase);
  },
};
