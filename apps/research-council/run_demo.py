"""Run a local Research Council placeholder demo."""

from __future__ import annotations

from research_council import ResearchCouncilInput, run_research_council


def build_sample_input() -> ResearchCouncilInput:
    return ResearchCouncilInput(
        raw_idea=(
            "People who collect notes in scattered tools might adopt a small "
            "AI-assisted research workflow if it turns vague project ideas into "
            "testable claims."
        ),
        goal=(
            "Validate whether a lightweight Research Council module is useful "
            "enough to become the first practical Jarvis app."
        ),
        context=(
            "Jarvis Core is an orchestration and records layer. Research Council "
            "should stay isolated as an app module for now."
        ),
        constraints=(
            "No web search in v0.1.",
            "No LLM calls in v0.1.",
            "Produce a Markdown report.",
        ),
        provided_evidence=(
            "User explicitly requested structured claims, an evidence ledger, critiques, experiments, and a Markdown research report.",
        ),
    )


def main() -> None:
    result = run_research_council(build_sample_input())
    print(result.markdown_report.markdown)


if __name__ == "__main__":
    main()
