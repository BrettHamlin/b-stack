import { brand } from "effect/Schema";
import * as Schema from "effect/Schema";

export const LooseName = Schema.String.pipe(brand("ItemName"));
