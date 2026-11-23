export const reach = (url: string): void => {
  const found: unknown = Reflect.get(globalThis, "fetch");
  if (typeof found === "function") Reflect.apply(found, undefined, [url]);
};
