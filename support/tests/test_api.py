"""The framework-free API that the static site runs in the browser (support/api.py), and the site build."""
import json
import zipfile

from support import api, site

EULER = "..3.2.6..9..3.5..1..18.64....81.29..7.......8..67.82....26.95..8..2.3..9..5.1.3.."


def call(method, url, body=None):
    out = json.loads(api.handle(method, url, json.dumps(body) if body is not None else None))
    return out["status"], out["body"]


def test_handle_serves_the_same_routes_as_the_server():
    assert call("GET", "/api/health") == (200, {"status": "ok", "version": api.VERSION})
    status, body = call("POST", "/api/solve", {"puzzle": EULER, "algorithm": "mac+", "explain": True})
    assert status == 200 and body["status"] == "solved" and body["explanation"]
    status, body = call("POST", "/api/race", {"puzzle": EULER, "algorithms": ["fc", "mac"]})
    assert status == 200 and len(body["results"]) == 2
    status, body = call("POST", "/api/generate", {"size": 4, "difficulty": "easy", "seed": 1})
    assert status == 200 and len(body["puzzle"]) == 16
    status, body = call("GET", "/api/puzzles?type=sudoku&difficulty=famous&limit=50")
    assert status == 200 and {p["id"] for p in body} >= {"inkala-2012"}


def test_handle_validates_like_the_server():
    assert call("POST", "/api/solve", {"puzzle": "not a sudoku"})[0] == 422
    assert call("POST", "/api/solve", {"puzzle": EULER, "algorithm": "magic"})[0] == 422
    assert call("POST", "/api/solve", {"puzzle": EULER, "timeout": 500})[0] == 422
    assert call("POST", "/api/solve", {"puzzle": "." * 2000})[0] == 422
    assert call("POST", "/api/race", {"puzzle": EULER, "algorithms": ["bt", "fc", "mrv", "lcv", "mac"]})[0] == 422
    assert call("POST", "/api/generate", {"size": 16})[0] == 422
    assert call("GET", "/api/nothing")[0] == 404


def test_site_build_has_everything_the_static_app_needs(tmp_path):
    out = site.build(tmp_path / "site")
    for name in ["index.html", "app.html", "pyworker.js", "benchmarks.json", ".nojekyll", "media/demo.mp4"]:
        assert (out / name).exists(), name
    assert '"pyodide"' in (out / "config.js").read_text()
    names = set(zipfile.ZipFile(out / "py.zip").namelist())
    assert {"support/api.py", "support/solver.py", "data/sudoku/famous.txt"} <= names
    assert "support/server.py" not in names and "support/benchmark.py" not in names
