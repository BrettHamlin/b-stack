import * as Context from "effect/Context";
import * as Effect from "effect/Effect";

export class Greeter extends Context.Service<Greeter, { readonly greet: Effect.Effect<string> }>()("@app/probe/Greeter") {}
export const hello = Effect.gen(function* () {
  const greeter = yield* Greeter;
  return yield* greeter.greet;
});
