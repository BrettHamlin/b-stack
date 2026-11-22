const ProbeUi = { status: "probe-status" };

export function Probe() {
  return <p data-testid={ProbeUi.status}>ready</p>;
}
