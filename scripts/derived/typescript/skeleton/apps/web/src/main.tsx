// The renderer's composition root.
import { createRoot } from "react-dom/client";

const root = document.querySelector("#root");
if (root !== null) {
  createRoot(root).render(<main />);
}
