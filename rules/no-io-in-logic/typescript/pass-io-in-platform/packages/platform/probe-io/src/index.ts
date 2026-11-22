import { WallClock } from "@app/probe";
import * as Effect from "effect/Effect";
import * as Layer from "effect/Layer";
import * as FileSystem from "effect/FileSystem";

export const wallClock = Layer.succeed(WallClock)({ now: Effect.sync(() => performance.now()) });
export const exists = Effect.fn("exists")(function* (path: string) {
  const fs = yield* FileSystem.FileSystem;
  return yield* fs.exists(path);
});
