"""Local read-only dashboard for jarvis-core task markdown files."""

from __future__ import annotations

import argparse
import html
import re
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


REPO_ROOT = Path(__file__).resolve().parents[2]
TASKS_DIR = REPO_ROOT / "memory" / "tasks"

TASK_ID_PATTERN = re.compile(r"^task-\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*$")
TASK_META_LINE_PATTERN = re.compile(r"^- ([a-z_]+): `(.*)`$")
TASK_REQUIRED_FIELDS = ("id", "title", "status", "repo", "created_at", "updated_at", "summary")
TASK_EXECUTION_FIELDS = (
    "executed",
    "success",
    "dry_run",
    "mode",
    "reason",
    "message",
    "execution_status",
    "execution_updated_at",
    "execution_summary",
)
DETAIL_MONO_FIELDS = ("id", "repo", "created_at", "updated_at", "execution_updated_at")
STATUS_ORDER = ("TODO", "DOING", "BLOCKED", "DONE", "FAILED", "NEEDS_APPROVAL")
STATUS_BADGE_CLASSES = {
    "TODO": "badge-todo",
    "DOING": "badge-doing",
    "BLOCKED": "badge-blocked",
    "DONE": "badge-done",
    "FAILED": "badge-failed",
    "NEEDS_APPROVAL": "badge-needs-approval",
}
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost"})


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _parse_updated_at(value: str) -> tuple[int, str]:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M UTC")
        return int(parsed.timestamp()), value
    except ValueError:
        return 0, value


def _read_task_file(task_file: Path) -> dict[str, str] | None:
    metadata: dict[str, str] = {}
    try:
        lines = task_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    for raw_line in lines:
        matched = TASK_META_LINE_PATTERN.match(raw_line.strip())
        if not matched:
            continue
        key, value = matched.groups()
        metadata[key] = value.strip()

    if any(not metadata.get(field) for field in TASK_REQUIRED_FIELDS):
        return None
    if not TASK_ID_PATTERN.fullmatch(metadata["id"]):
        return None

    metadata["file_name"] = task_file.name
    return metadata


def _load_tasks() -> list[dict[str, str]]:
    if not TASKS_DIR.exists() or not TASKS_DIR.is_dir():
        return []

    tasks: list[dict[str, str]] = []
    for task_file in sorted(TASKS_DIR.glob("*.md")):
        metadata = _read_task_file(task_file)
        if metadata is not None:
            tasks.append(metadata)

    return sorted(tasks, key=lambda task: _parse_updated_at(task["updated_at"]), reverse=True)


def _status_counts(tasks: list[dict[str, str]]) -> dict[str, int]:
    counts = {status: 0 for status in STATUS_ORDER}
    for task in tasks:
        status = task.get("status", "")
        if status in counts:
            counts[status] += 1
    return counts


def _status_badge(status: str) -> str:
    badge_class = STATUS_BADGE_CLASSES.get(status)
    class_value = "badge" if badge_class is None else f"badge {badge_class}"
    return f'<span class="{class_value}">{_escape(status)}</span>'


