import { formatCurrency } from "./format";

test("formats USD", () => {
  expect(formatCurrency(1234.5)).toBe("$1,234.50");
});
