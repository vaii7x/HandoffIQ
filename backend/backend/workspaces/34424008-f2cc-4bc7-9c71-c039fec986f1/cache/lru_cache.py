import time
import threading
from typing import Any, Optional, Dict, Tuple


class _Node:
    __slots__ = ('key', 'value', 'expiry', 'prev', 'next')

    def __init__(self, key: Any = None, value: Any = None, expiry: Optional[float] = None):
        self.key = key
        self.value = value
        self.expiry = expiry
        self.prev: Optional['_Node'] = None
        self.next: Optional['_Node'] = None


class LRUCache:
    """A thread-safe LRU cache supporting capacity limits, TTL expiration, and statistics."""

    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("Capacity must be greater than 0")
        
        self._capacity = capacity
        self._cache: Dict[Any, _Node] = {}
        self._lock = threading.RLock()
        
        # Statistics counters
        self._hits = 0
        self._misses = 0
        
        # Sentinel nodes for doubly linked list
        self._head = _Node()
        self._tail = _Node()
        self._head.next = self._tail
        self._tail.prev = self._head

    def get(self, key: Any, default: Any = None) -> Any:
        """Retrieve the value associated with the key. Returns default if not found or expired."""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return default

            node = self._cache[key]
            
            # Check for TTL expiration
            if node.expiry is not None and time.time() >= node.expiry:
                self._remove_node(node)
                del self._cache[key]
                self._misses += 1
                return default

            # Move to front (most recently used)
            self._move_to_head(node)
            self._hits += 1
            return node.value

    def put(self, key: Any, value: Any, ttl: Optional[float] = None) -> None:
        """Insert or update a key-value pair with an optional TTL in seconds."""
        with self._lock:
            expiry = time.time() + ttl if ttl is not None else None

            if key in self._cache:
                node = self._cache[key]
                node.value = value
                node.expiry = expiry
                self._move_to_head(node)
                return

            if len(self._cache) >= self._capacity:
                # Evict the Least Recently Used item (node right before tail)
                lru = self._tail.prev
                if lru is not self._head:
                    self._remove_node(lru)
                    del self._cache[lru.key]

            # Insert new node
            new_node = _Node(key=key, value=value, expiry=expiry)
            self._cache[key] = new_node
            self._add_to_head(new_node)

    def delete(self, key: Any) -> bool:
        """Remove a key from the cache. Returns True if found, False otherwise."""
        with self._lock:
            if key not in self._cache:
                return False
            
            node = self._cache[key]
            self._remove_node(node)
            del self._cache[key]
            return True

    def clear(self) -> None:
        """Clear all entries and reset statistics in the cache."""
        with self._lock:
            self._cache.clear()
            self._head.next = self._tail
            self._tail.prev = self._head
            self._hits = 0
            self._misses = 0

    def stats(self) -> Dict[str, int]:
        """Return cache hit and miss statistics."""
        with self._lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "size": len(self._cache),
                "capacity": self._capacity
            }

    def _add_to_head(self, node: _Node) -> None:
        node.prev = self._head
        node.next = self._head.next
        self._head.next.prev = node
        self._head.next = node

    def _remove_node(self, node: _Node) -> None:
        prev_node = node.prev
        next_node = node.next
        if prev_node is not None:
            prev_node.next = next_node
        if next_node is not None:
            next_node.prev = prev_node

    def _move_to_head(self, node: _Node) -> None:
        self._remove_node(node)
        self._add_to_head(node)

    def __len__(self) -> int:
        with self._lock:
            # Purge expired items count optionally, or return current dict length
            return len(self._cache)

    def __contains__(self, key: Any) -> bool:
        return self.get(key) is not None
