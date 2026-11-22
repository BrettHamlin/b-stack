import * as Schema from "effect/Schema";

export const PlayerId = Schema.String.pipe(Schema.brand("PlayerId"));
export type PlayerId = typeof PlayerId.Type;
import * as Effect from "effect/Effect";

const decodeId = Schema.decodeUnknownEffect(PlayerId);

export const greet = (id: PlayerId): string => `hello ${id}`;
export const greeting = decodeId("player-1").pipe(Effect.map(greet));
