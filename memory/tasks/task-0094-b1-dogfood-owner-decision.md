# task-0094-b1-dogfood-owner-decision

- id: `task-0094-b1-dogfood-owner-decision`
- title: `B1 C - dogfood 23건 처리 방안 Owner Decision 대기`
- status: `NEEDS_APPROVAL`
- repo: `jarvis-core`
- created_at: `2026-09-08 06:05 UTC`
- updated_at: `2026-09-08 06:05 UTC`
- summary: `B1 저장소 위생 작업의 남은 절반을 결정 대기 상태로 기록한다. A+B 는 cd179db 로 완료되어 historical task 4건과 work-order 6건이 편입됐고 끊어진 링크 4건이 해소됐다. 남은 untracked 는 dogfood 23건과 jarvis.bat 뿐이다. 이 기록은 결정이 아니라 결정 근거의 정리다. A/B/C/D 네 선택지를 사실 기반으로 비교하고, memory/tasks 디렉터리 전체 ignore 는 금지 사항으로 못박고, jarvis.bat 은 B1 C 범위에서 제외한다. 조사 중 B1 보고의 참조 분석 1건을 정정했다 - dogfood full task id 를 참조하는 tracked 파일은 0건이다.`
- source_command: `B1 C dogfood 23건 처리 방안 결정 대기 기록 작성 지시`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | **`cd179db`** = `origin/main` |
| tracked working tree | clean |
| untracked | **24건** — dogfood 23 + `jarvis.bat` |
| 이 작업의 변경 | **이 기록 파일 1개뿐** |

## 직전 상태

| 작업 | 커밋 | 내용 |
| --- | --- | --- |
| task-0093 | `8bbd019` | `suggest_skill` 부분문자열 라우팅 오탐 수정 |
| task-0093 기록 | `b9916ea` | 위 구현의 canonical 기록 |
| B1 read-only 조사 | (커밋 없음) | untracked 33건 분류 |
| **B1 A+B** | **`cd179db`** | historical task 4건 + work-order 6건 편입, **10 files, +269 / -0** |

### B1 A+B 가 편입한 10건

`memory/tasks` 4건 — `task-0030`, `task-0032`, `task-0033`, `task-0036`
(전부 `NEEDS_APPROVAL` 의사결정 기록)

`prompts` 6건 — `task-0030`, `task-0032`, `task-0033`, `task-0034`,
`task-0035`, `task-0036` work-order

편입 근거는 **끊어진 링크 4건**이었다. tracked 파일이 untracked 파일을 가리키고
있었고, 편입으로 전부 해소됐다.

| tracked 참조원 | 대상 | 결과 |
| --- | --- | --- |
| `memory/tasks/task-0034-...` | `prompts/task-0034-...-work-order` | 해소 |
| `memory/tasks/task-0035-...` | `prompts/task-0035-...-work-order` | 해소 |
| `prompts/task-0031-...-work-order` | `memory/tasks/task-0030-...` | 해소 |
| `docs/chatgpt-discord-claude-auto-collab-v0.1-design.md` | `memory/tasks/task-0030-...` | 해소 |

## 남은 untracked

### dogfood 23건 — `task-0006` ~ `task-0028`

| 항목 | 실측값 |
| --- | --- |
| 건수 | 23 |
| 생성 시각 범위 | **2026-07-30 10:55 UTC ~ 11:55 UTC** — 1시간, 단일 세션 |
| status | **23건 전부 `DONE`** |
| 줄 수 | **23건 전부 11줄** |
| 크기 | **20건이 386 bytes 동일 템플릿**, 나머지 3건 564 / 648 / 774 bytes |
| header 필드 | 23건 전부 `id` `title` `status` `repo` `created_at` `updated_at` `summary` `completion_evidence` `source_command` |
| `source_command` | `Voice Inbox` 22건, `Evaluate Idea` 1건 |
| canonical | **23/23 PASS** |

`completion_evidence` 는 전부
`Dogfood cycle NN completed through the actual Jarvis Console UI at <ISO8601>.`
형태다. **Console lifecycle 을 실제 UI 로 20회 돌린 실행 증거**이며, 동시에
**단일 세션이 1시간 만에 찍어낸 반복 산출물**이다. 두 성격을 동시에 갖는다는
점이 이 결정이 어려운 이유다.

