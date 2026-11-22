import { TallyUi } from "@app/contracts";

type TallyUi = { readonly label: string };

export const label: TallyUi = { label: "ready" };

export function Probe() {
  return <p data-testid={TallyUi.error}>{label.label}</p>;
}
