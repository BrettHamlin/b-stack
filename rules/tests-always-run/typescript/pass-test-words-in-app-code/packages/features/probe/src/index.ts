const options = { only: true, skip: false, prop: "name" };

export const probe = (): string => (options.only && !options.skip ? options.prop : "");
