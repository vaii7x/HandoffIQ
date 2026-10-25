import assert from 'node:assert';
import {
  LOCAL_DEMO_REQUIREMENTS,
  LOCAL_DEMO_BROKEN_HANDOFF,
  LOCAL_DEMO_REPAIRS,
  runLocalOracleChecks,
  demoService,
} from '../src/services/demoService.ts';

console.log('--- Testing HandoffIQ Demo Mode End-to-End Test Suite ---');

// ============================================================================
// Test 1: Canonical Requirements Structure & Authoritative Invariants
// ============================================================================
{
  console.log('\n[Test 1] Verifying Canonical Requirements (R1-R6)...');
  assert.strictEqual(
    LOCAL_DEMO_REQUIREMENTS.length,
    6,
    'Demo mode must define exactly 6 canonical requirements'
  );

  const reqIds = LOCAL_DEMO_REQUIREMENTS.map((r) => r.source_id);
  assert.deepStrictEqual(
    reqIds,
    ['R1', 'R2', 'R3', 'R4', 'R5', 'R6'],
    'Source IDs must map R1 through R6 in order'
  );

  for (const req of LOCAL_DEMO_REQUIREMENTS) {
    assert.ok(req.authoritative, `Requirement ${req.source_id} must be authoritative`);
    assert.ok(req.title && req.title.length > 5, `Requirement ${req.source_id} missing valid title`);
    assert.ok(req.description && req.description.length > 10, `Requirement ${req.source_id} missing valid description`);
    assert.ok(req.category && req.category.length > 3, `Requirement ${req.source_id} missing valid category`);
  }
  console.log('✓ Canonical requirements verified (6/6 authoritative, fully formed)');
}

// ============================================================================
// Test 2: Broken Handoff Fixture (5 Seeded Defects D1-D5, 1 Preserved R6)
// ============================================================================
{
  console.log('\n[Test 2] Verifying Broken Handoff Fixture (5 Defects + 1 Control)...');
  assert.strictEqual(
    LOCAL_DEMO_BROKEN_HANDOFF.length,
    6,
    'Broken handoff fixture must contain 6 items corresponding to R1-R6'
  );

  const brokenItems = LOCAL_DEMO_BROKEN_HANDOFF.filter((i) => i.status === 'broken');
  assert.strictEqual(brokenItems.length, 5, 'Exactly 5 seeded defects must be present (D1-D5)');

  const preservedItems = LOCAL_DEMO_BROKEN_HANDOFF.filter((i) => i.status === 'preserved');
  assert.strictEqual(preservedItems.length, 1, 'Exactly 1 preserved negative control must be present (R6)');

  const r6 = preservedItems[0];
  assert.strictEqual(r6.requirement_id, 'R6');
  assert.strictEqual(r6.received_text, r6.original_text, 'Preserved negative control must match original text identically');
  assert.strictEqual(r6.defect_id, null, 'Negative control must have defect_id = null');

  const defectIds = brokenItems.map((i) => i.defect_id).sort();
  assert.deepStrictEqual(defectIds, ['D1', 'D2', 'D3', 'D4', 'D5']);

  console.log('✓ Broken handoff fixture verified (D1-D5 broken, R6 preserved negative control)');
}

// ============================================================================
// Test 3: Deterministic Demo Oracle (Broken Phase Checks)
// ============================================================================
{
  console.log('\n[Test 3] Verifying Oracle Checks on Broken Handoff...');
  const oracleChecks = runLocalOracleChecks(LOCAL_DEMO_BROKEN_HANDOFF, 'broken_inspection');
  assert.strictEqual(oracleChecks.length, 6, 'Oracle must perform 6 checks (5 defects + 1 control)');

  const allPassed = oracleChecks.every((c) => c.passed);
  assert.ok(allPassed, 'All 6 oracle checks must pass on the broken fixture');

  const d1Check = oracleChecks.find((c) => c.check_id === 'ORACLE-D1');
  assert.ok(d1Check?.passed, 'Oracle D1 check must confirm cross-patient record access defect');

  const d2Check = oracleChecks.find((c) => c.check_id === 'ORACLE-D2');
  assert.ok(d2Check?.passed, 'Oracle D2 check must confirm plaintext password storage defect');

  const d3Check = oracleChecks.find((c) => c.check_id === 'ORACLE-D3');
  assert.ok(d3Check?.passed, 'Oracle D3 check must confirm concurrency protection loss defect');

  const d4Check = oracleChecks.find((c) => c.check_id === 'ORACLE-D4');
  assert.ok(d4Check?.passed, 'Oracle D4 check must confirm partial transaction failure defect');

  const d5Check = oracleChecks.find((c) => c.check_id === 'ORACLE-D5');
  assert.ok(d5Check?.passed, 'Oracle D5 check must confirm duplicate payment retry defect');

  const r6Check = oracleChecks.find((c) => c.check_id === 'ORACLE-R6-CONTROL');
  assert.ok(r6Check?.passed, 'Oracle R6 check must confirm preserved expiration rule');

  console.log('✓ Oracle broken inspection verified (all 6 seeded assertions pass)');
}

