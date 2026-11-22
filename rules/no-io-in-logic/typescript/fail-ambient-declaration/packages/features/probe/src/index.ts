declare const fetch: (url: string) => Promise<unknown>;

export const load = (url: string): Promise<unknown> => fetch(url);
