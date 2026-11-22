import { expect, it } from "@effect/vitest";

import { probe } from "@app/probe";

it("probe", () => {
  expect(probe()).toEqual(expect.objectContaining({ a: 1 }));
});
