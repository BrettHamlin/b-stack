export const load = (url: string): unknown => Reflect.get(globalThis, "fetch")(url);