`task-0006` 의 `source_command` 는 `Evaluate Idea` 인데, 이 Console 기능은
task-0075 에서 제거됐다. 즉 이 기록 1건은 **현재 존재하지 않는 기능의 유일한
실행 흔적**이다.

### `jarvis.bat` 1건

**B1 C 범위에서 제외한다.** 계속 untracked 로 유지하며, 이번 작업에서도
열지 않았고 읽지 않았고 건드리지 않았다. 이 저장소 전체 이력에서 `jarvis.bat`
을 건드린 커밋은 여전히 **0건**이다.

## canonical 수치가 둘인 이유

| 기준 | 값 |
| --- | --- |
| **fresh-clone (tracked)** | **58/58 PASS** |
| **local disk** | **81/81 PASS** |

차이 23 = **정확히 dogfood 23건**이다.

`memory/tasks` 는 디스크에서 읽히므로 이 PC 에서는 81개가 보이지만,
클론한 사람은 58개만 본다. **같은 검증을 돌려도 다른 숫자가 나온다.**
B1 C 를 결정해야 이 이중 기준이 사라진다 — A 를 택하면 81/81 로 합쳐지고,
B/C 를 택하면 58/58 로 확정된다. D 를 유지하는 한 두 수치는 계속 다르다.

그때까지 canonical 수치를 보고할 때는 **반드시 두 기준을 함께 적는다.**

## B1 조사 보고의 정정 1건

B1 read-only 보고에서 tracked 파일 여러 개가 dogfood task id 를 참조한다고
적었고 "픽스처 문자열일 수 있다"는 단서를 달았다. 이번에 정확히 확인한 결과
**단서 쪽이 맞았다.**

**dogfood 의 full task id 를 참조하는 tracked 파일은 0건이다.**

short id 가 등장하는 9개 파일은 전부 다른 것이었다.

| 위치 | 실제 내용 | 판정 |
| --- | --- | --- |
| `adapters/discord/bot_minimal.py` | `task-0006-self-check`, `task-0007-self-check`, `task-0009-self-check`, `task-0020-self-check` | 합성 픽스처 id — 별개 |
| `orchestrator/discord-intake/intake_parser.py` | `task-0007-discord-intake` | 예시 문자열 — 별개 |
| `orchestrator/discord-intake/run_smoke_tests.py` | `task-0007-sample` | 픽스처 — 별개 |
| `orchestrator/discord-nl-intent/run_smoke_tests.py` | `"task-0028 진행 상황 알려줘"` | NL intent 입력 텍스트 — 파일 불필요 |
| `docs/approve-target-id-alignment-note.md` 외 2건 | `task-0007-discord-intake` | 문서 예시 — 별개 |
| `docs/task-0041-append-only-event-log-design.md` | `task-0006` 을 포맷 샘플로 언급 | 산문 |
| `docs/chatgpt-handoff.md` | 23건을 **집단으로** 언급 | 산문 (아래 별도 항목) |

**이것이 C 와 A+B 의 결정적 차이다.** A+B 는 끊어진 링크 4건이라는 강제 사유가
있었지만, **C 에는 끊어진 링크가 0건이다.** 편입해야 할 기술적 압력이 없다.

테스트 결합도 없다. `run_smoke_tests.py:514`, `:797` 의
`len(list(tasks_dir.glob("task-*.md"))) == 1` 두 건은 모두 **임시 디렉터리**를
쓴다. 실제 `memory/tasks` 개수에 의존하는 tracked 테스트는 **0건**이다.

## 이미 기록된 기존 입장

`docs/chatgpt-handoff.md` (tracked) 에 이 문제에 대한 **명시적 입장이 이미
적혀 있다.**

- L62 — dogfood 23건은 실제 smoke/dogfood 산출물이며 저장소에 커밋된 테스트
  픽스처가 아니라고 구분한다.
- L507 — 이 23건이 working tree 를 의도적으로 dirty 하게 만든다고 적고,
  **명시적 결정 없이 stage / 삭제 / 픽스처 전환하지 말 것**을 지시한다.
  상태는 `Planned`.

**즉 현재의 D(유지) 상태는 사고가 아니라 기록된 유예다.** 그리고 그 기록이
요구하는 "명시적 결정"이 바로 B1 C 다. 어느 선택지를 택하든
`docs/chatgpt-handoff.md` L507 의 상태를 함께 갱신해야 한다.

## 검토 대상 선택지

