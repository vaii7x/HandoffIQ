# Thread-Safe LRU Cache with TTL

A high-performance, thread-safe LRU (Least Recently Used) cache implementation in Python featuring Time-To-Live (TTL) expiration, strict capacity constraints, and comprehensive operational statistics (hits/misses).

## Features
- **Capacity Constraint & LRU Eviction**: Strictly bounded capacity with O(1) time complexity for reads and writes using a doubly linked list and hash map combination.
- **TTL Expiration**: Optional Time-To-Live (TTL) support in seconds per key-value entry.
- **Thread-Safety**: Fully synchronized methods using reentrant locks (`threading.RLock`) for concurrent multi-threaded usage.
- **Dictionary-like API & Metrics**: Standard methods (`get`, `put`, `delete`, `clear`, `__len__`, `__contains__`) alongside hit/miss tracking.

## Usage Example
```python
from cache.lru_cache import LRUCache

# Create a cache with a max capacity of 2 items
cache = LRUCache(capacity=2)

cache.put("a", 1)
cache.put("b", 2, ttl=5) # expires in 5 seconds

print(cache.get("a")) # Returns 1
print(cache.stats())  # Returns hit/miss statistics
```
