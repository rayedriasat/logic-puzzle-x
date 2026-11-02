// Runs the solver's Python code (support/api.py) in the browser with Pyodide, so a static host
// like GitHub Pages can serve the whole app. Only the static build (python main.py site) uses it.
// Messages in: {id, method, url, body}. Messages out: {id, status, body} or {id, status: 0, error}.
import { loadPyodide } from "https://cdn.jsdelivr.net/npm/pyodide@314.0.7/pyodide.mjs";

const ROOT = "/home/pyodide/lpx";

const ready = (async () => {
  const pyodide = await loadPyodide();
  const bundle = await fetch(new URL("py.zip", self.location.href));
  if (!bundle.ok) throw new Error(`Could not load py.zip (${bundle.status})`);
  pyodide.unpackArchive(await bundle.arrayBuffer(), "zip", { extractDir: ROOT });
  pyodide.runPython(`import sys; sys.path.insert(0, "${ROOT}")`);
  return pyodide.pyimport("support.api");
})();

self.onmessage = async ({ data: { id, method, url, body } }) => {
  try {
    const api = await ready;
    const { status, body: out } = JSON.parse(api.handle(method, url, body ?? null));
    self.postMessage({ id, status, body: out });
  } catch (error) {
    self.postMessage({ id, status: 0, error: String(error?.message ?? error) });
  }
};
