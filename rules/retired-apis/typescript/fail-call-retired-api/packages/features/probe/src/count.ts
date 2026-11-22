/** @deprecated Use `countItems`, which skips blank names. */
export const sumAll = (names: ReadonlyArray<string>): number => names.length;

export const countItems = (names: ReadonlyArray<string>): number => names.filter((name) => name.trim() !== "").length;
