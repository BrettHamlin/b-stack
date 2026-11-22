import * as Context from "effect/Context";
import type * as Effect from "effect/Effect";

export interface ClockShape {
  readonly now: Effect.Effect<number>;
}
export class WallClock extends Context.Service<WallClock, ClockShape>()("@app/probe/WallClock") {}
