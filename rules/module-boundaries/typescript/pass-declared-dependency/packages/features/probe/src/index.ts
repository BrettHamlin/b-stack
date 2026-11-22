import { StorageFailed } from "@app/contracts";

export const failure = (): StorageFailed => new StorageFailed();
