"""Build the static website (landing page + app) for GitHub Pages: `python main.py site`.

The output folder needs no server. The app's Python API (support/api.py and the solver it uses)
is zipped into py.zip and runs in the browser with Pyodide (support/web/pyworker.js); the
benchmark numbers are precomputed into benchmarks.json.
"""
from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).parents[1]
WEB_DIR = Path(__file__).parent / "web"
# The modules support/api.py needs. benchmark/figures (numpy, matplotlib) and server (FastAPI) stay out.
PY_MODULES = ["__init__", "api", "csp", "explain", "generator", "propagation", "sat", "solver", "sudoku", "trace"]
MEDIA = {
    "demo.mp4": ROOT / "others" / "demo_video.mp4",
    "poster.jpg": ROOT / "others" / "demo_poster.jpg",
    "e1_nodes.png": ROOT / "data" / "results" / "e1_nodes.png",
    "e4_scale.png": ROOT / "data" / "results" / "e4_scale.png",
}


def build(out: Path) -> Path:
    from . import benchmark

    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(WEB_DIR, out)
    (out / "config.js").write_text('// Static build: the API runs in the browser (pyworker.js).\n'
                                   'window.LPX_BACKEND = "pyodide";\n', encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")  # serve files as they are

    (out / "media").mkdir()
    for name, source in MEDIA.items():
        shutil.copy2(source, out / "media" / name)

    with zipfile.ZipFile(out / "py.zip", "w", zipfile.ZIP_DEFLATED) as bundle:
        for module in PY_MODULES:
            bundle.write(ROOT / "support" / f"{module}.py", f"support/{module}.py")
        for path in sorted((ROOT / "data" / "sudoku").rglob("*")):
            if path.is_file():
                bundle.write(path, path.relative_to(ROOT).as_posix())

    (out / "benchmarks.json").write_text(json.dumps(benchmark.summary()), encoding="utf-8")
    return out
