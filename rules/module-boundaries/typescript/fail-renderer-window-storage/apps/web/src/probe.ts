export const keep = (value: string): void => {
  window.localStorage.setItem("probe", value);
};
