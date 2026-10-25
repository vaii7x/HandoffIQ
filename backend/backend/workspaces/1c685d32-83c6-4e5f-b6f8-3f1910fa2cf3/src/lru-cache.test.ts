import test from 'node:test';
import assert from 'node:assert';
import { LRUCache, type LRUCacheOptions } from './index.js';

test('Capacity Enforcement & Validation (R001)', async (t) => {
  await t.test('should reject zero capacity', () => {
    assert.throws(() => new LRUCache(0), /Invalid capacity/);
  });

  await t.test('should reject negative capacity', () => {
    assert.throws(() => new LRUCache(-5), /Invalid capacity/);
  });

  await t.test('should reject non-integer capacity', () => {
    assert.throws(() => new LRUCache(2.5), /Invalid capacity/);
    assert.throws(() => new LRUCache(NaN), /Invalid capacity/);
    assert.throws(() => new LRUCache(Infinity), /Invalid capacity/);
  });

  await t.test('should enforce capacity limits during insertion', () => {
    const cache = new LRUCache<string, number>(2);
    cache.set('a', 1);
    cache.set('b', 2);
    assert.strictEqual(cache.size, 2);

    cache.set('c', 3); // Should evict 'a'
    assert.strictEqual(cache.size, 2);
    assert.strictEqual(cache.get('a'), undefined);
    assert.strictEqual(cache.get('b'), 2);
    assert.strictEqual(cache.get('c'), 3);
  });

  await t.test('should report configured capacity via getCapacity', () => {
    const cache = new LRUCache<string, string>(42);
    assert.strictEqual(cache.getCapacity(), 42);
  });
});

test('LRU Ordering (R003)', async (t) => {
  await t.test('should update LRU order on get() access', () => {
    const cache = new LRUCache<string, number>(2);
    cache.set('a', 1);
    cache.set('b', 2);

    // Access 'a', making 'b' the least recently used
    assert.strictEqual(cache.get('a'), 1);

    // Insert 'c', should evict 'b' instead of 'a'
    cache.set('c', 3);

    assert.strictEqual(cache.get('b'), undefined);
    assert.strictEqual(cache.get('a'), 1);
    assert.strictEqual(cache.get('c'), 3);
  });

  await t.test('should update LRU order on set() updates', () => {
    const cache = new LRUCache<string, number>(2);
    cache.set('a', 1);
    cache.set('b', 2);

    // Update 'a', making 'b' the least recently used
    cache.set('a', 10);

    // Insert 'c', should evict 'b'
    cache.set('c', 3);

    assert.strictEqual(cache.get('b'), undefined);
    assert.strictEqual(cache.get('a'), 10);
    assert.strictEqual(cache.get('c'), 3);
  });

  await t.test('should handle access order with 3+ items correctly', () => {
    const cache = new LRUCache<string, number>(3);
    cache.set('a', 1);
    cache.set('b', 2);
    cache.set('c', 3); // MRU order: c, b, a

    // Access 'b' (middle element), MRU order becomes: b, c, a
    assert.strictEqual(cache.get('b'), 2);

    // Insert 'd', should evict 'a' (oldest)
    cache.set('d', 4);
    assert.strictEqual(cache.get('a'), undefined);
    assert.strictEqual(cache.get('c'), 3);
    assert.strictEqual(cache.get('b'), 2);
    assert.strictEqual(cache.get('d'), 4);
  });

  await t.test('has() should NOT alter LRU ordering', () => {
    const cache = new LRUCache<string, number>(2);
    cache.set('first', 1);
    cache.set('second', 2);

    // Check 'first' with has() - should NOT move 'first' to MRU
    assert.strictEqual(cache.has('first'), true);

    // Insert 'third' - 'first' was still LRU and must be evicted
    cache.set('third', 3);
    assert.strictEqual(cache.has('first'), false);
    assert.strictEqual(cache.has('second'), true);
    assert.strictEqual(cache.has('third'), true);
  });
});

