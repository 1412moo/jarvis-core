# task-0095-chatgpt-handoff-current-state-repair

- id: `task-0095-chatgpt-handoff-current-state-repair`
- title: `chatgpt-handoff.md 현재 상태 정보 정정`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-09 05:48 UTC`
- updated_at: `2026-09-09 05:48 UTC`
- summary: `A1 read-only 감사가 증명한 stale 현재 상태 주장만 최소 diff 로 고쳤다. 이 문서는 2026-08-01 이후 갱신되지 않아 Console 축소 arc 72 커밋을 반영하지 못했고, 존재하지 않는 route 8 개를 Implemented 로 광고하고 있었다. R1 은 제거된 3 계열(Evaluate Idea / Codex Review / Memory & Skills)을 삭제가 아니라 재분류했고 Removed 절을 신설해 근거 task 를 남겼다. R2 는 수치 6 건, R3 는 표시 그룹, R4 는 기준 HEAD, R5 는 부재 함수 주석이다. Decision Log 25 개 해시와 dogfood 실행 기록 등 역사 서술은 손대지 않았다. R6 Console metadata_review 코드 버그는 지시대로 수정하지 않고 별도 task 로 남겼다.`
- source_command: `A1 감사 결과 기반 handoff 현재 상태 정정 지시 (R1-R5, R6 제외)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | **`ad59fb1`** = `origin/main` |
| 직전 작업 | task-0094 (B1 C 결정 대기 기록), A1 read-only 감사 |
| 변경 파일 | `docs/chatgpt-handoff.md` + 이 기록 **2 개뿐** |
| 코드 변경 | **0** |

## 왜 고쳤나

`docs/chatgpt-handoff.md` 는 스스로를 *authoritative fast-start handoff* 로 규정하고
L11 에서 **소스와 충돌하면 문서를 고치라고** 명령한다. 그런데 마지막 갱신이
`e00334a` / **2026-08-01** 이라 그 이후 **72 커밋**(제품 소스 41)이 반영되지 않았다.

가장 실질적인 피해는 API 표였다. 문서는 route **20 개**를 나열하고 그중
**8 개가 존재하지 않는데** 대부분 `Implemented` 로 적혀 있었다. 이 문서를 읽는
외부 협력자는 없는 엔드포인트를 호출하게 된다.

task-0087/0088 이 README·skills.json·master-plan 에서 고친 것과 **같은 결함 유형**이며,
이 파일만 그때 감사 범위 밖이었다.

## R1 — 제거된 3 계열 재분류

**삭제하지 않고 재분류했다.** 근거: L18 이 `Planned` 를 "locked capability … has no
active implementation package" 로 정의하는데, 이 기능들은 잠긴 것이 아니라 **제거된**
것이라 기존 4 라벨 중 어느 것도 정확하지 않았다. 그래서 `## Removed Console Features`
절을 신설하고 제거 근거 task 를 명시했다.

| 계열 | 제거 task | 실측 근거 |
| --- | --- | --- |
| Evaluate Idea / Draft / Final Preview | task-0075 | `evaluate_idea`·`create_task_draft`·`create_task_preview` **0 건**, `web/` 의 `evaluate` **0 건** |
| Codex Review | (adapter 삭제) | `run_web_app.py:35` 주석이 *the deleted codex_review adapter* 라고 명시 |
| Memory / Skills | task-0071, task-0074 | `memory_skills`·`memory_guarded_save`·`candidate_preview` **0 건**, `web/` 의 `memory` **0 건** |

없어진 route **8 개**는 표에서 제거하고 Removed 절에 모았다.

| 없어진 route |
| --- |
| `GET /api/memory-skills` |
| `POST /api/evaluate-idea` |
| `POST /api/evaluate-idea/create-task-draft` |
| `POST /api/evaluate-idea/create-task-preview` |
| `POST /api/evaluate-idea/create-task-preview/invalidate` |
| `POST /api/codex-review/preview` |
| `POST /api/memory-skills/candidates/preview` |
| `POST /api/memory-skills/candidates` |

남은 실제 API 는 **GET 4 + POST 8 = 12 개**이고, 이는 `run_web_app.py:3348`
`handle_get_api` 와 `:3372` `handle_post_api` 의 dispatch 를 그대로 옮긴 것이다.

### 역사 기록은 보존했다

| 보존 대상 | 이유 |
| --- | --- |
| Decision Log L528 "Add deterministic Evaluate Idea" | 2026-07-23 에 실제로 일어난 일 |
| Decision Log 25 개 커밋 해시 | `git cat-file -e` **25/25 EXISTS** 로 검증됨 |
| `b80ed92` 관련 L9 / L60 / L63 | 커밋과 포함 파일 3 개까지 실측 일치 |
| 1 시간 dogfood 실행 기록 | 관측 기록 |
| Edit Before Create 선택 경위 | 과거 판단 서술 |

**제거 사실은 현재 상태 절에만 추가했고 과거 서술은 한 글자도 바꾸지 않았다.**

## R2 — 수치 6 건

전부 `ad59fb1` 에서 재측정했다.

