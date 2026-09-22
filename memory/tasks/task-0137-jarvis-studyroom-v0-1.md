# task-0137-jarvis-studyroom-v0-1

- id: `task-0137-jarvis-studyroom-v0-1`
- title: `Jarvis Studyroom v0.1 — 학습용 SPA 골격(A)과 실제 개발 역사/학습 콘텐츠(B)`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-22 10:00 UTC`
- updated_at: `2026-09-22 23:20 UTC`
- summary: `apps/studyroom/ — Jarvis-Core 자체를 교재 삼는 개인용 read-only 학습 SPA. A 단계(골격: Python stdlib 서버, path traversal 방어, 6-tab SPA, quiz+LocalStorage)는 코드로 이미 존재했으나 task 기록이 없었다. B 단계에서 recordroom 5건·glossary 15건·learn 10주제로 콘텐츠를 확장했다. 독립 Reviewer/QA가 glossary.json의 owner-approval·candidate 두 항목에서 사실 오류를 발견(PASS WITH MINOR)했고, 최소 범위로 수정한 뒤 재검증에서 PASS를 받았다. commit \`6dd2352df35ec3415f260ab4195753fe2e035cb1\`(12파일, "feat(studyroom): add v0.1 learning content")으로 반영했으며 push는 하지 않았다. Owner가 채팅에서 DONE 전환을 직접 지시했다.`
- source_command: `Owner가 채팅으로 직접 지시한 Studyroom task-0137-A 상태 확인(read-only) 및 task-0137-B 콘텐츠 구현`

## 기준선

| 항목 | 값 |
| --- | --- |
| 작업 전 상태 | tracked 수정 없음, untracked `apps/studyroom/`(A 단계 산출물, task 기록 없음), `jarvis.bat` |
| A 단계 확인 시점 | Reviewer/QA 없이 이 세션에서 read-only로 직접 확인 |
| B 단계 착수 근거 | Owner가 채팅에서 recordroom 5건(task-0001/0043/0044/0055/0073), glossary 15개 후보, learn 10주제를 직접 지정 |

## A 단계 — read-only 확인 결과 (이 기록 이전에 이미 존재하던 상태)

이번 세션 이전에 `apps/studyroom/`이 코드로는 이미 만들어져 있었으나, `memory/tasks/`,
`docs/`, `git log --all` 어디에도 task-0137 기록이 없었다. 저장소 규칙(모든 작업은
`memory/tasks/`에 기록)에 대한 예외였다.

| 확인 항목 | 결과 |
| --- | --- |
| 6개 화면(Home/Recordroom/Technologies/Features/Glossary/Learn) | `web/index.html` nav-tab과 `web/app.js`의 `switchTab()`에 전부 대응 함수 존재 |
| SPA navigation | `innerHTML` 교체 + `active` 클래스 토글, 페이지 리로드 없음 |
| Learn quiz + LocalStorage | 클릭 → `localStorage.setItem('studyroom_quiz_<topicId>_<qIdx>', ...)` → 재렌더, 진행률 배너·초기화 버튼 존재 |
| JSON content loading | `fetch()` + in-memory cache, content 5파일 전부 대응 |
| Python stdlib HTTP 서버 | `http.server`만 사용, 외부 패키지 import 없음(스모크테스트가 강제) |
| Path traversal 방어 | `resolve_safe_path()`의 `target.relative_to(base_dir)` 검사, 우회 패턴 3종 403 확인 |
| 콘텐츠 볼륨(A 단계 시점) | recordroom 1건, glossary 2건, learn 1주제·quiz 1문항 — 스키마 검증용 seed 수준 |

## B 단계 — 무엇을 만들었나 (이번 세션)

