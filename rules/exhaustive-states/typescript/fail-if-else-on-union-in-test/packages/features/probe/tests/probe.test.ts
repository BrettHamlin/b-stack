import type { Side } from "@app/probe";
import { expect, it } from "@effect/vitest";

const enemyOf = (side: Side): Side => {
  if (side._tag === "Blue") {
    return { _tag: "Red" };
  } else {
    return { _tag: "Blue" };
  }
};

it("picks the opposing side", () => {
  expect(enemyOf({ _tag: "Blue" })).toEqual({ _tag: "Red" });
});
