// The renderer's composition root.
import { createRoot } from "react-dom/client";

import { GreetingView } from "./GreetingView.tsx";

const root = document.querySelector("#root");
if (root !== null) {
  createRoot(root).render(<GreetingView />);
}
