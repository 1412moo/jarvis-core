"""Local HTTP server for Jarvis Studyroom v0.1 Foundation."""

from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from urllib.parse import unquote, urlparse

APP_ROOT = Path(__file__).resolve().parent
WEB_DIR = APP_ROOT / "web"
CONTENT_DIR = APP_ROOT / "content"

MIME_TYPES: dict[str, str] = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".ico": "image/x-icon",
}


def resolve_safe_path(url_path: str) -> tuple[Path | None, int]:
    """Resolve a URL path safely within WEB_DIR or CONTENT_DIR.

    Returns (Path, 200) if safe and found, (None, 403) on traversal, or (None, 404) if not found.
    """
    clean_path = unquote(url_path.split("?", 1)[0].split("#", 1)[0])

    if clean_path in ("", "/"):
        target = (WEB_DIR / "index.html").resolve()
        return (target, 200) if target.is_file() else (None, 404)

    # Route /content/*.json and /api/content/*.json
    if clean_path.startswith("/api/content/"):
        rel_sub = clean_path.removeprefix("/api/content/")
        target = (CONTENT_DIR / rel_sub).resolve()
        base_dir = CONTENT_DIR
    elif clean_path.startswith("/content/"):
        rel_sub = clean_path.removeprefix("/content/")
        target = (CONTENT_DIR / rel_sub).resolve()
        base_dir = CONTENT_DIR
    else:
        # Default to web directory
        rel_sub = clean_path.lstrip("/")
        target = (WEB_DIR / rel_sub).resolve()
        base_dir = WEB_DIR

    # Path traversal check
    try:
        target.relative_to(base_dir)
    except ValueError:
        return None, 403

    if target.is_file():
        return target, 200
    return None, 404


class StudyroomHandler(BaseHTTPRequestHandler):
    server_version = "JarvisStudyroom/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        target_file, status_code = resolve_safe_path(parsed.path)

        if status_code == 403:
            self.send_error(HTTPStatus.FORBIDDEN, "Forbidden: Path traversal is blocked")
            return
        if status_code == 404 or target_file is None:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        suffix = target_file.suffix.lower()
        content_type = MIME_TYPES.get(suffix, "application/octet-stream")

        try:
            content_bytes = target_file.read_bytes()
        except OSError as err:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"Read error: {err}")
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content_bytes)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(content_bytes)

    def log_message(self, format: str, *args: object) -> None:
        # Suppress noisy default logging
        sys.stderr.write(f"[Studyroom] {self.address_string()} - {format % args}\n")


def create_server(host: str = "127.0.0.1", port: int = 8080) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), StudyroomHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Jarvis Studyroom web server")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port number (default: 8080)")
    args = parser.parse_args()

    server = create_server(host=args.host, port=args.port)
    print(f"[Studyroom] Server running at http://{args.host}:{args.port}/")
    print("[Studyroom] Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Studyroom] Server stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