def _render_layout(title: str, body: str, auto_refresh: bool = False) -> str:
    refresh_meta = '  <meta http-equiv="refresh" content="30">\n' if auto_refresh else ""
    footer_text = "Localhost read-only dashboard"
    if auto_refresh:
        footer_text = f"{footer_text} · Auto refresh: 30s"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
{refresh_meta}  <title>{_escape(title)}</title>
  <style>
    :root {{ color-scheme: light; }}
    body {{
      margin: 0;
      background: #f6f7f9;
      color: #17202a;
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.5;
    }}
    main {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 24px;
    }}
    header {{
      margin-bottom: 20px;
    }}
    h1 {{
      margin: 0 0 4px;
      font-size: 28px;
    }}
    h2 {{
      margin: 28px 0 12px;
      font-size: 18px;
    }}
    a {{
      color: #185abc;
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    .nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }}
    .nav a {{
      background: #fff;
      border: 1px solid #d8dee6;
      border-radius: 999px;
      color: #344054;
      font-size: 13px;
      font-weight: 700;
      padding: 4px 10px;
    }}
    .nav a.active {{
      background: #17202a;
      border-color: #17202a;
      color: #fff;
    }}
    .muted {{
      color: #667085;
    }}
    .counts {{
      display: grid;
      gap: 8px;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      margin: 16px 0 24px;
    }}
    .count {{
      background: #fff;
      border: 1px solid #d8dee6;
      border-radius: 6px;
      padding: 12px;
    }}
    .count strong {{
      display: block;
      font-size: 22px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #fff;
      border: 1px solid #d8dee6;
      border-radius: 6px;
      overflow: hidden;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid #e7ebf0;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #eef2f6;
      font-size: 13px;
      color: #344054;
    }}
    tr:last-child td {{
      border-bottom: 0;
    }}
    .summary {{
      max-width: 540px;
    }}
    .detail {{
      background: #fff;
      border: 1px solid #d8dee6;
      border-radius: 6px;
      padding: 20px;
    }}
    dl {{
      display: grid;
      grid-template-columns: 180px 1fr;
      gap: 12px 18px;
      margin: 0;
    }}
    dt {{
      color: #667085;
      font-weight: 700;
    }}
    dd {{
      margin: 0;
      word-break: break-word;
    }}
    .detail-summary {{
      background: #f8fafc;
      border: 1px solid #e7ebf0;
      border-radius: 6px;
      padding: 10px 12px;
      white-space: pre-wrap;
    }}
    .mono {{
      color: #344054;
      font-family: Consolas, "Liberation Mono", Menlo, monospace;
      font-size: 13px;
    }}
    .badge {{
      display: inline-block;
      border: 1px solid #ccd4df;
      border-radius: 999px;
      padding: 2px 8px;
      background: #f8fafc;
      color: #344054;
      font-size: 12px;
      font-weight: 700;
    }}
    .badge-todo {{
      background: #f2f4f7;
      border-color: #d0d5dd;
      color: #344054;
    }}
    .badge-doing {{
      background: #eff6ff;
      border-color: #bfdbfe;
      color: #1d4ed8;
    }}
    .badge-blocked {{
      background: #fffbeb;
      border-color: #fde68a;
      color: #92400e;
    }}
    .badge-done {{
      background: #ecfdf3;
      border-color: #bbf7d0;
      color: #166534;
    }}
    .badge-failed {{
      background: #fef2f2;
      border-color: #fecaca;
      color: #991b1b;
    }}
    .badge-needs-approval {{
      background: #ecfeff;
      border-color: #a5f3fc;
      color: #155e75;
    }}
    .footer {{
      border-top: 1px solid #d8dee6;
      color: #667085;
      font-size: 13px;
      margin-top: 32px;
      padding-top: 16px;
    }}
  </style>
</head>
<body>
  <main>{body}<footer class="footer">{_escape(footer_text)}</footer></main>
