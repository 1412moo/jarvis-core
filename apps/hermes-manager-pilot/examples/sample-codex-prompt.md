# Sample Codex Prompt Template

This is a safe prompt template Hermes may prepare for user approval. It is not
an automatic Codex invocation.

```text
Repo:
C:\work\jarvis-core

Current HEAD:
<expected-head>

Goal:
<bounded goal>

Target files or directories:
- <path 1>
- <path 2>

Excluded files:
- jarvis.bat

Scope:
- <what to implement or inspect>

Non-goals:
- Do not modify unrelated files.
- Do not modify jarvis.bat.
- Do not use web/API/LLM calls unless explicitly approved.
- Do not add scheduler, crawler, DB, Discord command, or live integration unless explicitly approved.
- Do not commit unless this prompt explicitly asks for a commit.
- Do not push.

Safety:
- Preserve deterministic behavior.
- Keep changes additive and minimal.
- Preserve existing Research Council, Daily AI Radar, adapters, reports, snapshots, hashes, and tests unless explicitly scoped.
- Do not store secrets or sensitive data.

Validation commands:
- <command 1>
- <command 2>

Before finishing:
- Run requested validation commands or explain why any were skipped.
- Report changed files.
- Report risks and non-goals.
- Report working tree status.
- Confirm excluded files were not touched.

Final response:
- Implementation summary.
- Changed files.
- Test results.
- Risks.
- Working tree status.
```

Commit prompt additions, only when the user explicitly asks for a commit:

```text
Commit is approved for the scoped files only.

Before committing:
- Check git status --short.
- Confirm .git/index.lock is absent.
- Stage only approved files.
- Confirm jarvis.bat remains untracked and unstaged.
- Run validation commands.
- Run git diff --cached --stat.
- Run git diff --cached --check.

Commit message:
<approved commit message>

After committing:
- Report commit hash.
- Run git status --short.
- Confirm jarvis.bat remains untracked if it was untracked before.
```
