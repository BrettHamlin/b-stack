import { TallyUi, type Tally } from "@app/contracts";
import { entries, parseItemName, record, type TallyStore } from "@app/tally";
import * as Effect from "effect/Effect";
import type * as Layer from "effect/Layer";
import { useState } from "react";

export interface TallyViewProps {
  readonly initial: Tally;
  readonly store: Layer.Layer<TallyStore>;
}

export function TallyView({ initial, store }: TallyViewProps) {
  const [tally, setTally] = useState(initial);
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  const add = () => {
    Effect.runFork(
      parseItemName(name).pipe(
        Effect.flatMap(record),
        Effect.match({
          onFailure: (failure) => setError(failure.message),
          onSuccess: (next) => {
            setTally(next);
            setError("");
            setName("");
          },
        }),
        Effect.provide(store),
      ),
    );
  };

  const items = entries(tally);
  return (
    <main>
      <input data-testid={TallyUi.name} value={name} onChange={(event) => setName(event.target.value)} aria-label="Item name" />
      <button type="button" data-testid={TallyUi.add} onClick={add}>
        Add
      </button>
      <p data-testid={TallyUi.error} role="alert">
        {error}
      </p>
      <ul data-testid={TallyUi.items}>
        {items.length === 0 ? <li>(empty)</li> : items.map(([item, count]) => <li key={item}>{`${item} ${count}`}</li>)}
      </ul>
    </main>
  );
}
