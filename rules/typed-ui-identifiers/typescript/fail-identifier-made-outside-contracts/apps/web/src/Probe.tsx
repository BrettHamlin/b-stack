import { uiId } from "@app/contracts";

const status = uiId("probe-status");

export function Probe() {
  return <p data-testid={status}>ready</p>;
}
