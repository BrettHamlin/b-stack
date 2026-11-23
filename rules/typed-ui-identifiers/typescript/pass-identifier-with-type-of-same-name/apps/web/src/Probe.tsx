import { TallyUi } from "@app/contracts";

type TallyUi = { readonly label: string };

export const label = { label: "ready" } as const satisfies TallyUi;

export function Probe() {
  return <p data-testid={TallyUi.error.value}>{label.label}</p>;
}