### A — dogfood 23건 commit

| | |
| --- | --- |
| 장점 | canonical 이 81/81 단일 기준으로 합쳐진다. 번호 구멍 `0006~0028` 이 메워진다. Console lifecycle 20회 실행 증거가 저장소에 남는다. `Evaluate Idea` 로 만들어진 `task-0006` 이 제거된 기능의 흔적으로 보존된다 |
| 단점 | 386 bytes 동일 템플릿 20건이 영구 유입된다. 끊어진 링크가 0건이므로 **기술적 필요가 없다**. `memory/tasks` 를 실제 작업 기록 디렉터리로 읽는 사람에게 신호 대 잡음비가 나빠진다 |
| 비용 | 되돌리려면 삭제 커밋이 필요하고 이력에는 남는다 |

### B — dogfood 23건 삭제

| | |
| --- | --- |
| 장점 | 가장 깨끗한 최종 상태. canonical 58/58 로 확정. untracked 가 `jarvis.bat` 1건만 남는다 |
| 단점 | **비가역이다.** 20회 실행 증거가 사라진다. `task-0006` 의 `Evaluate Idea` 흔적은 복구 불가 |
| 충돌 | `docs/chatgpt-handoff.md` L62 는 이들을 "실제 산출물"로 규정했고 L507 은 명시적 결정 없는 삭제를 금지한다. **삭제하려면 그 판단을 뒤집는 근거가 필요하다** |

### C — 파일별 / 명시적 규칙으로 ignore

| | |
| --- | --- |
| 장점 | 파일은 남기고 working tree 는 깨끗해진다. canonical 58/58 로 확정. 비가역 손실 없음 |
| 단점 | `.gitignore` 에 23줄이 추가되고 영구 유지보수 부담이 된다. 이 PC 에만 존재하는 파일을 저장소 설정으로 관리하게 되어 **저장소가 특정 머신 상태를 기술하게 된다** |
| 필수 조건 | **파일 단위 열거 또는 `task-00NN-dogfood-cycle-NN.md` 수준의 정밀 패턴만 허용.** 아래 금지 사항 참조 |

### D — 당분간 untracked 유지 (현행)

| | |
| --- | --- |
| 장점 | 비용 0. 비가역 조치 없음. `docs/chatgpt-handoff.md` L507 의 기존 입장과 일치 |
| 단점 | **canonical 이중 기준(58 vs 81)이 계속된다.** `git status` 가 항상 23건 dirty 로 보여 실제 미커밋 변경을 가린다. 결정이 무기한 미뤄진다 |

## 금지 사항 — 디렉터리 전체 ignore

**`memory/tasks/` 를 디렉터리 단위로 ignore 하는 방식은 어떤 선택지에서도
채택하지 않는다.**

이유: `memory/tasks` 는 이 프로젝트의 **작업 기록 디렉터리**이고 현재 tracked
58건이 들어 있다. 디렉터리 패턴을 넣으면 `task-0095` 이후의 모든 신규 기록이
**자동으로 삼켜진다.** 새 작업 기록을 커밋하려던 사람이 조용히 실패하고,
그 사실을 한참 뒤에 발견하게 된다.

C 를 택할 경우 반드시 **파일 단위 열거** 또는 dogfood 만 정확히 겨냥하는
패턴을 쓰고, 신규 기록이 걸리지 않는지 `git check-ignore -v` 로 검증한다.

## 이번 작업의 범위

수행한 것 — **이 기록 파일 1개 생성**이 전부다.

수행하지 않은 것:

| 항목 | 상태 |
| --- | --- |
| dogfood 23건 수정 / 삭제 / 이동 / add / ignore | **0건** — `??` 유지 |
| `.gitignore` | **무변경** |
| 코드 | **무변경** |
| 기존 tracked 파일 | **무변경** |
| `jarvis.bat` | **접근하지 않음** |
| B1 C 결정 확정 | **하지 않음** |

## 상태

**B1 A+B = COMPLETE** (`cd179db`)

**B1 C = OWNER DECISION PENDING**

이 기록은 결정문이 아니라 결정 대기 기록이다. A / B / C / D 중 선택은
Owner 에게 남긴다. 결정이 내려지면 그 결정과 실행을 별도 task 로 기록하고,
`docs/chatgpt-handoff.md` L507 의 `Planned` 상태도 함께 갱신한다.
