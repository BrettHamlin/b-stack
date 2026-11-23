import type { ItemName } from "@app/contracts";

export class Caster {
  cast(value: unknown): ItemName;
  cast(value: unknown): unknown {
    return value;
  }
}
