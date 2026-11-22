// Runs in the renderer before the page, sandboxed: exposes the bridge and nothing else.
import type { SavedTally } from "@app/contracts";
import { TALLY_BRIDGE, TallyChannel, type TallyBridge } from "@app/contracts/ipc";
import { contextBridge, ipcRenderer } from "electron";

const bridge: TallyBridge = {
  load: async (): Promise<unknown> => {
    const loaded: unknown = await ipcRenderer.invoke(TallyChannel.load);
    return loaded;
  },
  save: async (tally: SavedTally): Promise<unknown> => {
    const saved: unknown = await ipcRenderer.invoke(TallyChannel.save, tally);
    return saved;
  },
};

contextBridge.exposeInMainWorld(TALLY_BRIDGE, bridge);
