import { effect } from "@effect/vitest";
import * as Effect from "effect/Effect";

import { probe } from "@app/probe";

effect("probe", () => Effect.sync(probe));
