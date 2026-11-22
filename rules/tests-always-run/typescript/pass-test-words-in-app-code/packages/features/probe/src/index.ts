export const probe = (): string => {
  const options = { only: true, skip: false, prop: "name" };
  return options.only && !options.skip ? options.prop : "";
};
