# task-0131-console-record-evidence-empty-input-guidance

- id: `task-0131-console-record-evidence-empty-input-guidance`
- title: `Console Record Evidence 빈 입력이면 서버 요청 없이 안내 표시`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-17 09:05 UTC`
- updated_at: `2026-09-17 10:26 UTC`
- summary: `evidence 입력이 비었거나 공백뿐일 때 Record Evidence 가 서버까지 가서 completion_evidence_invalid_value 코드를 Complete Preview 아래에 띄워 Owner 가 Complete Preview 오류로 오해했다. previewCompletionEvidence 가 trim 후 빈 값이면 요청 없이 Record Evidence 안내를 표시하고 기존 Evidence Preview 의 token confirmation taskId 를 비운다. 서버 1–500 자 검증, Complete Preview, task-0130 기능, 전이와 Confirm 은 무변경. DONE 은 Reviewer/QA 후 Owner 가 Console Complete 로 결정한다.`
- completion_evidence: `candidate 5b9a774 — Reviewer PASS, QA PASS, smoke exit 0, browser dogfooding PASS`
- source_command: `Owner 가 승인한 work package "Console Record Evidence: 빈 입력이면 서버 요청 없이 알아볼 수 있는 안내를 표시" task-0131 구현 지시`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `991511fc2ad3a6621829827acba39dafd4d4b5bc` |
| 작업 전 상태 | tracked 수정 없음, untracked `jarvis.bat` 만 |
| 근거 | task-0130 Owner dogfooding 중 발생한 오류와 read-only 조사 |

## 무엇이 문제였나

task-0130 Owner dogfooding 에서 Complete Preview 를 연 화면 아래에
`Completion evidence preview failed: completion_evidence_invalid_value` 가 보였다.
read-only 조사에서 이 문구가 나오는 경로는 하나였다. `.preview-completion-evidence`
(Record Evidence) 클릭 → `previewCompletionEvidence` 가 입력값을 그대로
`/api/completion-evidence/preview` 로 보냄 → `normalize_completion_evidence` 가 빈 값을
거부 → catch 가 서버 코드를 카드 안 evidence 결과 영역에 표시. 그 영역은 transition
결과 영역 바로 아래라 Complete Preview 의 오류처럼 보였다. Complete Task 만 누른
재현에서는 오류가 없었다. 결함은 아니지만 Owner 가 원인을 오해했고 조사 1 회가 필요했다.

같은 앱의 `suggestSkill` 은 이미 빈 입력이면 요청 없이
`Enter a goal before asking for a suggestion.` 을 표시하고 반환한다.

## Owner 결정 (승인 시 확정)

| # | 결정 |
| --- | --- |
| 1 | 빈/공백 evidence 는 서버 요청 없이 클라이언트에서 안내한다 |
| 2 | 안내 문구는 `Enter completion evidence before Record Evidence. Nothing was sent or recorded.` |
| 3 | 빈 입력 시 기존 Evidence Preview 의 token / confirmation / taskId 를 초기화한다 |
| 4 | 서버의 기존 1–500 자 검증은 변경하지 않는다 |
| 5 | Complete Preview, task-0130 기능, 전이/Confirm 동작은 변경하지 않는다 |
| 6 | 완료 후 Owner 가 Console 에서 직접 Complete 한다 |

제외: 서버 검증·오류 코드 변경, 그 밖의 잘못된 값 클라이언트 사전 검사, 버튼 disabled
또는 input 이벤트 토글, 카드 배치·결과 영역 분리·스타일, 오류 코드 전반 문구화,
다른 task 기록.

## Manager assignment

| 역할 | assignment |
| --- | --- |
| Implementer | `web/app.js` `previewCompletionEvidence`, `run_smoke_tests.py`, `README.md`, 이 기록. candidate local commit 1 개 |
| Reviewer | candidate full hash 에 고정, 위 4 파일 scope, strict read-only |
| QA | Reviewer PASS 후 같은 candidate 에서 smoke suite 와 mutation 재현 |
| Docs | README 한 문장으로 충족. 별도 Docs 실행 `not_required` |
| 완료 | Reviewer/QA PASS 후에도 `DOING`. evidence 기록과 `DOING → DONE` 은 Owner 가 Console 에서 결정 |

## 무엇을 바꿨나

| 파일 | 변경 |
| --- | --- |
| `apps/jarvis-console/web/app.js` | 상수 `COMPLETION_EVIDENCE_EMPTY_MESSAGE` 추가. `previewCompletionEvidence` 에서 입력 `trim()` 이 비면 `completionEvidenceBusy` 설정과 fetch 전에 token / confirmation / taskId 를 비우고, 그 task 의 evidence 결과 영역에 `Record Evidence:` 제목과 escape 된 안내를, 상태 줄에 같은 안내를 표시한 뒤 반환 |
| `apps/jarvis-console/README.md` | Record Completion Evidence 절에 빈 입력은 전송하지 않고 안내·Preview 초기화만 하며 서버가 받은 값의 검증자로 남는다는 문장 |
| `apps/jarvis-console/run_smoke_tests.py` | 아래 테스트 |

`run_web_app.py`, 서버 검증·오류 코드, Record Evidence confirm, Complete Preview,
전이, 카드 렌더러, 버튼 상태는 손대지 않았다.

JS `trim()` 이 제거하는 문자만으로 된 입력은 서버도 받지 않는다 (Implementer 보고, QA 재현 대상). Zs 공백은 서버
정규화에서 빈 값이 되어 거부되고, `\t` `\n` `\v` `\f` `\r` (Cc), `U+2028` (Zl),
`U+2029` (Zp), `U+FEFF` (Cf) 는 서버가 문자 자체를 거부한다. 25 개 문자 각각을 3 회
반복한 값으로 `normalize_completion_evidence` 가 전부 `None` 인 것을 확인했다. 따라서
이 안내가 서버가 수락했을 값을 막는 경우는 없다.

## 테스트

`_test_completion_evidence_vertical_slice` 에 추가했다.

| # | 계약 |
| --- | --- |
| 1 | 서버 `preview_completion_evidence` 는 `""` 와 `"   "` 에 여전히 400 `completion_evidence_invalid_value` |
| 2 | 안내 상수 문구가 정확히 일치 |
| 3 | 빈 입력 확인이 한 번 있고 `completionEvidenceBusy = true;` 와 preview fetch 보다 앞 |
| 4 | 확인 블록 안에 fetch 가 없고 `return` 으로 끝남 |
| 5 | 확인 블록이 token / confirmation / taskId 를 비움 |
| 6 | 확인 블록이 `escapeHtml(COMPLETION_EVIDENCE_EMPTY_MESSAGE)`, 상태 줄 안내, `Record Evidence:` 제목을 사용 |

## mutation probe — 7/7 (Implementer 보고, QA 재현 대상)

| mutation | 결과 |
| --- | --- |
| M1 확인 제거 (`if (false)`) | CAUGHT |
| M2 `return` 제거로 fetch 까지 진행 | CAUGHT |
| M3 token 초기화 제거 | CAUGHT |
| M4 안내 문구 변경 | CAUGHT |
| M5 서버가 빈 값 수락 | CAUGHT |
| M6 안내 escape 제거 | CAUGHT |
| M7 `trim()` 없이 확인 | CAUGHT |

원본 bytes 를 보관해 하나씩 바꾸고 전체 smoke 후 복원했다. 복원 전후 diff digest 동일.

## 결과 (Implementer 보고, QA 재현 대상)

- `python -B apps/jarvis-console/run_smoke_tests.py` → self-test passed, smoke tests passed, exit 0
- fixture 디렉터리 잔존 없음

## Repair 이력

retry_budget=1, retry_count=0, repair_budget=3 (Owner 가 2 로, 다시 3 으로 증액), repair_count=3

| # | 원인 | 조치 |
| --- | --- | --- |
| 1 | Reviewer minor: 첫 candidate `08099bcfc725ec744e9273924aa6727c77ed975f` 에서 25 문자 서버 거부 확인 문단이 Implementer 보고 표기 없이 확인된 사실처럼 적혔다 | 그 문단에 Implementer 보고, QA 재현 대상 표기. 코드·테스트 무변경. 새 candidate 에 fresh Reviewer → QA |
| 2 | Reviewer minor: candidate `7058217795c2032d07de6d4c0af00b48518d1b63` 에서 guard_block 을 `"\n    return;\n"` 로 자르는 테스트가 CRLF checkout 에서 깨질 수 있다고 지적. `Path.read_text` 가 이미 줄바꿈을 변환해 재현되지 않았지만(디스크 CRLF 2519, 읽은 텍스트 CR 0), repair budget 1 소진으로 Owner 에게 escalation. Owner 가 repair budget 을 2 로 증액하고 반영을 결정 | 테스트에서 app.js 를 읽은 직후 `.replace("\r\n", "\n")` 로 명시 정규화하고 상수 assertion 의 중복 replace 제거. 구현 코드 무변경. smoke exit 0, mutation 7/7 재확인(Implementer 보고). 새 candidate 에 fresh Reviewer → QA |
| 3 | Reviewer minor: candidate `7052cbb8a290eb5b65b4288bc865933b57f67ec5` 에서 이 표 2 행의 이스케이프 문자가 기록 스크립트 때문에 실제 줄바꿈으로 들어가 표가 깨졌다 (실제 결함). repair budget 2 소진으로 Owner 에게 escalation. Owner 가 repair budget 을 3 으로 증액하고 2 행만 수정하도록 결정 | Edit 도구로 2 행만 한 줄로 다시 쓰고 이스케이프를 문자 그대로 기록. staged blob 에서 2 행에 CR/LF 가 없음을 확인. 코드·테스트·README 무변경. 새 candidate 에 fresh Reviewer → QA |

## 검증 결과

최종 검증 candidate 는 **`5b9a7744081c26e28993ebc6af6124d422647c9c`** 다. 아래 결과는 모두 이 정확한 hash 에 묶여 있다.

| 단계 | 결과 | 근거 |
| --- | --- | --- |
| Reviewer (fresh) | **PASS**, findings 0 | 허용 명령만 사용. 계약 범위, run_web_app.py 무변경, guard 가 서버가 수락할 값을 막지 않음, XSS, busy flag, 2 행 형식 확인 |
| QA | **PASS** | HEAD 와 candidate 일치, status `?? jarvis.bat` 만 |
| QA smoke | exit 0 | `Jarvis Console browser shell self-test passed`, `Jarvis Console smoke tests passed` |
| QA mutation | 7/7 CAUGHT | M1~M7 전부 rc=1, 복원 후 `git diff --quiet` exit 0, fixture 잔존 없음 |
| QA 브라우저 | PASS | 포트 8791 Console 에서 task-0031 카드의 Record Evidence 를 빈 입력, 공백 3 개로 각각 클릭. `/api/completion-evidence/preview` 요청 0 건, 카드와 상태 줄에 안내 문구 표시, Confirm 없음. task-0031 파일 무변경, 서버 종료 |
| task 상태 | `DOING` | candidate 기준 |

위 표에서 앞선 절의 "Implementer 보고, QA 재현 대상" 표기 항목(smoke exit 0, mutation 7/7, 25 문자 서버 거부 결론)은 QA 가 smoke 와 mutation 을 재현했다. 25 문자 개별 확인은 QA 가 따로 재현하지 않았고, Reviewer 가 `normalize_completion_evidence` 코드와 대조해 결론이 맞다고 판단했다.

## 이 기록 commit 의 성격

이 절과 위 검증 결과 표, Repair 이력 3 행, budget 줄은 검증된 candidate
`5b9a7744081c26e28993ebc6af6124d422647c9c` **위에 쌓은 별도 evidence 기록 commit** 으로 추가됐다.

| 항목 | 내용 |
| --- | --- |
| 변경 파일 | 이 task 기록 한 개뿐 |
| 성격 | 검증 결과를 남기는 문서 기록. 새 코드 candidate 가 아니다 |
| 앞선 Reviewer/QA PASS | 무효화하지 않는다. 검증 대상은 여전히 `5b9a774…` 이며 코드·테스트·README 는 이 commit 에서 바뀌지 않는다 |
| 근거 | Owner 결정 (i). SOP §4 규칙 5·6 은 tracked file 이 바뀌는 repair 또는 Docs sync 가 candidate 를 바꾸면 기존 evidence 를 무효로 보지만, 검증 결과를 그 candidate 에 기록하는 행위 자체가 candidate 를 바꾸면 기록이 영원히 끝나지 않는다. 그래서 Owner 는 이 commit 을 §3 Docs 변경처럼 결과를 남기는 문서 기록으로 취급하고, diff 가 이 파일만 바꿨는지와 기록 후 smoke 통과를 확인하는 것으로 대신하도록 결정했다 |
| 완료 | `DOING` 유지. evidence 기록과 `DOING → DONE` 은 Owner 가 Console 에서 결정 |

## 바꾸지 않은 것

- 서버 1–500 자 검증, 오류 코드, 그 밖의 잘못된 값 처리
- 버튼 disabled, input 이벤트, 카드 배치·결과 영역·스타일
- Complete Preview, task-0130 기능, 전이/Confirm, 다른 task 기록
