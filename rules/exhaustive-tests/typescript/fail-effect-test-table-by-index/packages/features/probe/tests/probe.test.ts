import { it } from "@effect/vitest";
import * as Effect from "effect/Effect";

it["effect"].each([1, 2])("doubles %i", () => Effect.void);
