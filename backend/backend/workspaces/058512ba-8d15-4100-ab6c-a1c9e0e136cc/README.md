# Production-Ready Calculator

A robust, clean Python library for basic arithmetic operations.

## Requirements Addressed

- **R001**: Addition operation (`add`)
- **R002**: Subtraction operation (`subtract`)
- **R003**: Multiplication operation (`multiply`)
- **R004**: Division operation with zero division check (`divide` raising `ZeroDivisionError`)

## Usage Example

```python
from calculator import Calculator

calc = Calculator()

print(calc.add(10, 5))      # Output: 15.0
print(calc.subtract(10, 5)) # Output: 5.0
print(calc.multiply(10, 5)) # Output: 50.0
print(calc.divide(10, 5))   # Output: 2.0

# This will raise a ZeroDivisionError:
# calc.divide(10, 0)
```

## Running Tests

```bash
python -m unittest discover -s tests
```
