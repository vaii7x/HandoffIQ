import assert from 'node:assert';
import {
  computeAuthoritativeValidation,
  mapBackendIssueToDiscrepancy,
} from '../src/utils/validationSummary.ts';

const canonicalReqs = [
  { id: 'R001', original_text: 'Core capability: Expense tracker' },
  { id: 'R002', original_text: 'User authentication and secure session management.' },
  { id: 'R003', original_text: 'Responsive layout adaptive across viewports.' },
  { id: 'R004', original_text: 'Dark theme support.' },
  { id: 'R005', original_text: 'Persistent state management and data storage.' },
];

console.log('--- Testing 7 Frontend Validation Scenarios ---');

// ==========================================
// Scenario 1: 5 requirements preserved, 0 discrepancies
// ==========================================
{
  const res = computeAuthoritativeValidation({
    canonicalRequirements: canonicalReqs,
    rawIssues: [],
    isLoading: false,
    taskRequest: 'Build a responsive expense tracker with login and a dark theme.',
  });

  assert.strictEqual(res.canonicalCount, 5);
  assert.strictEqual(res.totalDetected, 0);
  assert.strictEqual(res.totalRepaired, 0);
  assert.strictEqual(res.totalUnresolved, 0);
  assert.strictEqual(res.postRepairPreservedCount, 5);
  assert.strictEqual(res.hasUnresolvedBlockers, false);
  assert.strictEqual(res.canContinueToCoding, true);
  assert.strictEqual(res.reqComparisonStatusText, 'Passed');
  assert.strictEqual(res.reqComparisonSupportingDetail, '5 analyzed · 0 discrepancies detected');
  assert.strictEqual(res.progressStatusText, 'Validation complete: all requirements verified compliant');
  assert.strictEqual(res.stats.find(s => s.id === 'preserved')?.value, '5 / 5');
  assert.strictEqual(res.stats.find(s => s.id === 'missing')?.value, 0);
  assert.strictEqual(res.stats.find(s => s.id === 'removed')?.value, 0);
  assert.strictEqual(res.stats.find(s => s.id === 'altered')?.value, 0);
  assert.strictEqual(res.stats.find(s => s.id === 'contradiction')?.value, 0);

  // Reconciliation check
  const catSum = res.missingCount + res.removedCount + res.alteredCount + res.contradictionCount + res.addedCount + res.otherCount;
  assert.strictEqual(res.totalDetected, catSum);
  assert.strictEqual(res.totalDetected, res.totalRepaired + res.totalUnresolved);
  console.log('✓ Scenario 1 passed');
}

// ==========================================
// Scenario 2: 3 discrepancies detected, 0 repaired
// ==========================================
{
  const rawIssues = [
    {
      id: 'iss-1',
      requirement_id: 'R999',
      issue_type: 'invented_requirement',
      severity: 'high',
      description: 'Invented requirement R999',
      repair_status: 'unresolved',
    },
    {
      id: 'iss-2',
      requirement_id: 'R002',
      issue_type: 'contradiction',
      severity: 'critical',
      description: 'Payload explicitly disables authentication',
      repair_status: 'unresolved',
    },
    {
      id: 'iss-3',
      requirement_id: 'R002',
      issue_type: 'weakened_constraint',
      severity: 'high',
      description: 'allow_anonymous=True weakens authentication',
      repair_status: 'unresolved',
    },
  ];

  const res = computeAuthoritativeValidation({
    canonicalRequirements: canonicalReqs,
    rawIssues,
    isLoading: false,
    taskRequest: 'Build a responsive expense tracker with login and a dark theme.',
  });

  assert.strictEqual(res.totalDetected, 3);
  assert.strictEqual(res.totalRepaired, 0);
  assert.strictEqual(res.totalUnresolved, 3);
  assert.strictEqual(res.addedCount, 1); // invented_requirement
  assert.strictEqual(res.contradictionCount, 1); // contradiction
  assert.strictEqual(res.alteredCount, 1); // weakened_constraint
  assert.strictEqual(res.missingCount, 0);
  assert.strictEqual(res.removedCount, 0);
  assert.strictEqual(res.hasUnresolvedBlockers, true);
  assert.strictEqual(res.canContinueToCoding, false);
  assert.strictEqual(res.reqComparisonStatusText, 'Issues Found');
  assert.strictEqual(res.reqComparisonSupportingDetail, '5 analyzed · 3 discrepancies (0 repaired · 3 unresolved)');
  assert.strictEqual(res.progressStatusText, 'Clarification required: 3 unresolved discrepancy');

  // Reconciliation
  const catSum = res.missingCount + res.removedCount + res.alteredCount + res.contradictionCount + res.addedCount + res.otherCount;
  assert.strictEqual(res.totalDetected, catSum);
  assert.strictEqual(res.totalDetected, res.totalRepaired + res.totalUnresolved);
  console.log('✓ Scenario 2 passed');
}

