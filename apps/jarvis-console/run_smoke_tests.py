"""Smoke tests for Jarvis Console v0.1."""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

import run_web_app


def main() -> None:
    run_web_app.run_self_test()

    status_code, status = run_web_app.handle_get_api("/api/status")
    assert status_code == HTTPStatus.OK
    assert status["ok"] is True
    assert status["console"] == "jarvis-console"
    assert status["mode"] == "local-only"
    assert status["registry_read_only"] is True
    assert len(status["skills"]) == 6
    assert {skill["skill_id"] for skill in status["skills"]}.issuperset(
        {"research_council", "daily_ai_radar", "hermes_manager"}
    )
    assert all({"docs", "tests", "examples", "action_guide", "when_to_use"}.issubset(skill) for skill in status["skills"])

    skill_code, skill_detail = run_web_app.handle_get_api("/api/skill", "skill_id=hermes_manager")
    assert skill_code == HTTPStatus.OK
    assert skill_detail["ok"] is True
    assert skill_detail["skill"]["skill_id"] == "hermes_manager"
    assert skill_detail["skill"]["docs"]
    assert skill_detail["skill"]["tests"]
    assert skill_detail["skill"]["action_guide"]
    assert skill_detail["skill"]["primary_next_action_label"] == "Open Hermes Manager"

    research_code, research_detail = run_web_app.handle_get_api("/api/skill", "skill_id=research_council")
    assert research_code == HTTPStatus.OK
    assert research_detail["skill"]["handoff_steps"][2] == "In the launcher, paste your idea, click Idea \uad6c\uccb4\ud654, then run the report."
    daily_code, daily_detail = run_web_app.handle_get_api("/api/skill", "skill_id=daily_ai_radar")
    assert daily_code == HTTPStatus.OK
    assert daily_detail["skill"]["handoff_steps"][2] == (
        "Read the generated radar report and review Executive Summary, Candidate Highlights, and Governance Notes."
    )
    assert "Radar recommendations are candidates, not implementation approval." in daily_detail["skill"]["safety_notes"]

    missing_skill_code, missing_skill = run_web_app.handle_get_api("/api/skill", "skill_id=missing")
    assert missing_skill_code == HTTPStatus.NOT_FOUND
    assert missing_skill["error"] == "unknown_skill"

    overview_code, overview = run_web_app.handle_get_api("/api/overview")
    assert overview_code == HTTPStatus.OK
    assert overview["ok"] is True
    assert overview["mode"] == "read-only"
    assert overview["repo"]["head_short"]
    assert "jarvis.bat" in overview["repo"]["protected_path_note"]
    assert len(overview["tasks"]) <= run_web_app.OVERVIEW_MAX_TOTAL_ITEMS
    assert len(overview["reports"]) <= run_web_app.OVERVIEW_MAX_TOTAL_ITEMS
    assert len(overview["checkpoints"]) <= run_web_app.OVERVIEW_MAX_TOTAL_ITEMS
    assert len(overview["docs_examples"]) <= run_web_app.OVERVIEW_MAX_TOTAL_ITEMS
    assert [group["group_id"] for group in overview["recent_groups"]] == [
        "tasks",
        "reports",
        "checkpoints",
        "docs_examples",
    ]
    assert [group["title"] for group in overview["recent_groups"]] == [
        "Recent Tasks",
        "Recent Reports",
        "Recent Checkpoints",
        "Recent Docs / Examples",
    ]
    assert all(group["read_only"] is True for group in overview["recent_groups"])
    assert overview["discovery"]["max_items_per_directory"] == run_web_app.OVERVIEW_MAX_ITEMS_PER_DIRECTORY
    assert overview["discovery"]["allowed_extensions"] == sorted(run_web_app.OVERVIEW_ALLOWED_EXTENSIONS)
    assert ".git" in overview["discovery"]["excluded"]
    assert "__pycache__" in overview["discovery"]["excluded"]
    assert any(skill["skill_id"] == "daily_ai_radar" for skill in overview["skills"])
    overview_items = [
        item
        for section in ("tasks", "reports", "checkpoints", "docs_examples")
        for item in overview[section]
    ]
    overview_items.extend(item for group in overview["recent_groups"] for item in group["items"])
    overview_items.extend(item for skill in overview["skills"] for item in skill["recent_items"])
    assert overview_items
    for item in overview_items:
        run_web_app.assert_overview_item_safety(item)
    assert any(item["source_area"] == "jarvis_console" for item in overview["checkpoints"] + overview["docs_examples"])
    assert any(item["item_type"] == "checkpoint" for item in overview["checkpoints"])
    assert all(item["item_type"] == "task" for item in overview["tasks"])
    assert all(item["item_type"] == "report" for item in overview["reports"])
    assert run_web_app.is_overview_candidate_path(run_web_app.REPO_ROOT / "docs" / "sample.md") is True
    assert run_web_app.is_overview_candidate_path(run_web_app.REPO_ROOT / "docs" / "sample.py") is False
    assert run_web_app.is_overview_candidate_path(run_web_app.REPO_ROOT / ".git" / "config.txt") is False
    assert run_web_app.is_overview_candidate_path(run_web_app.REPO_ROOT / "docs" / "__pycache__" / "sample.md") is False
    assert run_web_app.is_overview_candidate_path(run_web_app.REPO_ROOT / "docs" / ".hidden.md") is False
    assert run_web_app.is_overview_candidate_path(run_web_app.REPO_ROOT / "docs" / "secret-plan.md") is False
    assert run_web_app.is_overview_candidate_path(
        run_web_app.REPO_ROOT / "docs" / "sample.md",
        run_web_app.REPO_ROOT / "reports",
    ) is False
    for args in (("add", "."), ("commit", "-m", "test"), ("push",), ("reset", "--hard")):
        try:
            run_web_app.validate_read_only_git_args(args)
        except run_web_app.RegistryError:
            pass
        else:
            raise AssertionError(f"unsafe git args were not rejected: {args}")

    suggestion_code, suggestion = run_web_app.handle_post_api(
        "/api/suggest-skill",
        {"message": "I need Codex to review a repo README before commit."},
    )
    assert suggestion_code == HTTPStatus.OK
    assert suggestion["ok"] is True
    assert suggestion["recommended_skill"] == "hermes_manager"
    assert "git_bash" in suggestion["commands"]
    assert "powershell" in suggestion["commands"]

    assert run_web_app.suggest_skill("\uc81c\uc870\uc7a5\ube44 \uc2dc\ubbac\ub808\uc774\uc158 \uc544\uc774\ub514\uc5b4 \uac80\uc99d\ud574\uc918")["recommended_skill"] == "research_council"
    assert run_web_app.suggest_skill("\ucc3d\uc5c5 \uc544\uc774\ub514\uc5b4 \uc0ac\uc5c5\uc131 \uac80\ud1a0\ud574\uc918")["recommended_skill"] == "research_council"
    assert run_web_app.suggest_skill("\uac04\ubcd1 \uc571 \uc544\uc774\ub514\uc5b4 MVP \uac80\uc99d\ud574\uc918")["recommended_skill"] == "research_council"
    assert run_web_app.suggest_skill("Codex \ucee4\ubc0b \ub9ac\ubdf0 \ub3c4\uc640\uc918")["recommended_skill"] == "hermes_manager"
    assert run_web_app.suggest_skill("MCP Agent Skills \uc0c8 \uae30\uc220 \ucc3e\uc544\ubd10")["recommended_skill"] == "daily_ai_radar"
    assert run_web_app.suggest_skill("\ubc18\ubcf5 \uc791\uc5c5 skill\ub85c \uae30\uc5b5\ud574\uc918")["recommended_skill"] == "memory_skills"
    assert run_web_app.suggest_skill("\uc624\ub298 \ubb50\ud558\uc9c0")["recommended_skill"] == "unknown"
    assert run_web_app.suggest_skill("\uc2dc\ubbac\ub808\uc774\uc158 \uac8c\uc784 \ucd94\ucc9c\ud574\uc918")["recommended_skill"] == "unknown"

    app_js = Path(__file__).resolve().parent.joinpath("web", "app.js").read_text(encoding="utf-8")
    html = Path(__file__).resolve().parent.joinpath("web", "index.html").read_text(encoding="utf-8")
    assert "Refresh Overview" in html
    assert "Read-only operations dashboard" in html
    assert "does not create tasks" in html
    assert "recommendedSkillId" in app_js
    assert "handoffStepsForSkill" in app_js
    assert "copyNextActionForHandoff" in app_js
    assert "/api/overview" in app_js
    assert "renderOverview" in app_js
    assert "renderRecentGroups" in app_js
    assert "normalizedOverviewItemsMarkup" in app_js
    assert "Read-only metadata" in app_js
    assert "overview-badge" in app_js
    assert "Open file" not in app_js
    assert "Edit file" not in app_js
    assert "Delete file" not in app_js
    assert "loadOverview" in app_js
    assert "registeredSafetyNotes" in app_js
    assert "skill.safety_notes" in app_js
    assert "Suggested Skill Action Panel" in app_js
    assert "suggestion-action-panel" in app_js
    assert "Open Skill Details" in app_js
    assert "open-skill-details" in app_js
    assert "Open Local URL" in app_js
    assert "open-local-url" in app_js
    assert "Next handoff" in app_js
    assert "handoff-hint" in app_js
    assert "Copy Git Bash or PowerShell command." in app_js
    assert "Run it in your terminal." in app_js
    assert "Open the local URL after the server starts." in app_js
    assert "Follow the copied command output." in app_js
    assert "handoff_steps" in app_js
    assert "Run the command first if the page does not load." in app_js
    assert "data-copy-next-action" in app_js
    assert "Jarvis Console does not run it for you." in app_js
    assert "localOnlyUrl" in app_js
    assert "LOCAL_URL_PREFIX" in app_js
    assert "LOCAL_URL_PROTOCOL" in app_js
    assert "LOCAL_URL_HOSTNAME" in app_js
    assert "new URL(url)" in app_js
    assert "parsed.hostname === LOCAL_URL_HOSTNAME" in app_js
    assert "window.open" in app_js
    assert "noopener,noreferrer" in app_js
    assert "This only opens the URL. It does not start the server." in app_js
    assert "Commands are copy-only." in app_js
    assert "Choose a skill manually from the sidebar." in app_js
    assert "Copy Git Bash" in app_js
    assert "Copy PowerShell" in app_js
    assert "navigator.clipboard.writeText(command)" in app_js
    assert ">Run<" not in app_js
    assert ">Execute<" not in app_js
    assert ">Start<" not in app_js

    print("Jarvis Console smoke tests passed")


if __name__ == "__main__":
    main()
