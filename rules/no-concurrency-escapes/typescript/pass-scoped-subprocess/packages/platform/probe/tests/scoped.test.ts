import * as NodeServices from "@effect/platform-node/NodeServices";
import { expect, it } from "@effect/vitest";
import * as Effect from "effect/Effect";
import * as ChildProcess from "effect/process/ChildProcess";
import { ChildProcessSpawner } from "effect/process/ChildProcessSpawner";

import { ready } from "../src/index.ts";

it.live("ends a scoped child process when its Effect scope closes", () =>
  Effect.gen(function* () {
    const pid = yield* Effect.scoped(
      Effect.gen(function* () {
        const spawner = yield* ChildProcessSpawner;
        const handle = yield* spawner.spawn(ChildProcess.make("/bin/sleep", ["60"], { stdin: "ignore" }));
        return handle.pid;
      }),
    );
    expect([ready, pid > 0]).toEqual([true, true]);
  }).pipe(Effect.provide(NodeServices.layer)));