// ==========================================
// Scenario 3: 3 discrepancies detected, all 3 repaired and successfully revalidated
// ==========================================
{
  const rawIssues = [
    {
      id: 'iss-1',
      requirement_id: 'R003',
      issue_type: 'omission',
      severity: 'medium',
      description: 'Missing requirement R003',
      repair_status: 'repaired',
    },
    {
      id: 'iss-2',
      requirement_id: 'R004',
      issue_type: 'omission',
      severity: 'low',
      description: 'Missing requirement R004',
      repair_status: 'repaired',
    },
    {
      id: 'iss-3',
      requirement_id: 'R005',
      issue_type: 'omission',
      severity: 'high',
      description: 'Missing requirement R005',
      repair_status: 'repaired',
    },
  ];

  const res = computeAuthoritativeValidation({
    canonicalRequirements: canonicalReqs,
    rawIssues,
    isLoading: false,
    taskRequest: 'Build a responsive expense tracker with login and a dark theme.',
  });

  assert.strictEqual(res.totalDetected, 3);
  assert.strictEqual(res.totalRepaired, 3);
  assert.strictEqual(res.totalUnresolved, 0);
  assert.strictEqual(res.missingCount, 3);
  assert.strictEqual(res.hasUnresolvedBlockers, false);
  assert.strictEqual(res.canContinueToCoding, true);
  assert.strictEqual(res.postRepairPreservedCount, 5); // All 5 preserved post-repair!
  assert.strictEqual(res.reqComparisonStatusText, 'Repaired');
  assert.strictEqual(res.reqComparisonSupportingDetail, '5 analyzed · 3 discrepancies (3 repaired · 0 unresolved)');
  assert.strictEqual(res.progressStatusText, '3 discrepancies detected · 3 repaired · 0 unresolved');
  assert.strictEqual(res.stats.find(s => s.id === 'preserved')?.label, 'Preserved (Post-Repair)');
  assert.strictEqual(res.stats.find(s => s.id === 'preserved')?.value, '5 / 5');

  // Reconciliation
  const catSum = res.missingCount + res.removedCount + res.alteredCount + res.contradictionCount + res.addedCount + res.otherCount;
  assert.strictEqual(res.totalDetected, catSum);
  assert.strictEqual(res.totalDetected, res.totalRepaired + res.totalUnresolved);
  console.log('✓ Scenario 3 passed');
}

// ==========================================
// Scenario 4: 3 discrepancies detected, 2 repaired and 1 unresolved
// ==========================================
{
  const rawIssues = [
    {
      id: 'iss-1',
      requirement_id: 'R004',
      issue_type: 'omission',
      severity: 'low',
      description: 'Missing requirement R004',
      repair_status: 'repaired',
    },
    {
      id: 'iss-2',
      requirement_id: 'R005',
      issue_type: 'omission',
      severity: 'high',
      description: 'Missing requirement R005',
      repair_status: 'repaired',
    },
    {
      id: 'iss-3',
      requirement_id: 'R002',
      issue_type: 'contradiction',
      severity: 'critical',
      description: 'Payload explicitly disables authentication',
      repair_status: 'unresolved',
    },
  ];

  const res = computeAuthoritativeValidation({
    canonicalRequirements: canonicalReqs,
    rawIssues,
    isLoading: false,
    taskRequest: 'Build a responsive expense tracker with login and a dark theme.',
  });

  assert.strictEqual(res.totalDetected, 3);
  assert.strictEqual(res.totalRepaired, 2);
  assert.strictEqual(res.totalUnresolved, 1);
  assert.strictEqual(res.missingCount, 2);
  assert.strictEqual(res.contradictionCount, 1);
  assert.strictEqual(res.hasUnresolvedBlockers, true);
  assert.strictEqual(res.canContinueToCoding, false);
  assert.strictEqual(res.postRepairPreservedCount, 4); // R002 has unresolved discrepancy
  assert.strictEqual(res.reqComparisonStatusText, 'Issues Found');
  assert.strictEqual(res.reqComparisonSupportingDetail, '5 analyzed · 3 discrepancies (2 repaired · 1 unresolved)');
  assert.strictEqual(res.progressStatusText, 'Clarification required: 1 unresolved discrepancy');

  // Reconciliation
  const catSum = res.missingCount + res.removedCount + res.alteredCount + res.contradictionCount + res.addedCount + res.otherCount;
  assert.strictEqual(res.totalDetected, catSum);
  assert.strictEqual(res.totalDetected, res.totalRepaired + res.totalUnresolved);
  console.log('✓ Scenario 4 passed');
}