| 위치 | 전 | 후 | 측정 방법 |
| --- | --- | --- | --- |
| tracked Task 범위 | `task-0001`~`task-0005` | **59 건, `task-0001`~`task-0095`** | `git ls-files memory/tasks` |
| Console 탭 | eleven | **8** | `index.html` 의 `data-tab` 전수 |
| Skills 탭 카드 | six | **5** | `skills.json` |
| registry 카드 | six | **5** | `/api/status` `skills` 길이 |
| 로컬 Task 파일 | 28 건, 전부 `DONE` | **82 건 — `DONE 75 / NEEDS_APPROVAL 6 / DOING 1`** | 디스크 전수 |
| `run_web_app.py` | 약 428 KB | **약 176 KB** (180,119 bytes) | `stat` |
| `run_smoke_tests.py` | 약 350 KB | **약 224 KB** (229,310 bytes) | `stat` |

파일 크기는 **대소 관계까지 역전**돼 있었다. 문서는 `run_web_app.py` 가 더 크다고
했지만 실제로는 `run_smoke_tests.py` 가 더 크다. 크기 서술도 함께 고쳤다.

## R3 — 표시 그룹

live `/api/overview` 실측: 표시되는 10 건이 **전부 `metadata_review`** 이고
`Completed` 는 **0** 이다.

`Completed: 10` 을 `Needs metadata review: 10` 으로 고치되, **이 숫자가 R6 버그의
산물이며 버그를 고치면 달라진다는 사실을 문서에 함께 적었다.** 숫자만 바꿔두면
다음 독자가 이것을 정상 상태로 오해한다.

`attention` / manager `blocked` / director `blocked` 는 실측 결과 **여전히 정확해서
건드리지 않았다.**

## R4 — 기준 HEAD

`Last verified` 를 `2026-08-01` 에서 갱신하고, "`b80ed92` 기준, 진행 중 제품 작업
없음" 을 현재 HEAD 기준으로 다시 썼다. `b80ed92` 이후 **72 커밋**, 그중 제품 소스
**41 커밋**이다.

`b80ed92` 자체를 가리키는 역사 서술(L9 / L60 / L63)은 정확하므로 유지했다.

## R5 — 부재 함수 주석

2026-07-31 검증 실패 기록은 **보존**하되, 거기서 지목된
`run_memory_guarded_save_coordinator_self_tests` 가 **현재 저장소에 0 건**이라
그 실패는 재현될 수 없다는 사실을 덧붙였다.

이 환경에서 실측한 결과도 함께 적었다 — self-test `exit 0`, broad smoke `exit 0`.
다만 원문의 주장이 *"current Windows/Codex session"* 으로 한정돼 있고 이 실행 환경은
Codex 가 아니므로, **Codex 환경에서 해소됐다고 단정하지 않았다.**
`docs/master-plan.md` 와 Windows temp ACL 처리 방침은 Owner 결정이라 손대지 않았다.

## 건드리지 않은 것

| 항목 | 상태 |
| --- | --- |
| **R6 Console `metadata_review` 코드 버그** | **수정 금지 지시 — 별도 task** |
| `docs/master-plan.md` | 무변경 |
| 코드 전체 | 무변경 |
| `.gitignore` | 무변경 |
| dogfood 23 건 | sha256 무변경 |
| `jarvis.bat` | 무결성 digest 만 대조, **내용 열람 없음** |
| Owner Decision 항목 (dogfood L507 / master-plan baseline / `jarvis.bat` / Memory Roadmap) | 무변경 |
| 역사 기록 | 무변경 |

## R6 — 별도 task 로 남긴 이유

R3 이 어긋난 **원인은 문서가 아니라 코드**다.

```
run_web_app.py:1468
    for line_index, line in enumerate(text.splitlines()):
        if not line.lstrip().startswith("- "):
            continue          # 파일 전체를 훑는다
```

본문 markdown 목록이 메타데이터로 오인돼 `invalid_text` 가 된다. 실측으로
**디스크 82 건 중 35 건(43%)** 이 `Needs metadata review` 로 떨어진다. dogfood 23 건은
본문 목록이 없어 전부 valid 이고, 실질 기록만 탈락한다.

이것은 **이미 진단된 버그의 미수정 인스턴스**다.

```
task_file_writer.py:468
# task-0054: metadata is the header block, not "every line starting with -".
```

task-0054(`38b9027`)가 intake writer 를 header block 으로 한정했는데 **Console 의
Actionable Task View reader 에는 같은 수정이 적용되지 않았다.**

이번 지시가 명시적으로 수정을 금지했으므로 코드는 손대지 않았다.
이 기록 파일 자체도 본문에 목록이 있어 같은 이유로 `metadata_review` 로 분류된다.

## 검증

| 검증 | 결과 |
| --- | --- |
| canonical (이 기록) | PASS |
| canonical 전수 | fresh-clone 60/60 · disk 83/83 |
| `check_no_secrets --self-test` | PASS |
| handoff 내 문서 링크 실재 | 전건 확인 |
| `git diff --check` | clean |
| Console self-test | exit 0 |
| Console broad smoke | exit 0 |
