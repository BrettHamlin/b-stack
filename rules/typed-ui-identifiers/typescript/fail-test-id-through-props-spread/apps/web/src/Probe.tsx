export function Probe(props: { readonly id: string }) {
  const extra = { "data-testid": props.id };
  return <p {...extra}>ready</p>;
}