// ==========================================
// Scenario 5: A requirement weakened without changing its ID
// ==========================================
{
  const rawIssues = [
    {
      id: 'iss-1',
      requirement_id: 'R002',
      issue_type: 'weakened_constraint',
      severity: 'high',
      description: 'Security constraint was weakened in handoff payload: allow_anonymous=True.',
      observed_value: 'allow_anonymous=True',
      repair_status: 'unresolved',
    },
  ];

  const res = computeAuthoritativeValidation({
    canonicalRequirements: canonicalReqs,
    rawIssues,
    isLoading: false,
    taskRequest: 'Build a responsive expense tracker with login and a dark theme.',
  });

  assert.strictEqual(res.totalDetected, 1);
  assert.strictEqual(res.alteredCount, 1);
  assert.strictEqual(res.totalUnresolved, 1);
  assert.strictEqual(res.totalRepaired, 0);
  assert.strictEqual(res.hasUnresolvedBlockers, true);
  assert.strictEqual(res.canContinueToCoding, false);
  assert.strictEqual(res.postRepairPreservedCount, 4);
  assert(res.unresolvedRequirementIds.has('R002'));

  // Reconciliation
  const catSum = res.missingCount + res.removedCount + res.alteredCount + res.contradictionCount + res.addedCount + res.otherCount;
  assert.strictEqual(res.totalDetected, catSum);
  assert.strictEqual(res.totalDetected, res.totalRepaired + res.totalUnresolved);
  console.log('✓ Scenario 5 passed');
}

// ==========================================
// Scenario 6: A requirement missing entirely from received handoff
// ==========================================
{
  // 6A: Unrepaired omission
  const rawIssuesUnrepaired = [
    {
      id: 'iss-1',
      requirement_id: 'R005',
      issue_type: 'omission',
      severity: 'high',
      description: 'Canonical requirement R005 is missing from the handoff requirement_ids.',
      repair_status: 'unresolved',
    },
  ];

  const resA = computeAuthoritativeValidation({
    canonicalRequirements: canonicalReqs,
    rawIssues: rawIssuesUnrepaired,
    isLoading: false,
    taskRequest: 'Build a responsive expense tracker with login and a dark theme.',
  });

  assert.strictEqual(resA.totalDetected, 1);
  assert.strictEqual(resA.missingCount, 1);
  assert.strictEqual(resA.totalUnresolved, 1);
  assert.strictEqual(resA.canContinueToCoding, false);
  assert.strictEqual(resA.postRepairPreservedCount, 4);
  assert(resA.unresolvedRequirementIds.has('R005'));

  // 6B: Repaired omission
  const rawIssuesRepaired = [
    {
      id: 'iss-1',
      requirement_id: 'R005',
      issue_type: 'omission',
      severity: 'high',
      description: 'Canonical requirement R005 is missing from the handoff requirement_ids.',
      repair_status: 'repaired',
    },
  ];

  const resB = computeAuthoritativeValidation({
    canonicalRequirements: canonicalReqs,
    rawIssues: rawIssuesRepaired,
    isLoading: false,
    taskRequest: 'Build a responsive expense tracker with login and a dark theme.',
  });

  assert.strictEqual(resB.totalDetected, 1);
  assert.strictEqual(resB.missingCount, 1);
  assert.strictEqual(resB.totalRepaired, 1);
  assert.strictEqual(resB.totalUnresolved, 0);
  assert.strictEqual(resB.canContinueToCoding, true);
  assert.strictEqual(resB.postRepairPreservedCount, 5);

  console.log('✓ Scenario 6 passed');
}