| 파일 | 변경 |
| --- | --- |
| `apps/studyroom/content/recordroom.json` | 1건 → 5건. task-0001(기존 유지)·task-0043·task-0044·task-0055·task-0073 |
| `apps/studyroom/content/glossary.json` | 2건 → 15건. Commit/Baseline(기존 유지) + Candidate/Atomic Write/Fail-Closed/Append-Only Log/Hash Chain/Canonical JSON/Domain-Separated Hash/Path Traversal/SPA/Role-Based Signing Key/Owner Approval/Durable Writer/Smoke Test |
| `apps/studyroom/content/learn.json` | 1주제 → 10주제. learn-commit(기존 유지) + atomic-write/fail-closed/no-secrets/audit-chain/path-traversal/hidden-dependency/role-signing/baseline-candidate/task-system, 각 quiz 1문항 포함(총 10문항) |
| `apps/studyroom/content/technologies.json` | 2건 → 4건. Python/Git(기존 유지) + Node.js(stdlib crypto)/Ed25519 |
| `apps/studyroom/content/features.json` | 2건 → 5건. Task System/Console(기존 유지) + No-Secrets 자동 검사/역할별 서명 키/감사 해시체인 |
| `memory/tasks/task-0137-jarvis-studyroom-v0-1.md` | 이 기록(신규) |

`web/*.html`, `web/*.css`, `web/*.js`, `run_web_app.py`, `run_smoke_tests.py`는 수정하지
않았다. Studyroom 외 Jarvis-Core 코드(`adapters/`, `orchestrator/`, 다른 `apps/*`)와
`jarvis.bat`도 수정하지 않았다.

## 사실성 원칙 적용

모든 recordroom/learn 콘텐츠는 이 세션에서 직접 읽은 다음 task 원문에서만 가져왔다 —
`task-0001-bootstrap.md`, `task-0043-no-secrets-enforcement.md`,
`task-0044-audit-hash-chain.md`, `task-0055-execution-result-atomic-write.md`,
`task-0073-console-codex-review-removal.md`, `task-0042-role-based-signing-keys.md`,
`docs/task-0042-role-based-signing-keys-design.md`, `task-0136-jarvis-reviewer-call-prototype.md`.
날짜·숫자·파일 경로·테스트 결과·실패 원인·배제된 대안은 각 task 원문에 있는 표현만
사용했고, 원문에 없는 세부사항은 보충하지 않았다. `orchestrator/role-signing/`,
`orchestrator/audit-chain/`, `scripts/check_no_secrets.py`,
`orchestrator/discord-intake/task_file_writer.py`의 실제 파일 존재는 `ls`로 재확인한
뒤 technologies/features 항목에 반영했다(파일 내용까지 읽지는 않았으므로 그 이상의
세부 동작 설명은 넣지 않았다). audit-chain 항목은 "구현되었으나 실제 감사 기록은
아직 쌓이지 않는다"는 task-0044 원문의 명시적 한계를 그대로 반영했다 — 구현 완료로
과장하지 않았다.

Quiz 오답은 가능한 경우 원문에서 명시적으로 배제되거나 실패로 확인된 대안을 사용했다
(예: no-secrets 오탐 8건을 "실제 비밀"로 적는 오답, audit-chain 소급 기록을 정답처럼
적는 오답 — 둘 다 원문이 명시적으로 부정한 내용). path-traversal, atomic-write 일부
오답은 원문에 명시된 배제 대안이 없어 기술적으로 합리적인 일반 오답을 사용했다.

## 검증

| # | 항목 | 결과 |
| --- | --- | --- |
| 1 | `python -B apps/studyroom/run_smoke_tests.py` | `ALL SMOKE TESTS PASSED (5/5 suites, 0 failures)`, exit 0 |
| 2 | 콘텐츠 개수(ad-hoc read-only 스크립트, 신규 테스트 파일 아님) | recordroom 5, glossary 15, learn 10(quiz 총 10문항), technologies 4, features 5 |
| 3 | `related_recordroom` ID 교차검증 | 모든 learn 항목의 `related_recordroom` ID가 실제 recordroom ID 집합 안에 있음(불일치 0건) |
| 4 | 참조 파일 실존 확인 | `orchestrator/role-signing/`, `orchestrator/audit-chain/`, `scripts/check_no_secrets.py`, `orchestrator/discord-intake/task_file_writer.py` 모두 `ls`로 실존 확인 |
| 5 | task-0137 기록 부재 재확인 | 이번 세션에서도 `memory/tasks/task-0137*`, `grep -rli "0137" memory docs`, `git log --all --oneline \| grep 0137` 전부 0건이었음을 재확인한 뒤 이 파일을 신규 생성 |

