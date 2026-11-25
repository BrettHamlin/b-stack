import { expect, it } from "@effect/vitest";

import { greet } from "../src/index.ts";

it("greets by name", () => {
  expect(greet("Ada")).toEqual("Hello, Ada!");
});
