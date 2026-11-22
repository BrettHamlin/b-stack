import { ipcRenderer } from "electron";

export const send = (): void => ipcRenderer.send("x");
