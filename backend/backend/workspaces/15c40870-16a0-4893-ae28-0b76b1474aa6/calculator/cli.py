"""
Command Line Interface for the calculator application.
"""

import sys
from typing import Union
from .operations import add, subtract, multiply

Number = Union[int, float]


def get_number(prompt: str) -> Number:
    """Prompt the user until a valid number is entered."""
    while True:
        try:
            value = input(prompt).strip()
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            print("Invalid input. Please enter a valid number.")


def run_cli() -> None:
    """Run the interactive command line interface loop."""
    print("=== Python CLI Calculator ===")
    print("Supported operations:")
    print("  1. Addition (+)")
    print("  2. Subtraction (-)")
    print("  3. Multiplication (*)")
    print("  4. Exit")

    while True:
        print("\n-----------------------------")
        choice = input("Select an operation (1-4): ").strip()

        if choice == '4':
            print("Exiting calculator. Goodbye!")
            sys.exit(0)

        if choice not in ('1', '2', '3'):
            print("Invalid choice. Please select a number between 1 and 4.")
            continue

        num1 = get_number("Enter first number: ")
        num2 = get_number("Enter second number: ")

        try:
            if choice == '1':
                result = add(num1, num2)
                print(f"Result: {num1} + {num2} = {result}")
            elif choice == '2':
                result = subtract(num1, num2)
                print(f"Result: {num1} - {num2} = {result}")
            elif choice == '3':
                result = multiply(num1, num2)
                print(f"Result: {num1} * {num2} = {result}")
        except Exception as e:
            print(f"An error occurred during calculation: {e}")
