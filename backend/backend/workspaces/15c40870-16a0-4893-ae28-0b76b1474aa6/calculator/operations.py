"""
Core arithmetic operations for the calculator application.
"""

from typing import Union

Number = Union[int, float]


def add(a: Number, b: Number) -> Number:
    """Take two numerical inputs and return their sum accurately."""
    return a + b


def subtract(a: Number, b: Number) -> Number:
    """Take two numerical inputs and return their difference accurately."""
    return a - b


def multiply(a: Number, b: Number) -> Number:
    """Take two numerical inputs and return their product accurately."""
    return a * b
