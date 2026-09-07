# task-0075-console-evaluate-idea-removal

- id: `task-0075-console-evaluate-idea-removal`
- title: `Jarvis Console 축소 3단계 — evaluate_idea 전면 제거 (D6-b)`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-07 08:40 UTC`
- updated_at: `2026-09-07 08:40 UTC`
- summary: `D6-b 결정에 따라 Console 의 evaluate_idea 를 전면 제거했다. 평가 엔진은 research-council 소유였고 Console 은 껍데기였으며, task 초안 절반은 그 결과에 의존해 분리가 불가능했다. CreateLocalTaskRegistry 는 두 레지스트리가 융합돼 있어 512줄에서 147줄로 줄였는데, 손댄 분기는 전부 Voice 경로가 들어가지 않는 곳이라 동작은 동일하다. UI 의 authority lock 이 KEEP 핸들러 여섯을 감싸고 있어 함께 정리했다. 4,745줄 감소, 전 회귀 통과.`
- source_command: `D6-b Owner 결정 — evaluate_idea 전면 REMOVE`

## 기준선

HEAD `5ce75c6` = `origin/main`. Console 6파일 + 이 기록.

## 무엇을 지웠나

두 기능이 한 이름 아래 있었다.

| | 내용 | 처분 근거 |
| --- | --- | --- |
| **(A) Research Council wrapper** | `/api/evaluate-idea` -> `run_research_council()` 호출 | 평가 엔진은 `apps/research-council`(15,432줄) 소유. Console 은 입력 검증 + 결과 투영만 하는 껍데기였다 |
| **(B) idea -> 로컬 task 초안** | draft / preview / invalidate 3라우트, fingerprint idempotency, revision 충돌 검출, draft 상태기계 | Console 고유이나 Owner 가 핵심 lifecycle 범위 밖으로 결정 |

(B)는 `evaluation_fingerprint` 로 (A)의 결과를 재검증하므로 **(A) 없이 존재할 수 없다.**
따라서 부분 제거는 선택지가 아니었고 전면 제거가 유일하게 일관된 처분이었다.

## 🔴 CreateLocalTaskRegistry — KEEP 영역 수술

이 클래스는 **두 레지스트리가 융합**돼 있었다. Voice/Create 경로(task_lifecycle, KEEP)와
Evaluate draft 경로가 상태를 공유했다.

**512줄 -> 147줄.**

| 제거한 메서드 | 줄 |
| --- | --- |
| `store_draft` / `replay_draft_request` / `finalize_draft` / `invalidate_draft` / `_evaluate_token` / `_already_created` | 327 |

**남긴 것**: `__init__`(16) · `_digest`(2) · `_purge_expired_locked`(8) · `_capacity_used_locked`(4) ·
`issue`(29) · `confirm`(79).

상태 수술 4곳은 **모두 Voice/Create 가 진입하지 않는 분기**였다.

| 위치 | 내용 | 동작 영향 |
| --- | --- | --- |
| `_CreateLocalTaskRecord` | `linked_draft_id` / `draft_revision` 필드 | Voice 경로는 항상 `None` |
| `__init__` | `_drafts` / `_draft_request_index` | draft 전용 |
| `_purge_expired_locked` | draft 만료 정리 10줄 | draft 전용 |
| `_capacity_used_locked` | `standalone_records + len(self._drafts)` -> `len(self._records)` | **모든 record 가 이미 standalone** 이라 결과 동일 |
| `confirm` | `linked_draft` 3블록 12줄 | `linked_draft` 가 항상 `None` 이라 죽은 분기 |

`issue` 는 evaluate 참조가 **애초에 0**이었다.

## UI — authority lock 이 KEEP 핸들러를 감싸고 있었다

`evaluateTaskAuthorityLocked` 가 completion-evidence · task-transition · create-local-task
**여섯 핸들러**를 감싸고 있었다. Evaluate Final authority 가 살아 있는 동안 다른 task 쓰기를
막는 상호배제였다. 그 값을 세팅하는 코드가 evaluate 뿐이라 제거 후 **영구히 false** 가
되므로, 가드 6개를 함께 걷어냈다. **항상 false 인 분기를 지운 것이라 동작은 동일하다.**

app.js 함수 34개(1,025줄), `index.html` 의 Research 탭 전체, `styles.css` 의 `.evaluate-*`
규칙을 제거했다.

## 방법

top-level 심볼·상수·메서드·테스트 함수는 **AST 줄 범위**로, 클래스 내부 수술과 라우트는
**정확한 텍스트 블록**으로 잘랐다. JS 는 중괄호 매칭으로 함수 경계를 찾았다. 줄 종결자는
파일별로 감지해 보존했다.

## legacy 테스트 — caller 0 확인 후 제거

`_legacy_test_evaluate_idea_create_task_vertical_slice`(799줄)와
`_legacy_..._client_state_machine`(379줄)은 **정의만 있고 호출부가 없었다.**
`grep` 으로 caller 0 을 확인한 뒤 제거했다 — 이미 죽어 있던 1,178줄이다.

## 검증

| 검증 | 결과 |
| --- | --- |
| `/api/evaluate-idea` 4개 라우트 | 전부 **404** |
| `/api/create-local-task/preview` | 400 (정상 입력 검증) |
| `/api/voice-inbox/prepare` | **200** |
| `/api/status` · `/api/overview` · `/api/skill` · `/api/history` | **200** |
| `jarvis-console` 스모크 + browser shell self-test | **PASS** |
| **`research-council` 스모크** | **PASS** (무변경) |
| **`hermes-manager-pilot` 스모크** | **PASS** (무변경) |
| canonical 전수 | **67/67 PASS** |
| `validate_multi_agent_sop` | `status=PASS` |
| `bot_minimal` self-check | **92/92 PASS** |
| `discord-intake` | **90/90 PASS** |
| `audit-chain` | PASS |
| `buzz-bridge` | failed 0 |
| `discord-nl-intent` | 35/35 PASS |
| `check_no_secrets --self-test` | `status=PASS` |
| `node --check web/app.js` | OK |
| `git diff --check` | clean |
| research-council / hermes 변경 파일 | **0** |

## 줄 수

| 파일 | 전 | 후 | 증감 |
| --- | --- | --- | --- |
| `run_smoke_tests.py` | 7,659 | 5,457 | **-2,202** |
| `run_web_app.py` | 5,819 | 4,495 | **-1,324** |
| `web/app.js` | 3,472 | 2,447 | -1,025 |
| `web/styles.css` | 1,230 | 1,121 | -109 |
| `README.md` | 481 | 423 | -58 |
| `web/index.html` | 213 | 186 | -27 |
| 합계 | 18,874 | 14,129 | **-4,745** |

## 남은 evaluate 참조와 이유

| 잔여 | 이유 |
| --- | --- |
| `run_web_app.py:303` "does not evaluate whether verification evidence exists" | completion evidence 문구. 무관 |
| `run_web_app.py` `_capacity_used_locked` 주석 | 계산이 왜 동일한지 설명 |
| `run_smoke_tests.py` `evaluate_project_registry` 3곳 | **project_control** 소유. 무관 |
| `run_smoke_tests.py:157,184` | `skills.json` 의 `research_council` 항목 문구를 검증한다. **skill_registry 는 D6-c 미결** |
| `README.md:296` "Purpose: evaluate ideas..." | Research Council **앱** 설명 |
| `docs/` 설계 문서 | 역사 기록 |

> `skills.json` 의 `research_council` 항목이 여전히 Evaluate Idea 를 안내한다. 기능이
> 사라졌으므로 정정 대상이지만 **skill_registry 는 이번 범위 밖**이라 D6-c 와 함께 다뤄야
> 한다.

## 이번 단계 비범위

- Research Council 코드 · hermes-manager-pilot — **무변경 확인**
- task_lifecycle(create-local-task preview/confirm) · Voice Inbox · overview_status ·
  project_control · skill_registry · `suggestedActionPanel` — 무변경
- `preview_task_file_write` / `write_task_file` — 무변경
- D6-c — 미결 유지
- `jarvis.bat` — 건드리지 않았다
