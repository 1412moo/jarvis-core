# Jarvis Console Skill Registry v0.1

## Purpose

The Jarvis Console skill registry is a read-only metadata file that describes
which Jarvis skill surfaces are visible in the console. It lets the local
browser shell render skill cards, status metadata, command suggestions, and
deterministic routing without hardcoding that information in UI code.

The registry is not a plugin runtime and not an execution permission system.

## Read-Only Rule

Jarvis Console reads the registry. It must not modify the registry during normal
UI use.

Registry entries are display and routing metadata only.

## No Auto Execution Rule

Commands in the registry are display-only. Jarvis Console must not execute
registry commands, spawn app processes, call Codex, call ChatGPT, call Hermes,
or invoke external tools because a registry entry exists.

## Required Fields

Each skill entry must include:

- `skill_id`
- `display_name`
- `status`
- `category`
- `purpose`
- `short_description`
- `safe_next_action`
- `commands`
- `local_url`
- `app_path`
- `tags`
- `route_keywords`
- `safety_notes`
- `non_goals`

The `commands` object must include:

- `git_bash`
- `powershell`

Command values may be empty for planned skills.

## Optional Fields

No optional fields are defined in v0.1. Future versions may add fields, but
unknown fields should not grant new behavior or permissions.

## Allowed Status Values

- `available`
- `planned`
- `experimental`

## Allowed Category Values

- `validation`
- `scouting`
- `workflow`
- `memory`
- `system`

## Route Keywords Rule

`route_keywords` must be a deterministic list of literal strings. Jarvis Console
uses keyword matching only. It must not use an LLM, external API, web search, or
network call to decide routing in v0.1.

Ambiguous or unmatched requests should fall back to `unknown` / manual choice.

## Command Display Rule

Registry commands are instructions for the user to copy or run manually. They
are not buttons and not actions.

Display convention:

- Git Bash command first, using forward slash paths.
- PowerShell command second, using Windows backslash paths.

Jarvis Console must not execute command strings from the registry.

## Command Safety Validation

No registry command may include:

- `git add`
- `git commit`
- `git push`
- `git checkout`
- `git reset`
- `git clean`
- `git rm`
- `git stash`
- `curl`
- `wget`
- `Invoke-WebRequest`
- `Invoke-RestMethod`
- `Start-BitsTransfer`

Commands must not be treated as trusted executable instructions. They are
bounded display text.

## Local URL Rule

If `local_url` is present, it must start with:

```text
http://127.0.0.1
```

No external URL is allowed in v0.1.

## Safety Boundary

The registry must preserve these boundaries:

- Local-only.
- No automatic skill installation.
- No automatic skill execution.
- No Codex automatic invocation.
- No ChatGPT automatic invocation.
- No Hermes automatic invocation.
- No external network/API/LLM calls.
- No scheduler.
- No database.
- No Discord command.
- No MCP/A2A live integration.
- No repository writes.
- No automatic commit or push.
- Human approval required before implementation, commit, push, or external
  action.

## Future Extension Notes

Future versions may add richer skill metadata, examples, icons, capability
levels, or explicit handoff contracts. Those extensions should remain
metadata-first and must not grant execution power by default.
