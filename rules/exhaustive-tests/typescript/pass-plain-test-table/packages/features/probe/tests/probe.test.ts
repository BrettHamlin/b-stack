import { expect, it } from "@effect/vitest";

import { probe } from "@app/probe";

it.each([1, 2])("doubles %i", (n) => {
  expect(probe(n)).toBe(n * 2);
});
