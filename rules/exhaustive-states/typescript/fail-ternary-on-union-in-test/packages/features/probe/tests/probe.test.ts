import type { State } from "@app/probe";
import { expect, it } from "@effect/vitest";

const summary = (state: State): string => (state._tag === "Success" ? "done" : "other");

it("flags an app-owned Success tag in a ternary", () => {
  expect(summary({ _tag: "Success" })).toBe("done");
});
