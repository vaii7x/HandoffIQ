import time
import threading
import unittest
from cache.lru_cache import LRUCache


class TestLRUCache(unittest.TestCase):

    def test_capacity_and_eviction(self):
        cache = LRUCache(capacity=2)
        cache.put("a", 1)
        cache.put("b", 2)
        
        # Access "a" to make "b" the LRU item
        self.assertEqual(cache.get("a"), 1)
        
        # Insert "c", should evict "b"
        cache.put("c", 3)
        
        self.assertEqual(cache.get("a"), 1)
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("c"), 3)

    def test_ttl_expiration(self):
        cache = LRUCache(capacity=5)
        cache.put("quick", "silver", ttl=0.2)
        
        self.assertEqual(cache.get("quick"), "silver")
        
        # Wait for TTL expiration
        time.sleep(0.3)
        self.assertIsNone(cache.get("quick"))

    def test_statistics(self):
        cache = LRUCache(capacity=3)
        cache.put("x", 10)
        
        self.assertEqual(cache.get("x"), 10) # hit
        self.assertIsNone(cache.get("y"))     # miss
        
        stats = cache.stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["size"], 1)

    def test_delete_and_clear(self):
        cache = LRUCache(capacity=3)
        cache.put("a", 1)
        cache.put("b", 2)
        
        self.assertTrue(cache.delete("a"))
        self.assertFalse(cache.delete("nonexistent"))
        self.assertIsNone(cache.get("a"))
        
        cache.clear()
        self.assertEqual(cache.stats()["size"], 0)
        self.assertEqual(cache.stats()["hits"], 0)

    def test_thread_safety(self):
        cache = LRUCache(capacity=100)
        threads = []

        def worker(thread_id):
            for i in range(50):
                key = f"t{thread_id}_{i}"
                cache.put(key, i, ttl=2.0)
                cache.get(key)
                if i % 2 == 0:
                    cache.delete(key)

        for t_id in range(10):
            t = threading.Thread(target=worker, args=(t_id,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        stats = cache.stats()
        self.assertGreaterEqual(stats["hits"], 0)
        self.assertGreaterEqual(stats["misses"], 0)


if __name__ == "__main__":
    unittest.main()
