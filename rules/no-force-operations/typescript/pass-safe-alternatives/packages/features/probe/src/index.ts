import * as Option from "effect/Option";
import * as Schema from "effect/Schema";

const Point = Schema.Struct({ x: Schema.Number });
const decodePoint = Schema.decodeUnknownOption(Point);

export const first = (items: ReadonlyArray<string>): Option.Option<string> => Option.fromNullishOr(items[0]);
export const point = (value: unknown): Option.Option<{ readonly x: number }> => decodePoint(value);
export const name = { kind: "probe" } as const;
