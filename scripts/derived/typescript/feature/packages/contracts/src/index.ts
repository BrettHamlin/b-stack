import { uiId } from "./ui.ts";

export type { UiId } from "./ui.ts";

/** Element identifiers shared by the renderer and the journeys. */
export const GreetingUi = {
  name: uiId("greeting-name"),
  greet: uiId("greeting-greet"),
  shown: uiId("greeting-shown"),
} as const;
