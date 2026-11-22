import { it } from "@effect/vitest";
import * as Effect from "effect/Effect";

import { probe } from "@app/probe";

it.effect("probe", () => Effect.sync(probe));
