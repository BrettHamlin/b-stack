import type { ItemName } from "@app/contracts";
import * as Brand from "effect/Brand";

export const forged: ItemName = Brand.nominal<ItemName>()("bad name!!");
