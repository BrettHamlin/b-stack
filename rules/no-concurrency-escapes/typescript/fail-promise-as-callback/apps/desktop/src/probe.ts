const save = async (): Promise<void> => {};

export const each = (items: ReadonlyArray<string>): void => {
  items.forEach(async () => {
    await save();
  });
};
