"""Minimal HTTP smoke check for the local read-only dashboard."""

from __future__ import annotations

import http.client
import json
import threading
from http.server import ThreadingHTTPServer

from dashboard import DashboardHandler


HOST = "127.0.0.1"


class QuietDashboardHandler(DashboardHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


def _request(port: int, method: str, path: str) -> tuple[int, dict[str, str], str]:
    connection = http.client.HTTPConnection(HOST, port, timeout=5)
    try:
        connection.request(method, path)
        response = connection.getresponse()
        body = response.read().decode("utf-8", errors="replace")
        return response.status, dict(response.getheaders()), body
    finally:
        connection.close()


def _run_case(
    port: int,
    name: str,
    method: str,
    path: str,
    expected_status: int,
    expected_text: tuple[str, ...] = (),
    expected_allow: str | None = None,
    unexpected_text: tuple[str, ...] = (),
) -> dict[str, object]:
    actual_status, headers, body = _request(port, method, path)
    missing_text = [text for text in expected_text if text not in body]
    unexpected_present = [text for text in unexpected_text if text in body]
    actual_allow = headers.get("Allow")
    passed = actual_status == expected_status and not missing_text and not unexpected_present
    if expected_allow is not None:
        passed = passed and actual_allow == expected_allow

    return {
        "name": name,
        "method": method,
        "path": path,
        "expected_status": expected_status,
        "actual_status": actual_status,
        "expected_text": list(expected_text),
        "missing_text": missing_text,
        "unexpected_text": list(unexpected_text),
        "unexpected_present": unexpected_present,
        "expected_allow": expected_allow,
        "actual_allow": actual_allow,
        "passed": passed,
    }


def main() -> None:
    server = ThreadingHTTPServer((HOST, 0), QuietDashboardHandler)
    port = int(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, daemon=True)

    try:
        thread.start()
        cases = [
            ("root", "GET", "/", 200, ("Jarvis Tasks",), None),
            ("tasks", "GET", "/tasks", 200, ("Recently updated tasks",), None),
            (
                "task_detail",
                "GET",
                "/tasks/task-0002-report-system",
                200,
                ("task-0002-report-system", "Back to task list"),
                None,
            ),
            ("missing", "GET", "/missing", 404, (), None),
            ("tasks_status_done", "GET", "/tasks?status=DONE", 200, ("Filtered by status: DONE",), None),
            ("tasks_status_invalid", "GET", "/tasks?status=INVALID", 400, (), None),
            ("tasks_auto_refresh", "GET", "/tasks", 200, ('http-equiv="refresh"',), None),
            (
                "tasks_footer_info",
                "GET",
                "/tasks",
                200,
                ("Localhost read-only dashboard", "Auto refresh: 30s"),
                None,
            ),
            (
                "tasks_nav_links",
                "GET",
                "/tasks",
                200,
                ("/tasks?status=DONE", "/tasks?status=DOING"),
                None,
            ),
            (
                "tasks_nav_all_active",
                "GET",
                "/tasks",
                200,
                ('class="active"', '<a class="active" href="/tasks">All Tasks</a>'),
                None,
            ),
            (
                "tasks_done_nav_active",
                "GET",
                "/tasks?status=DONE",
                200,
                ('<a class="active" href="/tasks?status=DONE">DONE</a>',),
                None,
            ),
            (
                "task_detail_no_auto_refresh",
                "GET",
                "/tasks/task-0002-report-system",
                200,
                (),
                None,
                ('http-equiv="refresh"',),
            ),
            (
                "task_detail_footer_info",
                "GET",
                "/tasks/task-0002-report-system",
                200,
                ("Localhost read-only dashboard",),
                None,
                ("Auto refresh: 30s",),
            ),
            (
                "task_detail_nav_link",
                "GET",
                "/tasks/task-0002-report-system",
                200,
                ("/tasks?status=DONE",),
                None,
            ),
            (
                "task_detail_nav_no_active",
                "GET",
                "/tasks/task-0002-report-system",
                200,
                ("/tasks?status=DONE",),
                None,
                ('class="active"',),
            ),
            ("post_tasks", "POST", "/tasks", 405, (), "GET"),
        ]
        results = [_run_case(port, *case) for case in cases]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    failed = [result for result in results if not result["passed"]]
    print(json.dumps({"total": len(results), "failed": len(failed), "results": results}, indent=2))
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