</body>
</html>"""


def _render_nav(active_status: str | None = None) -> str:
    links = (
        ("All Tasks", "/tasks", None),
        ("DONE", "/tasks?status=DONE", "DONE"),
        ("DOING", "/tasks?status=DOING", "DOING"),
        ("FAILED", "/tasks?status=FAILED", "FAILED"),
        ("BLOCKED", "/tasks?status=BLOCKED", "BLOCKED"),
    )
    items = []
    for label, href, link_status in links:
        active_class = ' class="active"' if active_status == link_status else ""
        items.append(f'<a{active_class} href="{_escape(href)}">{_escape(label)}</a>')
    return f'<nav class="nav">{"".join(items)}</nav>'


def _render_counts(counts: dict[str, int]) -> str:
    items = []
    for status in STATUS_ORDER:
        items.append(
            f'<div class="count"><span class="muted">{_escape(status)}</span><strong>{counts.get(status, 0)}</strong></div>'
        )
    return f'<section class="counts">{"".join(items)}</section>'


def _render_task_rows(tasks: list[dict[str, str]]) -> str:
    if not tasks:
        return '<p class="muted">No task files found.</p>'

    rows = []
    for task in tasks:
        task_id = task["id"]
        rows.append(
            "<tr>"
            f'<td><a href="/tasks/{_escape(task_id)}">{_escape(task_id)}</a></td>'
            f"<td>{_escape(task['title'])}</td>"
            f"<td>{_status_badge(task['status'])}</td>"
            f"<td>{_escape(task['updated_at'])}</td>"
            f'<td class="summary">{_escape(task["summary"])}</td>'
            "</tr>"
        )
    return (
        "<table>"
        "<thead><tr><th>ID</th><th>Title</th><th>Status</th><th>Updated</th><th>Summary</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
    )


def _render_index(status_filter: str | None = None) -> str:
    tasks = _load_tasks()
    counts = _status_counts(tasks)
    visible_tasks = tasks
    filter_note = ""
    if status_filter is not None:
        visible_tasks = [task for task in tasks if task["status"] == status_filter]
        filter_note = f'<p class="muted">Filtered by status: {_escape(status_filter)}</p>'

    body = (
        "<header>"
        "<h1>Jarvis Tasks</h1>"
        f'<p class="muted">Read-only view of {_escape(TASKS_DIR.relative_to(REPO_ROOT))}</p>'
        f"{_render_nav(status_filter)}"
        "</header>"
        "<h2>Status counts</h2>"
        f"{_render_counts(counts)}"
        "<h2>Recently updated tasks</h2>"
        f"{filter_note}"
        f"{_render_task_rows(visible_tasks)}"
    )
    return _render_layout("Jarvis Tasks", body, auto_refresh=True)


def _task_by_id(task_id: str) -> dict[str, str] | None:
    if not TASK_ID_PATTERN.fullmatch(task_id):
        return None
    for task in _load_tasks():
        if task["id"] == task_id:
            return task
    return None


def _render_detail_fields(task: dict[str, str], fields: tuple[str, ...]) -> str:
    rows = []
    for field in fields:
        value = task.get(field)
        if value:
            if field == "status":
                rendered_value = _status_badge(value)
            elif field == "summary":
                rendered_value = f'<div class="detail-summary">{_escape(value)}</div>'
            elif field in DETAIL_MONO_FIELDS:
                rendered_value = f'<span class="mono">{_escape(value)}</span>'
            else:
                rendered_value = _escape(value)
            rows.append(f"<dt>{_escape(field)}</dt><dd>{rendered_value}</dd>")
    return f"<dl>{''.join(rows)}</dl>"


def _render_task_detail(task_id: str) -> tuple[HTTPStatus, str]:
    task = _task_by_id(task_id)
    if task is None:
        body = (
            "<header>"
            "<h1>Task not found</h1>"
            '<p><a href="/tasks">Back to task list</a></p>'
            "</header>"
            f"<p>No readable task exists for <code>{_escape(task_id)}</code>.</p>"
        )
        return HTTPStatus.NOT_FOUND, _render_layout("Task not found", body)

    execution_fields = tuple(field for field in TASK_EXECUTION_FIELDS if task.get(field))
    execution_section = ""
    if execution_fields:
        execution_section = "<h2>Execution metadata</h2>" + _render_detail_fields(task, execution_fields)

    body = (
        "<header>"
        f"<h1>{_escape(task['title'])}</h1>"
        f"{_render_nav('')}"
        '<p><a href="/tasks">Back to task list</a></p>'
        "</header>"
        '<section class="detail">'
        f"{_render_detail_fields(task, TASK_REQUIRED_FIELDS)}"
        f"{execution_section}"
        "</section>"
    )
    return HTTPStatus.OK, _render_layout(task["title"], body)


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "JarvisDashboard/0.1"

    def _send_html(self, status: HTTPStatus, body: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        if path == "/":
            self._send_html(HTTPStatus.OK, _render_index())
            return

        if path == "/tasks":
            query = parse_qs(parsed_url.query, keep_blank_values=True)
            status_filter = None
            if "status" in query:
                status_values = query["status"]
                if len(status_values) != 1 or status_values[0] not in STATUS_ORDER:
                    body = _render_layout("Bad Request", "<h1>Bad Request</h1><p>Invalid status filter.</p>")
                    self._send_html(HTTPStatus.BAD_REQUEST, body)
                    return
                status_filter = status_values[0]

            self._send_html(HTTPStatus.OK, _render_index(status_filter))
            return

        if path.startswith("/tasks/"):
            task_id = unquote(path.removeprefix("/tasks/")).strip("/")
            status, body = _render_task_detail(task_id)
            self._send_html(status, body)
            return

        self._send_html(HTTPStatus.NOT_FOUND, _render_layout("Not Found", "<h1>Not Found</h1>"))

    def do_HEAD(self) -> None:
        self._send_method_not_allowed()

    def do_POST(self) -> None:
        self._send_method_not_allowed()

    def do_PUT(self) -> None:
        self._send_method_not_allowed()

    def do_PATCH(self) -> None:
        self._send_method_not_allowed()

    def do_DELETE(self) -> None:
        self._send_method_not_allowed()

    def _send_method_not_allowed(self) -> None:
        body = _render_layout("Method Not Allowed", "<h1>Method Not Allowed</h1>")
        payload = body.encode("utf-8")
        self.send_response(HTTPStatus.METHOD_NOT_ALLOWED.value)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Allow", "GET")
        self.end_headers()
        self.wfile.write(payload)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local read-only dashboard for jarvis-core tasks.")
    parser.add_argument("--host", default="127.0.0.1", help="Local bind host. Allowed: 127.0.0.1, localhost")
    parser.add_argument("--port", default=8765, type=int, help="Local bind port.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.host not in LOCAL_HOSTS:
        raise SystemExit("host_not_allowed: use 127.0.0.1 or localhost")

    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"Serving read-only dashboard at http://{args.host}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
