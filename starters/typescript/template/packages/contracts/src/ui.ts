// Identifiers the renderer puts on elements and journeys find them by. A UiId is a distinct type, so a journey can't
// pass a raw string, and only contracts make one (lint: bstack/typed-ui-identifiers).
import * as Brand from "effect/Brand";

export type UiId = string & Brand.Brand<"UiId">;

export const uiId = Brand.nominal<UiId>();
