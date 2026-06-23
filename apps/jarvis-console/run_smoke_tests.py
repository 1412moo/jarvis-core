"""Smoke tests for Jarvis Console v0.1."""

from __future__ import annotations

from http import HTTPStatus

import run_web_app


def main() -> None:
    run_web_app.run_self_test()

    status_code, status = run_web_app.handle_get_api("/api/status")
    assert status_code == HTTPStatus.OK
    assert status["ok"] is True
    assert status["console"] == "jarvis-console"
    assert status["mode"] == "local-only"

    suggestion_code, suggestion = run_web_app.handle_post_api(
        "/api/suggest-skill",
        {"message": "I need Codex to review a repo README before commit."},
    )
    assert suggestion_code == HTTPStatus.OK
    assert suggestion["ok"] is True
    assert suggestion["recommended_skill"] == "hermes_manager"

    print("Jarvis Console smoke tests passed")


if __name__ == "__main__":
    main()
