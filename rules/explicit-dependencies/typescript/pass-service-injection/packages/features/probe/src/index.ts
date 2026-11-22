import * as Context from "effect/Context";
import * as Effect from "effect/Effect";
import * as Layer from "effect/Layer";

export class Greeter extends Context.Service<Greeter, { readonly greet: Effect.Effect<string> }>()("@app/probe/Greeter") {}
export const hello = Effect.gen(function* () {
  const greeter = yield* Greeter;
  return yield* greeter.greet;
});
export const english = Layer.succeed(Greeter)({ greet: Effect.succeed("hello") });
export const greeting = hello.pipe(Effect.provide(english));
