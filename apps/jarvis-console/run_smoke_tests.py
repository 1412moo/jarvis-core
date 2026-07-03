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
    history_code, history = run_web_app.handle_get_api("/api/history")
    assert history_code == HTTPStatus.OK
    assert history["ok"] is True
    assert history["mode"] == "read-only"
    assert history["repo"]["head_short"]
    assert "root" not in history["repo"]
    assert "jarvis.bat" in history["repo"]["protected_path_note"]
    assert history["recent_commits"]
    assert len(history["recent_commits"]) <= run_web_app.HISTORY_MAX_COMMITS
    for commit in history["recent_commits"]:
        run_web_app.assert_history_commit_safety(commit)
    history_items = history["checkpoint_docs"] + history["related_items"]
    assert history_items
    for item in history_items:
        run_web_app.assert_overview_item_safety(item)
        assert run_web_app.is_history_candidate_name(Path(item["path"]))
    assert any(item["path"] == "docs/jarvis-console-v0.1-checkpoint.md" for item in history["checkpoint_docs"])
    assert [item["path"] for item in history["discovery"]["safe_directories"]] == [
        "docs",
        "apps/jarvis-console",
        "apps/hermes-manager-pilot/examples",
        "apps/daily-ai-radar/examples",
    ]
    assert ".git" in history["discovery"]["excluded"]
    assert "__pycache__" in history["discovery"]["excluded"]
    assert "This view is read-only." in history["notes"]
    assert "It does not create commits or checkpoints." in history["notes"]

    memory_code, memory = run_web_app.handle_get_api("/api/memory-skills")
    assert memory_code == HTTPStatus.OK
    assert memory["ok"] is True
    assert memory["mode"] == "read-only"
    assert memory["phase"] == "phase_1_read_only_sample"
    assert memory["read_only"] is True
    assert memory["sample"] is True
    assert memory["no_persistence"] is True
    assert memory["runtime_write"] is False
    assert memory["post_endpoints"] is False
    assert len(memory["candidates"]) == 3
    assert "Review Candidate" in memory["allowed_actions"]
    assert "Copy Candidate" in memory["allowed_actions"]
    assert "Copy Skill Draft Prompt" in memory["allowed_actions"]
    assert "Open Skill Details" in memory["allowed_actions"]
    assert any("Voice Inbox" in item for item in memory["guidance"])
    assert any("No automatic memory save." == item for item in memory["safety_boundary"])
    assert any("No runtime file write." == item for item in memory["safety_boundary"])
    for candidate in memory["candidates"]:
        run_web_app.assert_memory_candidate_safety(candidate)
    assert run_web_app.handle_post_api("/api/memory-skills", {})[0] == HTTPStatus.NOT_FOUND
    assert run_web_app.handle_post_api("/api/memory-skills/candidates", {})[0] == HTTPStatus.NOT_FOUND

    for args in (
        ("add", "."),
        ("commit", "-m", "test"),
        ("push",),
        ("reset", "--hard"),
        ("tag", "v0.1"),
        ("merge", "main"),
        ("rebase", "main"),
    ):
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

    assert run_web_app.clean_voice_transcript("코덱스 케어노트 헤르메스") == "Codex CareNote Hermes"
    assert run_web_app.clean_voice_transcript("엠씨피 에이전트 스킬 데일리 레이더") == "MCP Agent Skills Daily AI Radar"
    assert run_web_app.clean_voice_transcript("고깃집 리뷰 정리해줘") == "고깃집 리뷰 정리해줘"
    assert run_web_app.clean_voice_transcript("영화 리뷰 정리해줘") == "영화 리뷰 정리해줘"
    assert run_web_app.clean_voice_transcript("영화 리뷰 수정해줘") == "영화 리뷰 수정해줘"
    assert run_web_app.clean_voice_transcript("프리뷰 화면 확인") == "프리뷰 화면 확인"
    voice_empty_code, voice_empty = run_web_app.handle_post_api("/api/voice-inbox/prepare", {"transcript": ""})
    assert voice_empty_code == HTTPStatus.BAD_REQUEST
    assert voice_empty["error"] == "empty_transcript"
    voice_missing_code, voice_missing = run_web_app.handle_post_api("/api/voice-inbox/prepare", {})
    assert voice_missing_code == HTTPStatus.BAD_REQUEST
    assert voice_missing["error"] == "missing_transcript"
    voice_type_code, voice_type = run_web_app.handle_post_api("/api/voice-inbox/prepare", {"transcript": 123})
    assert voice_type_code == HTTPStatus.BAD_REQUEST
    assert voice_type["error"] == "transcript_must_be_string"
    voice_long_code, voice_long = run_web_app.handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "a" * (run_web_app.VOICE_INBOX_MAX_TRANSCRIPT_CHARS + 1)},
    )
    assert voice_long_code == HTTPStatus.BAD_REQUEST
    assert voice_long["error"] == "transcript_too_long"
    voice_research_code, voice_research = run_web_app.handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "Jarvis, CareNote 복약 기록 UX 리스크를 Research Council로 검증해줘"},
    )
    assert voice_research_code == HTTPStatus.OK
    assert voice_research["task_candidate"]["suggested_skill"] == "research_council"
    assert voice_research["task_candidate"]["confidence"] == "high"
    assert voice_research["task_candidate"]["needs_confirmation"] is True
    assert "CareNote" in voice_research["cleaned_transcript"]
    assert "Research Council" in voice_research["cleaned_transcript"]
    voice_hermes_code, voice_hermes = run_web_app.handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "코덱스한테 README 수정하고 커밋 리뷰 프롬프트 만들어줘"},
    )
    assert voice_hermes_code == HTTPStatus.OK
    assert voice_hermes["task_candidate"]["suggested_skill"] == "hermes_manager"
    assert "Codex" in voice_hermes["cleaned_transcript"]
    assert "commit" in voice_hermes["cleaned_transcript"]
    assert "review" in voice_hermes["cleaned_transcript"]
    voice_radar_code, voice_radar = run_web_app.handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "MCP Agent Skills 새 기술 Daily Radar로 확인해줘"},
    )
    assert voice_radar_code == HTTPStatus.OK
    assert voice_radar["task_candidate"]["suggested_skill"] == "daily_ai_radar"
    voice_memory_code, voice_memory = run_web_app.handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "이 반복 작업 skill 후보로 기억해줘"},
    )
    assert voice_memory_code == HTTPStatus.OK
    assert voice_memory["task_candidate"]["suggested_skill"] == "memory_skills"
    assert voice_memory["task_candidate"]["needs_confirmation"] is True
    voice_unknown_code, voice_unknown = run_web_app.handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "오늘 뭐하지"},
    )
    assert voice_unknown_code == HTTPStatus.OK
    assert voice_unknown["task_candidate"]["suggested_skill"] == "unknown"
    assert voice_unknown["task_candidate"]["confidence"] == "low"
    voice_restaurant_code, voice_restaurant = run_web_app.handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "고깃집 리뷰 정리해줘"},
    )
    assert voice_restaurant_code == HTTPStatus.OK
    assert voice_restaurant["task_candidate"]["suggested_skill"] == "unknown"
    assert voice_restaurant["cleaned_transcript"] == "고깃집 리뷰 정리해줘"
    assert "고git" not in voice_restaurant["cleaned_transcript"]
    voice_movie_code, voice_movie = run_web_app.handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "영화 리뷰 정리해줘"},
    )
    assert voice_movie_code == HTTPStatus.OK
    assert voice_movie["task_candidate"]["suggested_skill"] == "unknown"
    assert voice_movie["cleaned_transcript"] == "영화 리뷰 정리해줘"
    voice_movie_edit_code, voice_movie_edit = run_web_app.handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "영화 리뷰 수정해줘"},
    )
    assert voice_movie_edit_code == HTTPStatus.OK
    assert voice_movie_edit["task_candidate"]["suggested_skill"] == "unknown"
    assert voice_movie_edit["cleaned_transcript"] == "영화 리뷰 수정해줘"
    voice_preview_code, voice_preview = run_web_app.handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "프리뷰 화면 확인"},
    )
    assert voice_preview_code == HTTPStatus.OK
    assert voice_preview["task_candidate"]["suggested_skill"] == "unknown"
    assert voice_preview["cleaned_transcript"] == "프리뷰 화면 확인"
    voice_report_review_code, voice_report_review = run_web_app.handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "report review draft"},
    )
    assert voice_report_review_code == HTTPStatus.OK
    assert voice_report_review["task_candidate"]["suggested_skill"] == "unknown"
    voice_daily_routine_code, voice_daily_routine = run_web_app.handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "데일리 루틴 정리"},
    )
    assert voice_daily_routine_code == HTTPStatus.OK
    assert voice_daily_routine["task_candidate"]["suggested_skill"] == "unknown"
    assert "This is a task candidate, not an execution." in voice_research["safety_notes"]

    app_js = Path(__file__).resolve().parent.joinpath("web", "app.js").read_text(encoding="utf-8")
    html = Path(__file__).resolve().parent.joinpath("web", "index.html").read_text(encoding="utf-8")
    assert "Voice Inbox" in html
    assert "Transcript / rough thought" in html
    assert "Prepare Task Candidate" in html
    assert "Paste From Clipboard" in html
    assert "Clear Transcript" in html
    assert "v0.1 does not record audio." in html
    assert "Jarvis will not run tools until you choose a handoff." in html
    assert "Refresh Overview" in html
    assert "Refresh History" in html
    assert "Refresh Memory / Skills" in html
    assert "Checkpoints / History" in html
    assert "Read-only operations dashboard" in html
    assert "does not create tasks" in html
    assert "does not create commits" in html
    assert "read-only: sample candidates only" in html
    assert "no POST" in html
    assert "no persistence" in html
    assert "no runtime write" in html
    assert "recommendedSkillId" in app_js
    assert "handoffStepsForSkill" in app_js
    assert "copyNextActionForHandoff" in app_js
    assert "/api/overview" in app_js
    assert "/api/history" in app_js
    assert "/api/memory-skills" in app_js
    assert "/api/voice-inbox/prepare" in app_js
    assert "renderOverview" in app_js
    assert "renderHistory" in app_js
    assert "renderMemorySkills" in app_js
    assert "loadMemorySkills" in app_js
    assert "memoryCandidateCards" in app_js
    assert "renderRecentCommits" in app_js
    assert "renderVoiceCandidate" in app_js
    assert "prepareVoiceCandidate" in app_js
    assert "jarvisCommandFromCleaned" in app_js
    assert "voiceUnknownGuidance" in app_js
    assert "renderRecentGroups" in app_js
    assert "normalizedOverviewItemsMarkup" in app_js
    assert "Read-only metadata" in app_js
    assert "overview-badge" in app_js
    assert "Open file" not in app_js
    assert "Edit file" not in app_js
    assert "Delete file" not in app_js
    assert "navigator.mediaDevices" not in app_js
    assert "getUserMedia" not in app_js
    assert "<audio" not in app_js
    assert "MediaRecorder" not in app_js
    assert "loadOverview" in app_js
    assert "loadHistory" in app_js
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
    assert "navigator.clipboard.writeText(text)" in app_js
    assert "copy-text" in app_js
    assert "Copy Cleaned Task" in app_js
    assert "Copy As Jarvis Command" in app_js
    assert "Open Memory / Skills" in app_js
    assert "Copy Candidate" in app_js
    assert "Copy Skill Draft Prompt" in app_js
    assert "Review Candidate" in app_js
    assert "does not save this candidate automatically" in app_js
    assert "No persistence, no runtime write, and no automatic skill creation." in app_js
    assert "No matching skill yet." in app_js
    assert "Idea validation -> Research Council" in app_js
    assert ">Run<" not in app_js
    assert ">Execute<" not in app_js
    assert ">Start<" not in app_js

    print("Jarvis Console smoke tests passed")


if __name__ == "__main__":
    main()
