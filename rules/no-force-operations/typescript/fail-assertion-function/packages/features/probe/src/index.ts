import type { ItemName } from "@app/contracts";

export function assertName(value: unknown): asserts value is ItemName {
  if (value === undefined) throw new Error("missing");
}
