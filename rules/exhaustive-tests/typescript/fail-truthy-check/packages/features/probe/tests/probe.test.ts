import { expect, it } from "@effect/vitest";

import { probe } from "@app/probe";

it("probe", () => {
  expect(probe()).toBeTruthy();
});