// ==========================================
// Scenario 7: Contradictory or ambiguous requirements that need review
// ==========================================
{
  const rawIssues = [
    {
      id: 'iss-1',
      requirement_id: 'R002',
      issue_type: 'contradiction',
      severity: 'critical',
      description: 'Explicit contradiction on requirement R002: auth_enabled=False',
      repair_status: 'unresolved',
    },
  ];

  const res = computeAuthoritativeValidation({
    canonicalRequirements: canonicalReqs,
    rawIssues,
    isLoading: false,
    taskRequest: 'Build a responsive expense tracker with login and a dark theme.',
  });

  assert.strictEqual(res.totalDetected, 1);
  assert.strictEqual(res.contradictionCount, 1);
  assert.strictEqual(res.totalUnresolved, 1);
  assert.strictEqual(res.hasUnresolvedBlockers, true);
  assert.strictEqual(res.canContinueToCoding, false);
  assert.strictEqual(res.reqComparisonStatusText, 'Issues Found');
  assert.strictEqual(res.constraintsRisksStatusText, 'Review Required');
  assert.strictEqual(res.progressStatusText, 'Clarification required: 1 unresolved discrepancy');

  // Reconciliation
  const catSum = res.missingCount + res.removedCount + res.alteredCount + res.contradictionCount + res.addedCount + res.otherCount;
  assert.strictEqual(res.totalDetected, catSum);
  assert.strictEqual(res.totalDetected, res.totalRepaired + res.totalUnresolved);
  console.log('✓ Scenario 7 passed');
}

