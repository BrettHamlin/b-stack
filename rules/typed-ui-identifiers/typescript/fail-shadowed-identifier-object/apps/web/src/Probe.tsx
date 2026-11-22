import { TallyUi as ProbeUi } from "@app/contracts";

export const Probe = () => {
  const make = (ProbeUi: { readonly status: string }) => <p data-testid={ProbeUi.status}>ready</p>;
  return make({ status: "probe-status" });
};
