"""Unit tests for the Calculator class."""

import unittest
from calculator.core import Calculator

class TestCalculator(unittest.TestCase):
    """Test suite for arithmetic operations."""

    def setUp(self) -> None:
        self.calc = Calculator()

    def test_add(self) -> None:
        self.assertEqual(self.calc.add(2, 3), 5.0)
        self.assertEqual(self.calc.add(-1, 1), 0.0)
        self.assertEqual(self.calc.add(0, 0), 0.0)

    def test_subtract(self) -> None:
        self.assertEqual(self.calc.subtract(5, 3), 2.0)
        self.assertEqual(self.calc.subtract(3, 5), -2.0)
        self.assertEqual(self.calc.subtract(0, 0), 0.0)

    def test_multiply(self) -> None:
        self.assertEqual(self.calc.multiply(4, 3), 12.0)
        self.assertEqual(self.calc.multiply(-2, 3), -6.0)
        self.assertEqual(self.calc.multiply(5, 0), 0.0)

    def test_divide(self) -> None:
        self.assertEqual(self.calc.divide(6, 3), 2.0)
        self.assertEqual(self.calc.divide(5, 2), 2.5)
        with self.assertRaises(ZeroDivisionError):
            self.calc.divide(5, 0)

if __name__ == "__main__":
    unittest.main()
