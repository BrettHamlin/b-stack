import { expect, it } from "@effect/vitest";

import { probe } from "@app/probe";

it("probe", () => {
  expect(probe()).toEqual({ a: 1, b: 2 });
});
