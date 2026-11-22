import { double } from "@app/probe";
import { describe, expect, it } from "@effect/vitest";

describe.only("double", () => {
  it("doubles", () => {
    expect(double(2)).toBe(4);
  });
});
