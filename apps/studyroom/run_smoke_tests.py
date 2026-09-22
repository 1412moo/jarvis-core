"""Deterministic smoke tests for Jarvis Studyroom v0.1 Foundation."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.request import urlopen

APP_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_ROOT))

from run_web_app import CONTENT_DIR, WEB_DIR, create_server, resolve_safe_path

REQUIRED_FILES = [
    APP_ROOT / "README.md",
    APP_ROOT / "run_web_app.py",
    APP_ROOT / "run_smoke_tests.py",
    WEB_DIR / "index.html",
    WEB_DIR / "styles.css",
    WEB_DIR / "app.js",
    CONTENT_DIR / "recordroom.json",
    CONTENT_DIR / "technologies.json",
    CONTENT_DIR / "features.json",
    CONTENT_DIR / "glossary.json",
    CONTENT_DIR / "learn.json",
]


def test_files_exist() -> None:
    print("[1/5] Checking required files existence...")
    for file_path in REQUIRED_FILES:
        assert file_path.is_file(), f"Missing required file: {file_path}"
        assert file_path.stat().st_size > 0, f"File is empty: {file_path}"
    print("  -> All 11 required files exist and are non-empty.")


def test_json_schemas() -> None:
    print("[2/5] Validating JSON schema and contents...")
    
    # 1. recordroom.json
    records = json.loads((CONTENT_DIR / "recordroom.json").read_text(encoding="utf-8"))
    assert isinstance(records, list) and len(records) > 0, "recordroom.json must be a non-empty list"
    for r in records:
        for k in ("id", "title", "task_id", "what_happened", "why_needed", "issue_faced", "resolution", "engineering_lesson"):
            assert k in r, f"recordroom item missing key: {k}"

    # 2. technologies.json
    techs = json.loads((CONTENT_DIR / "technologies.json").read_text(encoding="utf-8"))
    assert isinstance(techs, list) and len(techs) > 0, "technologies.json must be a non-empty list"
    for t in techs:
        for k in ("id", "name", "description", "jarvis_usage"):
            assert k in t, f"technologies item missing key: {k}"

    # 3. features.json
    features = json.loads((CONTENT_DIR / "features.json").read_text(encoding="utf-8"))
    assert isinstance(features, list) and len(features) > 0, "features.json must be a non-empty list"
    for f in features:
        for k in ("id", "name", "what", "why", "how"):
            assert k in f, f"features item missing key: {k}"

    # 4. glossary.json
    glossary = json.loads((CONTENT_DIR / "glossary.json").read_text(encoding="utf-8"))
    assert isinstance(glossary, list) and len(glossary) > 0, "glossary.json must be a non-empty list"
    for g in glossary:
        for k in ("id", "term", "dev_definition", "simple_explanation", "jarvis_example"):
            assert k in g, f"glossary item missing key: {k}"

    # 5. learn.json
    learn = json.loads((CONTENT_DIR / "learn.json").read_text(encoding="utf-8"))
    assert isinstance(learn, list) and len(learn) > 0, "learn.json must be a non-empty list"
    for l in learn:
        for k in ("id", "title", "developer_explanation", "beginner_explanation", "jarvis_example", "quiz"):
            assert k in l, f"learn item missing key: {k}"
        assert isinstance(l["quiz"], list) and len(l["quiz"]) > 0, "quiz must be a non-empty list"
        for q in l["quiz"]:
            assert "question" in q and "options" in q and "answer" in q, "quiz item missing fields"

    print("  -> All 5 JSON files parsed and schema structure validated.")


def test_path_traversal_defense() -> None:
    print("[3/5] Testing path traversal defense logic...")
    
    # Safe paths
    p, code = resolve_safe_path("/")
    assert code == 200 and p == WEB_DIR / "index.html", f"Expected / to resolve index.html, got {p}, {code}"
    
    p, code = resolve_safe_path("/styles.css")
    assert code == 200 and p == WEB_DIR / "styles.css"

    p, code = resolve_safe_path("/content/glossary.json")
    assert code == 200 and p == CONTENT_DIR / "glossary.json"

    # Traversal attempts
    p, code = resolve_safe_path("/../README.md")
    assert code in (403, 404), f"Expected traversal to be blocked, got {code}"

    p, code = resolve_safe_path("/content/../../AGENTS.md")
    assert code == 403, f"Expected 403 for /content/../../AGENTS.md, got {code}"

    p, code = resolve_safe_path("/api/content/../../run_web_app.py")
    assert code == 403, f"Expected 403 for traversal, got {code}"

    print("  -> Path traversal defense verified.")


def test_web_app_http_server() -> None:
    print("[4/5] Testing live HTTP server responses...")
    
    # Bind to localhost with OS-selected free port (0)
    server = create_server(host="127.0.0.1", port=0)
    actual_port = server.server_address[1]
    
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.1)

    base_url = f"http://127.0.0.1:{actual_port}"
    try:
        # 1. GET /
        with urlopen(f"{base_url}/") as res:
            assert res.status == 200
            body = res.read().decode("utf-8")
            assert "Jarvis Studyroom" in body
            assert "app.js" in body

        # 2. GET /styles.css
        with urlopen(f"{base_url}/styles.css") as res:
            assert res.status == 200
            assert "text/css" in res.headers.get("Content-Type", "")

        # 3. GET /app.js
        with urlopen(f"{base_url}/app.js") as res:
            assert res.status == 200
            assert "javascript" in res.headers.get("Content-Type", "")

        # 4. GET /content/glossary.json
        with urlopen(f"{base_url}/content/glossary.json") as res:
            assert res.status == 200
            data = json.loads(res.read().decode("utf-8"))
            assert len(data) > 0

        # 5. Traversal attempt via HTTP -> must yield 403
        try:
            urlopen(f"{base_url}/content/../../AGENTS.md")
            assert False, "Expected HTTP 403 Forbidden for traversal attempt"
        except HTTPError as err:
            assert err.code == 403, f"Expected 403, got {err.code}"

    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=1.0)

    print(f"  -> Server tested on port {actual_port}: all endpoints responded correctly.")


def test_isolation_no_external_dependencies() -> None:
    print("[5/5] Testing isolation & zero-dependency rule...")
    
    # Ensure run_web_app imports ONLY stdlib modules
    web_app_code = (APP_ROOT / "run_web_app.py").read_text(encoding="utf-8")
    forbidden_terms = ["flask", "django", "fastapi", "requests", "express", "marked", "prism"]
    for term in forbidden_terms:
        assert term not in web_app_code.lower(), f"Forbidden dependency detected in run_web_app.py: {term}"

    print("  -> Zero external dependencies confirmed.")


def run_all() -> None:
    print("=" * 60)
    print("Starting Jarvis Studyroom v0.1 Smoke Tests")
    print("=" * 60)
    test_files_exist()
    test_json_schemas()
    test_path_traversal_defense()
    test_web_app_http_server()
    test_isolation_no_external_dependencies()
    print("=" * 60)
    print("ALL SMOKE TESTS PASSED (5/5 suites, 0 failures)")
    print("=" * 60)


if __name__ == "__main__":
    run_all()
