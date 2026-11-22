import { ItemName } from "@app/contracts";
import * as Effect from "effect/Effect";
import * as Schema from "effect/Schema";

const decodeId = Schema.decodeUnknownEffect(ItemName);

export const greet = (id: ItemName): string => `hello ${id}`;
export const greeting = decodeId("player-1").pipe(Effect.map(greet));
