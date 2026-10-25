export interface LRUCacheOptions {
  defaultTTL?: number;
}

interface CacheNode<K, V> {
  key: K;
  value: V;
  expiresAt: number | null;
  prev: CacheNode<K, V> | null;
  next: CacheNode<K, V> | null;
}

/**
 * A production-ready generic LRU (Least Recently Used) Cache implementation with capacity enforcement,
 * optional per-entry and default TTL expiration, and strict input validation.
 *
 * Complexity characteristics:
 * - get(key): O(1) average time
 * - set(key, value, ttl?): O(1) amortized average time (triggers O(n) purgeExpired only when full)
 * - has(key): O(1) average time (does not mutate LRU ordering)
 * - delete(key): O(1) average time
 * - clear(): O(1) time
 * - getCapacity(): O(1) time
 * - size (getter): O(n) time, as it scans and purges all expired entries
 * - purgeExpired(): O(n) time, scanning all entries to purge expired items
 */
export class LRUCache<K, V> {
  private readonly capacity: number;
  private readonly defaultTTL: number | null;
  private readonly map: Map<K, CacheNode<K, V>>;
  private head: CacheNode<K, V> | null;
  private tail: CacheNode<K, V> | null;

  constructor(capacity: number, options?: LRUCacheOptions) {
    if (!Number.isInteger(capacity) || capacity <= 0) {
      throw new Error(`Invalid capacity: ${capacity}. Capacity must be a positive integer.`);
    }

    this.capacity = capacity;
    this.defaultTTL = options?.defaultTTL !== undefined ? options.defaultTTL : null;

    if (this.defaultTTL !== null && (!Number.isInteger(this.defaultTTL) || this.defaultTTL <= 0)) {
      throw new Error(`Invalid defaultTTL: ${this.defaultTTL}. TTL must be a positive integer.`);
    }

    this.map = new Map();
    this.head = null;
    this.tail = null;
  }

  /**
   * Retrieves the value associated with the key, refreshing its LRU position to MRU (head).
   * Returns undefined if the key does not exist or if the entry has expired.
   * Time complexity: O(1) average.
   */
  public get(key: K): V | undefined {
    const node = this.map.get(key);
    if (!node) {
      return undefined;
    }

    if (this.isExpired(node)) {
      this.removeNode(node);
      this.map.delete(key);
      return undefined;
    }

    this.moveToHead(node);
    return node.value;
  }

  /**
   * Inserts or updates a key-value pair in the cache with an optional custom TTL in milliseconds.
   * If the cache is at capacity when inserting a new key, expired entries are purged first.
   * If the cache is still at capacity after purging, the least-recently-used (LRU) entry is evicted.
   * Time complexity: O(1) amortized average (O(n) scan only if at capacity).
   */
  public set(key: K, value: V, ttl?: number): this {
    if (ttl !== undefined && (!Number.isInteger(ttl) || ttl <= 0)) {
      throw new Error(`Invalid TTL: ${ttl}. TTL must be a positive integer.`);
    }

    const effectiveTTL = ttl !== undefined ? ttl : this.defaultTTL;
    const expiresAt = effectiveTTL !== null ? Date.now() + effectiveTTL : null;

    let node = this.map.get(key);

    if (node) {
      node.value = value;
      node.expiresAt = expiresAt;
      this.moveToHead(node);
    } else {
      // 1. Purge expired entries first if capacity limit is reached
      if (this.map.size >= this.capacity) {
        this.purgeExpired();
      }

      // 2. If still at capacity after purging, evict the least recently used item (tail)
      if (this.map.size >= this.capacity) {
        this.evictLRU();
      }

      node = {
        key,
        value,
        expiresAt,
        prev: null,
        next: null,
      };

      this.addToHead(node);
      this.map.set(key, node);
    }

    return this;
  }

  /**
   * Checks whether a key exists in the cache and has not expired.
   * In accordance with standard cache semantics, this operation does NOT alter the LRU access order.
   * If the entry is found to have expired, it is lazily removed.
   * Time complexity: O(1) average.
   */
  public has(key: K): boolean {
    const node = this.map.get(key);
    if (!node) {
      return false;
    }

    if (this.isExpired(node)) {
      this.removeNode(node);
      this.map.delete(key);
      return false;
    }

    return true;
  }

  /**
   * Removes a key and its associated value from the cache.
   * Returns true if the key existed (and was not already expired) and was deleted, false otherwise.
   * Time complexity: O(1) average.
   */
  public delete(key: K): boolean {
    const node = this.map.get(key);
    if (!node) {
      return false;
    }

    const expired = this.isExpired(node);
    this.removeNode(node);
    this.map.delete(key);
    return !expired;
  }

  /**
   * Clears all entries from the cache and resets the doubly-linked list.
   * Time complexity: O(1).
   */
  public clear(): void {
    this.map.clear();
    this.head = null;
    this.tail = null;
  }

  /**
   * Returns the count of active, non-expired entries currently in the cache.
   * Note: This operation runs in O(n) time because it purges all expired entries.
   */
  public get size(): number {
    this.purgeExpired();
    return this.map.size;
  }

  /**
   * Returns the configured maximum capacity of the cache.
   * Time complexity: O(1).
   */
  public getCapacity(): number {
    return this.capacity;
  }

  /**
   * Iterates through all entries and purges any that have expired past their TTL.
   * Returns the number of entries purged.
   * Time complexity: O(n) where n is the number of items in the cache.
   */
  public purgeExpired(): number {
    const now = Date.now();
    let purgedCount = 0;
    for (const [key, node] of this.map.entries()) {
      if (node.expiresAt !== null && now >= node.expiresAt) {
        this.removeNode(node);
        this.map.delete(key);
        purgedCount++;
      }
    }
    return purgedCount;
  }

  private isExpired(node: CacheNode<K, V>): boolean {
    if (node.expiresAt === null) {
      return false;
    }
    return Date.now() >= node.expiresAt;
  }

  private evictLRU(): void {
    if (!this.tail) {
      return;
    }
    const lruNode = this.tail;
    this.removeNode(lruNode);
    this.map.delete(lruNode.key);
  }

  private removeNode(node: CacheNode<K, V>): void {
    if (node.prev) {
      node.prev.next = node.next;
    } else {
      this.head = node.next;
    }

    if (node.next) {
      node.next.prev = node.prev;
    } else {
      this.tail = node.prev;
    }

    node.prev = null;
    node.next = null;
  }

  private addToHead(node: CacheNode<K, V>): void {
    node.prev = null;
    node.next = this.head;

    if (this.head) {
      this.head.prev = node;
    }

    this.head = node;

    if (!this.tail) {
      this.tail = node;
    }
  }

  private moveToHead(node: CacheNode<K, V>): void {
    if (this.head === node) {
      return;
    }
    this.removeNode(node);
    this.addToHead(node);
  }
}
