import * as NodeServices from "@effect/platform-node/NodeServices";
import { expect, it } from "@effect/vitest";
import * as Effect from "effect/Effect";
import * as ChildProcess from "effect/process/ChildProcess";
import { ChildProcessSpawner } from "effect/process/ChildProcessSpawner";

import { ready } from "../src/index.ts";

it.live("leaves a detached child process alive after its Effect scope exits", () =>
  Effect.gen(function* () {
    const spawner = yield* ChildProcessSpawner;
    const detach =
      "const { spawn } = require('node:child_process'); " +
      "spawn(process.execPath, ['-e', 'setTimeout(() => {}, 60000)'], { detached: true, stdio: 'ignore' }).unref();";
    const handle = yield* spawner.spawn(
      ChildProcess.make("node", ["-e", detach], {
        stdin: "ignore",
      }),
    );
    expect([ready, yield* handle.exitCode]).toEqual([true, 0]);
  }).pipe(Effect.scoped, Effect.provide(NodeServices.layer)));
