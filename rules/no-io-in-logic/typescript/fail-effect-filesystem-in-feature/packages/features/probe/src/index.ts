import * as Effect from "effect/Effect";
import * as FileSystem from "effect/FileSystem";

export const read = (path: string) =>
  Effect.gen(function* () {
    const fs = yield* FileSystem.FileSystem;
    return yield* fs.readFileString(path);
  });
