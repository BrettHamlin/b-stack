// Runs in the renderer before the page, sandboxed: exposes the bridge and nothing else. A feature that needs the main
// process adds its calls to the bridge.
import { contextBridge } from "electron";

contextBridge.exposeInMainWorld("app", {});
