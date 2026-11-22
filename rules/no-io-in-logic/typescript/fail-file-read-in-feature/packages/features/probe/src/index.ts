import * as NodeFs from "node:fs";

export const read = (path: string): string => NodeFs.readFileSync(path, "utf8");
