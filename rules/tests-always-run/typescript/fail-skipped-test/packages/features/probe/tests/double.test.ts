import { double } from "@app/probe";
import { expect, it } from "@effect/vitest";

it.skip("doubles", () => {
  expect(double(2)).toBe(4);
});
