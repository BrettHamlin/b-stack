import * as Schema from "effect/Schema";

export const PlayerId = Schema.String.pipe(Schema.brand("PlayerId"));
export type PlayerId = typeof PlayerId.Type;

export const greet = (id: PlayerId): string => `hello ${id}`;
export const greeting = greet("player-1");
