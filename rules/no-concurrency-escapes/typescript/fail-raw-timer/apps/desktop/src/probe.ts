export const later = (run: () => void): void => {
  setTimeout(run, 100);
};
