import * as NodeFs from "node:fs";

export const read = (): string => NodeFs.readFileSync("x", "utf8");
