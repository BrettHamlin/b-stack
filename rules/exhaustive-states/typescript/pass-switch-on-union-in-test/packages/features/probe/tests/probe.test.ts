import type { Side } from "@app/probe";
import { expect, it } from "@effect/vitest";
import * as Option from "effect/Option";

const enemyOf = (side: Side): Side => {
  switch (side._tag) {
    case "Blue":
      return { _tag: "Red" };
    case "Red":
      return { _tag: "Blue" };
  }
};

it("switches over every union member, while plain strings and Option helpers stay allowed", () => {
  const seen: Array<string> = [];
  const start: Side = { _tag: "Blue" };
  if (start._tag === "Blue") seen.push("blue");
  const maybe = Option.some("ok");
  const unwrapped = Option.isSome(maybe) ? maybe.value : "empty";
  const label = unwrapped === "ok" ? "ready" : "waiting";
  expect([enemyOf(start), seen, label]).toEqual([{ _tag: "Red" }, ["blue"], "ready"]);
});
