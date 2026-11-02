// Where the JSON API runs. "server": the FastAPI server (python main.py) answers /api/*.
// The static build (python main.py site) replaces this file with "pyodide", which runs the
// same Python code in the browser (pyworker.js), so the site needs no backend.
window.LPX_BACKEND = "server";
