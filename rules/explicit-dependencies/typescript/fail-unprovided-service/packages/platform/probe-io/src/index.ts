import { hello } from "@app/probe";
import * as Effect from "effect/Effect";

export const run = (): Promise<string> => Effect.runPromise(hello);
