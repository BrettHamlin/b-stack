import { double } from "@app/probe";
import { expect, it } from "@effect/vitest";

it("doubles", { skip: true }, () => {
  expect(double(2)).toBe(5);
});
