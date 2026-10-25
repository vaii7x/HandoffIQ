export class Calculator {
  /**
   * Adds two numbers.
   * @param a The first number
   * @param b The second number
   * @returns The sum of a and b
   */
  public add(a: number, b: number): number {
    return a + b;
  }

  /**
   * Subtracts the second number from the first number.
   * @param a The first number (minuend)
   * @param b The second number (subtrahend)
   * @returns The difference between a and b
   */
  public subtract(a: number, b: number): number {
    return a - b;
  }

  /**
   * Multiplies two numbers.
   * @param a The first number
   * @param b The second number
   * @returns The product of a and b
   */
  public multiply(a: number, b: number): number {
    return a * b;
  }

  /**
   * Divides the first number by the second number.
   * @param a The numerator
   * @param b The denominator
   * @returns The quotient of a and b
   * @throws Error if b is zero
   */
  public divide(a: number, b: number): number {
    if (b === 0) {
      throw new Error("Division by zero is not allowed.");
    }
    return a / b;
  }
}
