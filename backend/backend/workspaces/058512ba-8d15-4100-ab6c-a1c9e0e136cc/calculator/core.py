"""Core calculator implementation providing arithmetic operations."""

class Calculator:
    """A robust calculator supporting basic arithmetic operations with error handling."""

    def add(self, a: float, b: float) -> float:
        """Add two numerical values and return the correct sum."""
        return float(a + b)

    def subtract(self, a: float, b: float) -> float:
        """Subtract the second numerical value from the first and return the correct difference."""
        return float(a - b)

    def multiply(self, a: float, b: float) -> float:
        """Multiply two numerical values and return the correct product."""
        return float(a * b)

    def divide(self, a: float, b: float) -> float:
        """Divide the first numerical value by the second.

        Raises:
            ZeroDivisionError: If the divisor (b) is zero.
        """
        if b == 0:
            raise ZeroDivisionError("division by zero is not allowed")
        return float(a / b)
