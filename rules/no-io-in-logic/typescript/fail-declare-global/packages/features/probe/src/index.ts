declare global {
  const process: { readonly env: Record<string, string> };
}

export const home = (): string | undefined => process.env["HOME"];