스모크 테스트 자체는 이번 작업에서 확대하지 않았다 — 기존 5개 스위트(필수 파일,
JSON 스키마, path traversal, 실 HTTP 서버, 무의존성)가 콘텐츠 스키마 검증까지 이미
포함하고 있어 추가 테스트가 불필요하다고 판단했다.

## 바꾸지 않은 것

- `apps/studyroom/web/*`, `apps/studyroom/run_web_app.py`, `apps/studyroom/run_smoke_tests.py`
- `adapters/`, `orchestrator/`, `apps/jarvis-console/`, `apps/research-council/`,
  `apps/hermes-manager-pilot/`, `apps/daily-ai-radar/` 등 Studyroom 외 모든 런타임 코드
- `jarvis.bat`
- 이번 작업 범위를 벗어난 기존 task 문서(`memory/tasks/task-0001~0136`), `docs/master-plan.md`

## Reviewer/QA (2026-09-22)

독립 Reviewer/QA 관점에서 실제 파일을 원문과 대조해 검토했다(구현자 관점 요약을 그대로
승인하지 않음). 구조·격리·의존성·테스트 항목은 전부 문제없었으나, 콘텐츠 사실성에서
2건을 발견해 최초 판정은 **PASS WITH MINOR**였다.

| # | Severity | 위치 | 내용 |
| --- | --- | --- | --- |
| 1 | BLOCKING | `glossary.json` `owner-approval` | "승인 1~7의 원문이 그대로 보존되어 있다"고 적었으나, `task-0136-jarvis-reviewer-call-prototype.md` 원문은 승인 6이 Owner 결정에 따라 **원문 없이** 유지됐다고 명시(258·430·446행) |
| 2 | MINOR | `glossary.json` `candidate` | "hash가 없거나 40자가 아니면 BLOCKED"가 task-0136 Skill 자체의 검증처럼 읽혔으나, 실제로는 `.claude/agents/reviewer.md`의 책임이고 `SKILL.md`는 그 규칙을 재구현하지 않고 참조만 함(`SKILL.md:73` "The binding rule stays in the Reviewer") |

### 수정

`glossary.json`의 `owner-approval`·`candidate` 두 항목의 `jarvis_example`만 최소 수정했다.

- `owner-approval`: "승인 1~5와 7의 원문이 그대로 보존되어 있습니다. 승인 6만은 Owner 결정에 따라 원문 없이 유지되며..."로 정정
- `candidate`: "이 검증은 Reviewer 정의(.claude/agents/reviewer.md)의 책임이며 task-0136의 Skill은 그 규칙을 다시 구현하지 않고 참조만 합니다"를 추가

다른 파일(recordroom/learn/technologies/features, web/*, README, task 기록 본문)은 건드리지
않았다.

### 재검증

수정된 두 항목을 `task-0136` 원문, `.claude/agents/reviewer.md`, `SKILL.md`와 다시 대조해
모순이 없음을 확인했다. JSON 파싱 정상(15개 항목, 중복 id 0건), 스모크 테스트
`ALL SMOKE TESTS PASSED (5/5 suites, 0 failures)` exit 0. 최종 판정 **PASS**.

## Commit (2026-09-22)

Owner 지시로 `apps/studyroom/`과 이 기록만 staging해 commit했다.

| 항목 | 값 |
| --- | --- |
| commit hash | `6dd2352df35ec3415f260ab4195753fe2e035cb1` |
| message | `feat(studyroom): add v0.1 learning content` |
| 포함 파일 | 12개 — `apps/studyroom/{README.md, content/*.json(5), run_smoke_tests.py, run_web_app.py, web/*(3)}`, `memory/tasks/task-0137-jarvis-studyroom-v0-1.md` |
| 제외 | `jarvis.bat`(별도 untracked 유지), `apps/studyroom/__pycache__/`(`.gitignore`로 자동 제외) |
| push | 하지 않음 |

커밋 전 `python -B apps/studyroom/run_smoke_tests.py` 재실행으로 PASS를 재확인한 뒤
진행했다.

## 남은 작업

- push는 Owner가 별도로 결정
- (INFO, task-0137-B 범위 밖) `web/app.js`의 Home 카드 문구와 `README.md`가 "Nostr"를
  Technologies 주제로 언급하지만 `technologies.json`에는 아직 없음 — 후속 콘텐츠 추가 또는
  문구 정정이 필요하면 별도 task로 진행
