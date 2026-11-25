import { GreetingUi } from "@app/contracts";
import { greet } from "@app/greeting";
import { useState } from "react";

export function GreetingView() {
  const [name, setName] = useState("");
  const [shown, setShown] = useState("");
  return (
    <main>
      <input
        data-testid={GreetingUi.name.value}
        value={name}
        onChange={(event) => setName(event.target.value)}
        aria-label="Name"
      />
      <button type="button" data-testid={GreetingUi.greet.value} onClick={() => setShown(greet(name))}>
        Greet
      </button>
      <ul data-testid={GreetingUi.shown.value}>
        <li>{shown}</li>
      </ul>
    </main>
  );
}