// ============================================================================
// Test 4: Validation Engine Response & Discrepancy Attribution
// ============================================================================
(async () => {
  console.log('\n[Test 4] Verifying Validation Service Execution & Discrepancies...');
  const valRes = await demoService.validateHandoff();

  assert.strictEqual(valRes.validator_detected_count, 5, 'Validator must detect all 5 discrepancies');
  assert.strictEqual(valRes.oracle_seeded_defect_count, 5, 'Oracle must confirm 5 seeded defects');
  assert.strictEqual(valRes.preserved_count, 1, 'Validator must confirm 1 preserved negative control');
  assert.strictEqual(valRes.all_seeded_defects_detected, true, 'all_seeded_defects_detected flag must be true');
  assert.strictEqual(valRes.missed_defects.length, 0, 'No seeded defects should be missed');
  assert.strictEqual(valRes.discrepancies.length, 5, 'Discrepancies list must contain 5 items');

  const detectedReqIds = valRes.discrepancies.map((d) => d.requirement_id).sort();
  assert.deepStrictEqual(detectedReqIds, ['R1', 'R2', 'R3', 'R4', 'R5']);

  for (const disc of valRes.discrepancies) {
    assert.ok(disc.validator_detected, `Discrepancy ${disc.requirement_id} must have validator_detected = true`);
    assert.ok(disc.oracle_detected, `Discrepancy ${disc.requirement_id} must have oracle_detected = true`);
    assert.strictEqual(disc.is_missed_by_validator, false, `Discrepancy ${disc.requirement_id} must not be missed`);
    assert.ok(disc.explanation.length > 15, `Discrepancy ${disc.requirement_id} explanation missing`);
    assert.ok(disc.evidence.length > 0, `Discrepancy ${disc.requirement_id} evidence missing`);
    assert.strictEqual(disc.severity, 'critical', `Discrepancy ${disc.requirement_id} severity must be critical`);
  }

  assert.strictEqual(valRes.preserved_requirement.requirement_id, 'R6');
  assert.strictEqual(valRes.preserved_requirement.status, 'preserved');
  console.log('✓ Validation service verified (5 detected, 0 missed, 1 preserved control, evidence preserved)');

  // ============================================================================
  // Test 5: Synthetic Repair Diffs & Explanations
  // ============================================================================
  console.log('\n[Test 5] Verifying Synthetic Repair Items (REP-1 to REP-5)...');
  const repairs = await demoService.getRepairs();
  assert.strictEqual(repairs.length, 5, 'Repairs fixture must contain 5 items');

  const repReqIds = repairs.map((r) => r.requirement_id).sort();
  assert.deepStrictEqual(repReqIds, ['R1', 'R2', 'R3', 'R4', 'R5']);

  for (const rep of repairs) {
    assert.strictEqual(rep.status, 'repaired');
    assert.ok(rep.diff_before.startsWith('- '), `Repair ${rep.id} diff_before must start with "- "`);
    assert.ok(rep.diff_after.startsWith('+ '), `Repair ${rep.id} diff_after must start with "+ "`);
    assert.ok(rep.repair_reason.length > 15, `Repair ${rep.id} repair_reason missing or short`);
    assert.notStrictEqual(rep.broken_text, rep.repaired_text, `Repair ${rep.id} broken and repaired must differ`);
  }
  console.log('✓ Synthetic repairs verified (5 readable diffs, clear repair rationales)');

  // ============================================================================
  // Test 6: Revalidation Engine & Oracle Assertion
  // ============================================================================
  console.log('\n[Test 6] Verifying Revalidation & Certification...');
  const revalRes = await demoService.revalidateHandoff();

  assert.strictEqual(revalRes.validator_issues_count, 0, 'Revalidation validator issues count must be 0');
  assert.strictEqual(revalRes.unresolved_count, 0, 'Revalidation unresolved count must be 0');
  assert.strictEqual(revalRes.resolved_count, 5, 'Revalidation resolved count must be 5');
  assert.strictEqual(revalRes.all_clear, true, 'all_clear must be true');
  assert.strictEqual(revalRes.oracle_passed, true, 'oracle_passed must be true');
  assert.strictEqual(revalRes.remaining_issues.length, 0, 'remaining_issues must be empty array');

  assert.ok(revalRes.oracle_checks.length >= 6, 'Oracle revalidation checks must cover all 6 requirements');
  assert.ok(revalRes.oracle_checks.every((c) => c.passed), 'Every revalidation oracle assertion must pass');

  // Verify mandatory disclaimer
  assert.ok(
    revalRes.disclaimer.includes('Note: A corrected specification does not prove the generated code implements it'),
    'Mandatory disclaimer must be present verbatim'
  );
  console.log('✓ Revalidation verified (0 issues, 100% oracle pass, mandatory disclaimer present)');

  console.log('\n====================================================================');
  console.log('ALL DEMO MODE FRONTEND TESTS PASSED SUCCESSFULLY (6/6 SUITES)');
  console.log('====================================================================\n');
})();
