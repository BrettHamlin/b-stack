import { expect, it } from "@effect/vitest";
import * as Effect from "effect/Effect";

import { probe } from "@app/probe";

it.effect.each([1, 2])("doubles %i", (n) => Effect.sync(() => expect(probe(n)).toBe(n * 2)));
