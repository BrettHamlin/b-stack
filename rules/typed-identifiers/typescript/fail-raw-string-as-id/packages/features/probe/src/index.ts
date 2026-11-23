import type { ItemName } from "@app/contracts";

export const greet = (id: ItemName): string => `hello ${id}`;
export const greeting = greet("player-1");