test('TTL Expiration and Lazy Cleanup (R002)', async (t) => {
  await t.test('should reject invalid default TTL or per-entry TTL', () => {
    assert.throws(() => new LRUCache(2, { defaultTTL: -10 }), /Invalid defaultTTL/);
    assert.throws(() => new LRUCache(2, { defaultTTL: 1.5 }), /Invalid defaultTTL/);
    assert.throws(() => new LRUCache(2, { defaultTTL: 0 }), /Invalid defaultTTL/);
    assert.throws(() => new LRUCache(2, { defaultTTL: NaN }), /Invalid defaultTTL/);

    const cache = new LRUCache<string, string>(2);
    assert.throws(() => cache.set('a', 'val', -5), /Invalid TTL/);
    assert.throws(() => cache.set('a', 'val', 2.2), /Invalid TTL/);
    assert.throws(() => cache.set('a', 'val', 0), /Invalid TTL/);
    assert.throws(() => cache.set('a', 'val', NaN), /Invalid TTL/);
  });

  await t.test('should expire items after TTL via get and has', async () => {
    const cache = new LRUCache<string, string>(3, { defaultTTL: 50 });
    cache.set('a', 'alpha');
    cache.set('b', 'beta', 200); // Longer TTL override

    assert.strictEqual(cache.get('a'), 'alpha');
    assert.strictEqual(cache.has('a'), true);

    // Wait for 'a' to expire (default TTL 50ms)
    await new Promise((resolve) => setTimeout(resolve, 80));

    assert.strictEqual(cache.get('a'), undefined);
    assert.strictEqual(cache.has('a'), false);
    // 'b' should still be alive
    assert.strictEqual(cache.get('b'), 'beta');
  });

  await t.test('should update existing entry and refresh its TTL', async () => {
    const cache = new LRUCache<string, string>(2);
    cache.set('k', 'v1', 50);

    // Re-set before expiration with a longer TTL
    cache.set('k', 'v2', 200);
    assert.strictEqual(cache.get('k'), 'v2');

    // Wait 70ms past original TTL
    await new Promise((resolve) => setTimeout(resolve, 70));
    assert.strictEqual(cache.get('k'), 'v2');
    assert.strictEqual(cache.has('k'), true);
  });

  await t.test('should revive expired key on set() with new value', async () => {
    const cache = new LRUCache<string, string>(2);
    cache.set('k', 'old_val', 25);

    await new Promise((resolve) => setTimeout(resolve, 40));
    // Now expired
    assert.strictEqual(cache.has('k'), false);

    // Set new value
    cache.set('k', 'new_val', 200);
    assert.strictEqual(cache.has('k'), true);
    assert.strictEqual(cache.get('k'), 'new_val');
  });
});

test('Regression: Expired MRU entry must be purged before capacity eviction without evicting valid LRU entry', async () => {
  // Capacity: 2
  const cache = new LRUCache<string, string>(2);

  // Step 1: Insert 'item-expired' with short TTL (30ms)
  cache.set('item-expired', 'expired-val', 30);

  // Step 2: Insert 'item-valid' with no expiration
  cache.set('item-valid', 'valid-val');

  // Step 3: Access 'item-expired' via get() to move it to MRU (head)
  // LRU ordering is now: [Head / MRU: 'item-expired', Tail / LRU: 'item-valid']
  assert.strictEqual(cache.get('item-expired'), 'expired-val');

  // Step 4: Wait > 30ms for 'item-expired' to expire
  await new Promise((resolve) => setTimeout(resolve, 55));

  // Step 5: Insert a new item 'item-new'
  // When inserting at capacity, set() MUST purge expired entries first.
  // 'item-expired' (at head) must be purged, freeing capacity.
  // 'item-valid' (at tail) must NOT be evicted.
  cache.set('item-new', 'new-val');

  // Verification:
  // 1. 'item-valid' at tail is still present and accessible
  assert.strictEqual(
    cache.has('item-valid'),
    true,
    'Valid entry at tail must NOT be evicted when an expired entry can be purged'
  );
  assert.strictEqual(cache.get('item-valid'), 'valid-val');

  // 2. 'item-expired' is gone
  assert.strictEqual(cache.has('item-expired'), false);
  assert.strictEqual(cache.get('item-expired'), undefined);

  // 3. 'item-new' is present
  assert.strictEqual(cache.has('item-new'), true);
  assert.strictEqual(cache.get('item-new'), 'new-val');

  // 4. Cache size is 2
  assert.strictEqual(cache.size, 2);
});

