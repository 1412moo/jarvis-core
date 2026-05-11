# Read-Only Dashboard

## Purpose

`dashboard.py` provides a localhost read-only dashboard for inspecting Jarvis task records in a browser.

It is only an inspection surface for `memory/tasks/*.md`. The Markdown task files remain the source of truth.

## Run

```powershell
python -B adapters/web/dashboard.py --host 127.0.0.1 --port 8765
```

Open:

```text
http://127.0.0.1:8765/
```

## Routes

- `/`
- `/tasks`
- `/tasks/<task-id>`

Unknown GET routes return `404`. Non-GET requests return `405`.

Status filter:

```text
http://127.0.0.1:8765/tasks?status=DONE
```

Supported status values: `TODO`, `DOING`, `BLOCKED`, `DONE`, `FAILED`, `NEEDS_APPROVAL`.

Invalid status values return `400`.

## Read-Only Principles

- No write endpoints.
- No task create/edit/delete behavior.
- No approve/run/retry controls.
- No execution trigger.
- No task status transition behavior.

## Data Source

- `memory/tasks/*.md`
- Existing task metadata contract only.
- Optional execution metadata is displayed only when it already exists in a task file.

## Implementation Limits

- Python standard library only.
- Single-file MVP: `adapters/web/dashboard.py`.
- No database.
- No authentication.
- Localhost only.
- No direct change to Discord command behavior.

## Verification

Start the dashboard:

```powershell
python -B adapters/web/dashboard.py --host 127.0.0.1 --port 8765
```

Check the read-only routes:

```powershell
Invoke-WebRequest http://127.0.0.1:8765/
Invoke-WebRequest http://127.0.0.1:8765/tasks
Invoke-WebRequest http://127.0.0.1:8765/tasks/task-0002-report-system
```

Run the localhost read-only HTTP contract smoke check:

```powershell
python -B adapters/web/run_smoke_check.py
```

The smoke check verifies:

- `GET /`
- `GET /tasks`
- `GET /tasks/<task-id>`
- `404`
- `405`

Confirm existing smoke tests still pass:

```powershell
python -B orchestrator/discord-intake/run_smoke_tests.py
```

## Future Changes

- Keep execution scope separate from UI scope.
- Keep UI changes read-only unless a separate task explicitly expands the contract.
- Be careful about importing `bot_minimal.py` directly; it also owns Discord command behavior and execution-related paths.
- Treat shared parsing as a future refactor, not part of the single-file MVP.
