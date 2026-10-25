# Generic LRU Cache in TypeScript

A production-grade, highly optimized generic LRU (Least Recently Used) Cache implementation in TypeScript with capacity enforcement, strict input validation, and optional per-item or default TTL (Time-To-Live) expiration with automated lazy cleanup and pre-eviction purge.

## Features

- **Generic Type Support (`LRUCache<K, V>`)**: Fully typed keys and values.
- **Strict Capacity Enforcement**: Rejects zero, negative, non-integer, or non-finite capacities with descriptive errors.
- **TTL Expiration & Lazy Cleanup**: Global default TTL or per-entry TTL overrides with automatic lazy eviction upon access.
- **Pre-Eviction Expired Item Purge**: When cache is at capacity, expired items (even those at the MRU head) are purged before capacity-based eviction, preventing premature eviction of valid LRU items.
- **Accurate Semantics**: `has()` checks existence and purges expired entries without altering LRU order; `get()` updates LRU order to MRU.
- **Node.js Native Test Suite**: Comprehensive tests covering edge cases, TTL lifecycles, and eviction regressions.

## Complexity Analysis

| Operation | Time Complexity | Description |
|---|---|---|
| `get(key)` | $O(1)$ average | Hash map lookup + doubly-linked list node relocation to MRU head. |
| `set(key, value, ttl?)` | $O(1)$ amortized | Hash map insertion / update. If at capacity, executes a linear purge scan to remove expired items before evicting the LRU tail. |
| `has(key)` | $O(1)$ average | Existence check + lazy expiration cleanup. Does **not** mutate LRU ordering. |
| `delete(key)` | $O(1)$ average | Hash map lookup and node detachment from the doubly-linked list. |
| `clear()` | $O(1)$ | Clears the map and nullifies list head/tail references. |
| `getCapacity()` | $O(1)$ | Returns the configured positive integer capacity. |
| **`size` (getter)** | **$O(n)$** | **Scans all entries to purge expired items before returning the count of active entries.** |
| **`purgeExpired()`** | **$O(n)$** | **Iterates through all entries in the cache to detect and remove expired nodes.** |

> **Complexity Note**: While core data structure lookups and pointer updates run in $O(1)$ time, querying `size` and calling `purgeExpired()` perform a full scan of all $n$ entries ($O(n)$). In `set()`, an $O(n)$ expired-entry purge is triggered only when the cache has reached maximum capacity to avoid evicting valid entries prematurely.

## Installation & Setup

Clone the repository and install dependencies:

```bash
npm install
```

## Usage Example

```typescript
import { LRUCache } from './src/index.js'; // or from 'generic-lru-cache' once installed

// Initialize cache with a maximum capacity of 3 and default TTL of 5000ms
const cache = new LRUCache<string, string>(3, { defaultTTL: 5000 });

// Insert items
cache.set('session_1', 'user_data_alice');
cache.set('session_2', 'user_data_bob');

// Retrieve item (refreshes position to MRU head)
console.log(cache.get('session_1')); // 'user_data_alice'

// Check existence (does not affect LRU ordering)
console.log(cache.has('session_2')); // true

// Custom per-item TTL override (1000ms)
cache.set('temp_token', 'token_xyz', 1000);

// Expired items are purged automatically when at capacity or when querying size
console.log(cache.size); // O(n) purge + active count

// Delete item
cache.delete('session_2');

// Clear all entries
cache.clear();
```

## Running Tests

Run the test suite using Node.js's built-in test runner:

```bash
npm test
```

## Build

Compile TypeScript declarations and JavaScript bundles to `dist/`:

```bash
npm run build
```

## License

MIT
