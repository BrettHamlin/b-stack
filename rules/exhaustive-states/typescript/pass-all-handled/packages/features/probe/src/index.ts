export type Light = { readonly _tag: "Red" } | { readonly _tag: "Amber" } | { readonly _tag: "Green" };

export const wait = (light: Light): number => {
  switch (light._tag) {
    case "Red":
      return 30;
    case "Amber":
      return 5;
    case "Green":
      return 0;
  }
};
