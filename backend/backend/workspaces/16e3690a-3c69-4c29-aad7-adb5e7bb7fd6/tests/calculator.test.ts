import { Calculator } from "../src/calculator";

describe("Calculator", () => {
  let calculator: Calculator;

  beforeEach(() => {
    calculator = new Calculator();
  });

  test("should add two numbers correctly", () => {
    expect(calculator.add(2, 3)).toBe(5);
    expect(calculator.add(-1, 1)).toBe(0);
    expect(calculator.add(0, 0)).toBe(0);
  });

  test("should subtract two numbers correctly", () => {
    expect(calculator.subtract(5, 3)).toBe(2);
    expect(calculator.subtract(3, 5)).toBe(-2);
    expect(calculator.subtract(0, 0)).toBe(0);
  });

  test("should multiply two numbers correctly", () => {
    expect(calculator.multiply(4, 3)).toBe(12);
    expect(calculator.multiply(-2, 3)).toBe(-6);
    expect(calculator.multiply(5, 0)).toBe(0);
  });

  test("should divide two numbers correctly", () => {
    expect(calculator.divide(6, 3)).toBe(2);
    expect(calculator.divide(5, 2)).toBe(2.5);
    expect(calculator.divide(-6, 3)).toBe(-2);
  });

  test("should throw an error when dividing by zero", () => {
    expect(() => calculator.divide(5, 0)).toThrow("Division by zero is not allowed.");
  });
});