// ==========================================
// Scenario 8: Food-Ordering 10 Broken Discrepancies Verification
// ==========================================
{
  const foodCanonicalReqs = [
    { id: 'R001', original_text: 'User authentication with securely hashed passwords using bcrypt.' },
    { id: 'R002', original_text: 'Delivery fee calculation ($5 flat fee on orders under $30).' },
    { id: 'R003', original_text: 'Full order placement rejecting partial orders if any item unavailable.' },
    { id: 'R004', original_text: 'Atomic inventory deduction within a database transaction.' },
    { id: 'R005', original_text: 'Idempotent payment processing preventing duplicate charges.' },
    { id: 'R006', original_text: 'Strict role-based authorization for order cancellation.' },
    { id: 'R007', original_text: 'Single inventory restoration ensuring stock restored once on cancel.' },
    { id: 'R008', original_text: 'Server-side validation of order payload, item prices, and totals.' },
    { id: 'R009', original_text: 'Complete automated test coverage for orders, payments, and inventory.' },
    { id: 'R010', original_text: 'Persistent PostgreSQL database storage.' },
  ];

  const brokenFoodIssues = [
    {
      id: 'iss-1',
      requirement_id: 'R001',
      issue_type: 'weakened_constraint',
      severity: 'critical',
      description: 'Security constraint weakened on requirement R001: Passwords are stored in plaintext.',
      original_value: 'User authentication with securely hashed passwords using bcrypt.',
      observed_value: 'Plaintext password storage',
      repair_status: 'unresolved',
      evidence: ['Payload specifies plaintext password storage'],
    },
    {
      id: 'iss-2',
      requirement_id: 'R002',
      issue_type: 'omission',
      severity: 'high',
      description: 'Canonical requirement R002 was omitted from handoff specification.',
      original_value: 'Delivery fee calculation ($5 flat fee on orders under $30).',
      observed_value: 'Omitted from handoff specification',
      repair_status: 'unresolved',
      evidence: ['Delivery fee is omitted from handoff specification'],
    },
    {
      id: 'iss-3',
      requirement_id: 'R003',
      issue_type: 'weakened_constraint',
      severity: 'high',
      description: 'Business rule weakened on requirement R003: Handoff permits partial orders.',
      original_value: 'Full order placement rejecting partial orders.',
      observed_value: 'Allow partial order fulfillment',
      repair_status: 'unresolved',
      evidence: ['Payload permits partial order fulfillment'],
    },
    {
      id: 'iss-4',
      requirement_id: 'R004',
      issue_type: 'contradiction',
      severity: 'critical',
      description: 'Contradiction on requirement R004: Non-atomic inventory updates.',
      original_value: 'Atomic inventory deduction within a database transaction.',
      observed_value: 'Non-atomic inventory updates',
      repair_status: 'unresolved',
      evidence: ['Payload specifies non-atomic inventory updates'],
    },
    {
      id: 'iss-5',
      requirement_id: 'R005',
      issue_type: 'contradiction',
      severity: 'critical',
      description: 'Contradiction on requirement R005: Duplicate payment risk.',
      original_value: 'Idempotent payment processing preventing duplicate charges.',
      observed_value: 'Non-idempotent charge endpoint with duplicate payment risk',
      repair_status: 'unresolved',
      evidence: ['Payload lacks idempotency guarantees'],
    },
    {
      id: 'iss-6',
      requirement_id: 'R006',
      issue_type: 'weakened_constraint',
      severity: 'critical',
      description: 'Authorization gap on requirement R006: Unauthenticated cancellation endpoint.',
      original_value: 'Strict role-based authorization for order cancellation.',
      observed_value: 'Unauthenticated cancellation endpoint',
      repair_status: 'unresolved',
      evidence: ['Payload indicates unauthenticated cancellation'],
    },
    {
      id: 'iss-7',
      requirement_id: 'R007',
      issue_type: 'weakened_constraint',
      severity: 'high',
      description: 'Integrity constraint weakened on requirement R007: Repeated inventory restoration.',
      original_value: 'Single inventory restoration.',
      observed_value: 'Repeated inventory restoration on retries',
      repair_status: 'unresolved',
      evidence: ['Payload permits repeated inventory restoration'],
    },
    {
      id: 'iss-8',
      requirement_id: 'R008',
      issue_type: 'weakened_constraint',
      severity: 'high',
      description: 'Integrity constraint weakened on requirement R008: Frontend-only validation.',
      original_value: 'Server-side validation of order payload, item prices, and totals.',
      observed_value: 'Frontend-only validation',
      repair_status: 'unresolved',
      evidence: ['Payload specifies frontend-only validation'],
    },
    {
      id: 'iss-9',
      requirement_id: 'R009',
      issue_type: 'implementation_gap',
      severity: 'high',
      description: 'Testing coverage gap on requirement R009: Automated tests are incomplete.',
      original_value: 'Complete automated test coverage.',
      observed_value: 'Incomplete test coverage / tests skipped',
      repair_status: 'unresolved',
      evidence: ['Payload indicates incomplete test coverage'],
    },
    {
      id: 'iss-10',
      requirement_id: 'R010',
      issue_type: 'contradiction',
      severity: 'critical',
      description: 'Contradiction on requirement R010: In-memory storage used instead of PostgreSQL.',
      original_value: 'Persistent PostgreSQL database storage.',
      observed_value: 'In-memory dictionary storage',
      repair_status: 'unresolved',
      evidence: ['Payload specifies in-memory storage opposing database requirement'],
    },
  ];

  const res = computeAuthoritativeValidation({
    canonicalRequirements: foodCanonicalReqs,
    rawIssues: brokenFoodIssues,
    isLoading: false,
    taskRequest: 'Build a robust food ordering backend platform.',
  });

  assert.strictEqual(res.canonicalCount, 10);
  assert.strictEqual(res.analyzedCount, 10);
  assert.strictEqual(res.totalDetected, 10);
  assert.strictEqual(res.totalRepaired, 0);
  assert.strictEqual(res.totalUnresolved, 10);
  assert.strictEqual(res.postRepairPreservedCount, 0); // 0/10 preserved because all 10 have unresolved discrepancies
  assert.strictEqual(res.hasUnresolvedBlockers, true);
  assert.strictEqual(res.canContinueToCoding, false);
  assert.strictEqual(res.stats.find(s => s.id === 'preserved')?.value, '0 / 10');
  assert.strictEqual(res.missingCount, 1);
  assert.strictEqual(res.contradictionCount, 3);
  assert.strictEqual(res.alteredCount, 5);
  assert.strictEqual(res.otherCount, 1); // implementation_gap mapped to other

  // Perfect mathematical reconciliation
  const catSum = res.missingCount + res.removedCount + res.alteredCount + res.contradictionCount + res.addedCount + res.otherCount;
  assert.strictEqual(res.totalDetected, catSum);
  assert.strictEqual(res.totalDetected, res.totalRepaired + res.totalUnresolved);
  console.log('✓ Scenario 8 passed (Food-Ordering 10 Broken Discrepancies Reconciled)');

  // Valid Paraphrased Handoff Check (10/10 Preserved, 0 Discrepancies)
  const validRes = computeAuthoritativeValidation({
    canonicalRequirements: foodCanonicalReqs,
    rawIssues: [],
    isLoading: false,
    taskRequest: 'Build a robust food ordering backend platform.',
  });
  assert.strictEqual(validRes.canonicalCount, 10);
  assert.strictEqual(validRes.totalDetected, 0);
  assert.strictEqual(validRes.postRepairPreservedCount, 10);
  assert.strictEqual(validRes.hasUnresolvedBlockers, false);
  assert.strictEqual(validRes.canContinueToCoding, true);
  assert.strictEqual(validRes.stats.find(s => s.id === 'preserved')?.value, '10 / 10');
  console.log('✓ Scenario 8B passed (Food-Ordering Valid Paraphrased Handoff 10/10 Preserved)');
}

