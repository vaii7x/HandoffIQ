"""
Unit tests for the calculator operations module.
"""

import unittest
from calculator.operations import add, subtract, multiply


class TestCalculatorOperations(unittest.TestCase):

    def test_add_integers(self):
        self.assertEqual(add(5, 3), 8)

    def test_add_floats(self):
        self.assertAlmostEqual(add(2.5, 3.1), 5.6)

    def test_add_negative(self):
        self.assertEqual(add(-1, 1), 0)

    def test_subtract_integers(self):
        self.assertEqual(subtract(10, 4), 6)

    def test_subtract_floats(self):
        self.assertAlmostEqual(subtract(5.5, 2.2), 3.3)

    def test_subtract_negative(self):
        self.assertEqual(subtract(-5, -3), -2)

    def test_multiply_integers(self):
        self.assertEqual(multiply(4, 3), 12)

    def test_multiply_floats(self):
        self.assertAlmostEqual(multiply(2.0, 3.5), 7.0)

    def test_multiply_zero(self):
        self.assertEqual(multiply(5, 0), 0)


if __name__ == "__main__":
    unittest.main()
