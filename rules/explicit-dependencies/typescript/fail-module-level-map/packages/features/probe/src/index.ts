export const cache = new Map<string, number>();

export const remember = (key: string, value: number): void => {
  cache.set(key, value);
};