// ==========================================
// Scenario 9: 36-Requirement Pharmacy System (Broken Handoff vs Compliant Handoff)
// ==========================================
{
  const pharmacyCanonicalReqs = Array.from({ length: 36 }, (_, i) => ({
    id: `R${String(i + 1).padStart(3, '0')}`,
    source_id: `R${i + 1}`,
    original_text: `Pharmacy specification R${i + 1}`,
  }));

  const brokenSourceIds = [
    'R2', 'R5', 'R7', 'R8', 'R9', 'R12', 'R13', 'R14', 'R15', 'R16', 'R17',
    'R18', 'R19', 'R20', 'R21', 'R22', 'R23', 'R24', 'R25', 'R26', 'R27',
    'R28', 'R29', 'R30', 'R31', 'R32', 'R33', 'R34', 'R35', 'R36'
  ];

  const brokenPharmacyIssues = brokenSourceIds.map((sid, idx) => ({
    id: `iss-pharm-${idx}`,
    requirement_id: sid,
    issue_type: ['R7', 'R12', 'R13', 'R15', 'R19', 'R20', 'R21', 'R22', 'R23', 'R25', 'R26', 'R35'].includes(sid)
      ? 'contradiction'
      : ['R34', 'R36'].includes(sid)
      ? 'implementation_gap'
      : 'weakened_constraint',
    severity: ['R17'].includes(sid) ? 'medium' : 'critical',
    description: `Discrepancy detected on requirement ${sid}`,
    original_value: `Expected invariant for ${sid}`,
    observed_value: `Broken specification for ${sid}`,
    repair_status: 'unresolved',
    evidence: [`Downstream handoff explicitly violates ${sid}`],
  }));

  const res = computeAuthoritativeValidation({
    canonicalRequirements: pharmacyCanonicalReqs,
    rawIssues: brokenPharmacyIssues,
    isLoading: false,
    taskRequest: 'Build a production-oriented hospital pharmacy system with React and FastAPI.',
  });

  assert.strictEqual(res.canonicalCount, 36);
  assert.strictEqual(res.analyzedCount, 36);
  assert.strictEqual(res.totalDetected, 30);
  assert.strictEqual(res.totalRepaired, 0);
  assert.strictEqual(res.totalUnresolved, 30);
  assert.strictEqual(res.postRepairPreservedCount, 6); // 36 - 30 = 6 preserved
  assert.strictEqual(res.hasUnresolvedBlockers, true);
  assert.strictEqual(res.canContinueToCoding, false);
  assert.strictEqual(res.stats.find(s => s.id === 'preserved')?.value, '6 / 36');

  // Exact category reconciliation
  const catSum = res.missingCount + res.removedCount + res.alteredCount + res.contradictionCount + res.addedCount + res.otherCount;
  assert.strictEqual(res.totalDetected, catSum);
  assert.strictEqual(res.totalDetected, res.totalRepaired + res.totalUnresolved);
  console.log('✓ Scenario 9 passed (Pharmacy 36 Requirements - Broken Handoff Firmly Blocked)');

  // Compliant Handoff Check (36/36 Preserved, 0 Discrepancies)
  const validPharmacyRes = computeAuthoritativeValidation({
    canonicalRequirements: pharmacyCanonicalReqs,
    rawIssues: [],
    isLoading: false,
    taskRequest: 'Build a production-oriented hospital pharmacy system with React and FastAPI.',
  });
  assert.strictEqual(validPharmacyRes.canonicalCount, 36);
  assert.strictEqual(validPharmacyRes.totalDetected, 0);
  assert.strictEqual(validPharmacyRes.postRepairPreservedCount, 36);
  assert.strictEqual(validPharmacyRes.hasUnresolvedBlockers, false);
  assert.strictEqual(validPharmacyRes.canContinueToCoding, true);
  assert.strictEqual(validPharmacyRes.stats.find(s => s.id === 'preserved')?.value, '36 / 36');
  console.log('✓ Scenario 9B passed (Pharmacy 36 Requirements - Compliant Handoff 36/36 Preserved)');
}

console.log('All frontend validation scenarios verified successfully!');
