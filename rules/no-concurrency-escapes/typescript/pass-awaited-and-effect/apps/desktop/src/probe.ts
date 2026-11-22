import * as Effect from "effect/Effect";

const save = async (): Promise<void> => {};

export const onClick = async (): Promise<void> => {
  await save();
};
export const later = (run: () => void): Effect.Effect<void> => Effect.sleep("100 millis").pipe(Effect.andThen(Effect.sync(run)));