test('Basic Operations (get, set, has, delete, clear)', () => {
  const cache = new LRUCache<string, string>(5);

  assert.strictEqual(cache.has('x'), false);
  assert.strictEqual(cache.get('x'), undefined);
  assert.strictEqual(cache.delete('x'), false);

  cache.set('x', 'xylophone');
  assert.strictEqual(cache.has('x'), true);
  assert.strictEqual(cache.get('x'), 'xylophone');

  assert.strictEqual(cache.delete('x'), true);
  assert.strictEqual(cache.has('x'), false);

  cache.set('y', 'yacht');
  cache.set('z', 'zebra');
  assert.strictEqual(cache.size, 2);

  cache.clear();
  assert.strictEqual(cache.size, 0);
  assert.strictEqual(cache.has('y'), false);
  assert.strictEqual(cache.has('z'), false);
});

test('Node Deletion Edge Cases (Head, Tail, Middle, Single Node)', () => {
  const cache = new LRUCache<string, number>(5);

  // Single node deletion
  cache.set('single', 1);
  assert.strictEqual(cache.delete('single'), true);
  assert.strictEqual(cache.size, 0);

  // Fill 3 nodes: [MRU: c, b, a: LRU]
  cache.set('a', 1);
  cache.set('b', 2);
  cache.set('c', 3);

  // Delete head (c)
  assert.strictEqual(cache.delete('c'), true);
  assert.strictEqual(cache.size, 2);
  assert.strictEqual(cache.get('c'), undefined);
  assert.strictEqual(cache.get('b'), 2);
  assert.strictEqual(cache.get('a'), 1);

  // Delete tail (a)
  assert.strictEqual(cache.delete('a'), true);
  assert.strictEqual(cache.size, 1);
  assert.strictEqual(cache.get('a'), undefined);
  assert.strictEqual(cache.get('b'), 2);

  // Reset and test deleting middle node
  cache.clear();
  cache.set('x', 10);
  cache.set('y', 20);
  cache.set('z', 30); // order: z, y, x
  assert.strictEqual(cache.delete('y'), true);
  assert.strictEqual(cache.size, 2);
  assert.strictEqual(cache.get('y'), undefined);
  assert.strictEqual(cache.get('z'), 30);
  assert.strictEqual(cache.get('x'), 10);
});

test('Size Getter and purgeExpired() Complexity & Behavior', async () => {
  const cache = new LRUCache<string, string>(5);
  cache.set('e1', 'v1', 30);
  cache.set('e2', 'v2', 30);
  cache.set('p1', 'permanent');

  assert.strictEqual(cache.size, 3);

  // Wait 50ms for e1 and e2 to expire
  await new Promise((resolve) => setTimeout(resolve, 55));

  // Explicit purgeExpired() call should purge exactly 2 entries
  const purged = cache.purgeExpired();
  assert.strictEqual(purged, 2);

  // size should now be 1
  assert.strictEqual(cache.size, 1);
  assert.strictEqual(cache.has('p1'), true);

  // Add another expiring entry
  cache.set('e3', 'v3', 30);
  await new Promise((resolve) => setTimeout(resolve, 55));

  // size getter automatically executes purgeExpired()
  assert.strictEqual(cache.size, 1);
});
