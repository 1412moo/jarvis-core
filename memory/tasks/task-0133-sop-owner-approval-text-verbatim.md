# task-0133-sop-owner-approval-text-verbatim

- id: `task-0133-sop-owner-approval-text-verbatim`
- title: `Multi-Agent SOP 보강 — Owner 승인 조건 원문 기록, 충돌 시 구현 전 질문, Reviewer 원문 대조`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-09-17 12:01 UTC`
- updated_at: `2026-09-17 12:01 UTC`
- summary: `task-0132 에서 Owner 가 승인 메시지로 제외한 Roadmap 변경이 Reviewer PASS 와 QA PASS 를 받은 candidate 에 들어 있었고 Owner 가 직접 찾았다. Reviewer 와 QA 가 받은 계약이 Owner 승인 원문이 아니라 Manager 요약이었고 그 요약이 원문과 달랐다. SOP 3 절 Manager 에 승인 조건 원문 인용과 충돌 시 구현 전 질문을, Reviewer 에 원문 대조를, 6 절에 원문 충돌이 기존 gate_safety_conflict 의 사례임을 추가한다. validator, agent 정의, budget, candidate 규칙, 기존 task, Console 문서는 무변경. DONE 은 Reviewer/QA 후 Owner 가 Console Complete 로 결정한다.`
- source_command: `Owner 가 승인한 task-0133 SOP 보강 work package 지시`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `73497fb9a5a8567f5088f51c9b3588cec22a89d4` |
| 작업 전 상태 | tracked 수정 없음, untracked `jarvis.bat` 만 |
| validator | `python -B scripts/validate_multi_agent_sop.py` → `status=PASS`, `negative_failures=0` |

## 무엇이 문제였나

task-0132 에서 일어난 순서다.

1. Manager 제안서는 handoff `:504` (Roadmap 4 행) 갱신을 범위에 넣었다.
2. Owner 승인 메시지는 "진행 범위는 제안서 그대로 유지하세요" 와 함께 "오래된 task 정리와 Roadmap 갱신도 하지 마세요." 를 담았다. 두 조건은 Roadmap 4 행에서 충돌한다.
3. Manager 는 충돌을 묻지 않고 task 기록에 "오래된 task 정리와 Roadmap 전반 갱신은 하지 않는다" 로 요약했다.
4. Manager 가 Reviewer 에게 준 계약은 Roadmap 4 행을 "explicitly listed in the approved proposal" 로 설명했고 Reviewer 는 PASS, QA 도 같은 계약으로 PASS 였다.
5. Owner 가 최종 보고를 보고 제외 위반을 찾았고 repair 1 회와 fresh Reviewer/QA 가 필요했다.

Reviewer 는 받은 계약에 대해서는 정확했다. 계약의 출처가 원문이 아니라 요약이었던 것이 원인이다.
현재 SOP 에는 승인 조건을 원문으로 남기는 규칙도, 원문 조건끼리 또는 원문과 제안서가 충돌할 때
구현 전에 멈추는 규칙도, Reviewer 가 원문을 받는 규칙도 없다.

## Owner 승인 원문

아래는 Owner 메시지를 요약하지 않고 옮긴 것이다. 이 task 부터 새 조항을 스스로 적용한다.

승인 메시지:

```text
Owner 결정

1. jarvis-console workstream 밖의 SOP 보강 진행: 승인
   * 이번 작업은 제품 코드 변경이 아니라 개발 운영 절차(SOP) 보강이므로 별도 work package로 진행합니다.
   * Console workstream 자체의 범위나 우선순위를 변경하는 것으로 해석하지 않습니다.
2. 이번 범위: 제안서 6번 그대로 승인
   * `scripts/validate_multi_agent_sop.py` 수정 제외
   * `.codex/agents/*.toml`, `.claude/agents/reviewer.md` 수정 제외
   * task-0131 결과 기록 commit 취급을 일반 SOP로 확대 금지
   * repair/retry budget, candidate 무효화 규칙 변경 금지
   * task-0132의 기존 이력 서술 수정 금지
   * Console / master-plan / handoff / Roadmap / 기존 task 수정 금지
3. 추가 조건
   * task-0133 하나만 생성합니다.
   * SOP 문서의 실제 변경만 candidate에 포함합니다.
   * Reviewer에게는 Manager 요약 + Owner 승인 원문을 모두 전달합니다.
   * 승인 원문과 제안서가 충돌하는 경우, 구현을 진행하지 않고 Owner에게 bounded question을 올립니다.
   * 기존 `gate_safety_conflict`를 사용하고 새 gate는 만들지 않습니다.
   * 테스트 후 candidate checkpoint commit까지 진행합니다.
   * push는 가능하면 작업 단위 종료 후, merge는 별도 검토 후 진행합니다.
   * `jarvis.bat`는 계속 완전히 무시합니다.
```

구현 전 bounded question 과 Owner 답 (원문 조건 충돌 2 건):

```text
Q1. 승인 원문의 'SOP 문서의 실제 변경만 candidate에 포함합니다'와 제안서의 'diff 범위는 SOP 문서와 task-0133 기록 2개 파일'이 부딪혀요. task-0133 기록을 어디에 둘까요?
A1. candidate에 함께 (Recommended)
Q2. 'push는 가능하면 작업 단위 종료 후, merge는 별도 검토 후'를 어떻게 이해할까요? 지금 작업은 main 브랜치에 직접 commit되고 있어서 merge 단계가 없어요.
A2. 이번엔 push 안 함 (Recommended)
```

## Manager 요약 (원문 해석)

| # | 조건 | 원문 근거 |
| --- | --- | --- |
| 1 | 변경 파일은 `docs/jarvis-multi-agent-sop-v0.1.md` 와 이 기록 두 개 | 승인 2, 3 "task-0133 하나만", A1 |
| 2 | SOP 추가 내용: §3 Manager 원문 인용·충돌 시 구현 전 질문, §3 Reviewer 원문 대조, §6 기존 `gate_safety_conflict` 사례 명시 | 제안서 5, 승인 2 "제안서 6번 그대로", 승인 3 새 gate 금지 |
| 3 | validator, `.codex/agents/*.toml`, `.claude/agents/reviewer.md` 무변경 | 승인 2 |
| 4 | task-0131 결과 기록 commit 취급 일반화 금지, budget·candidate 무효화 규칙 무변경 | 승인 2 |
| 5 | task-0132 이력, Console, master-plan, handoff, Roadmap, 기존 task 무변경 | 승인 2 |
| 6 | §6 gate 목록 줄 자체는 validator 필수 문구이므로 수정하지 않고 사례 설명만 덧붙인다 | 승인 3 새 gate 금지, 승인 2 validator 무변경 |
| 7 | candidate checkpoint commit 까지. push 하지 않음 | 승인 3, A2 |
| 8 | `jarvis.bat` 무시 | 승인 3 |

## Manager assignment

| 역할 | assignment |
| --- | --- |
| Implementer | 위 SOP 문서 조항 추가와 이 기록. candidate local commit 1 개 |
| Reviewer | candidate full hash 에 고정, 두 파일 scope, strict read-only. Manager 요약과 위 Owner 승인 원문을 모두 받는다 |
| QA | Reviewer PASS 후 같은 candidate 에서 validator, `git diff --check`, diff 범위, Console smoke suite |
| Docs | 이 package 자체가 문서 변경. 별도 Docs 실행 `not_required` |
| 완료 | Reviewer/QA PASS 후에도 `DOING`. `DOING → DONE` 은 Owner 가 Console 에서 결정 |

## 무엇을 바꿨나

### `docs/jarvis-multi-agent-sop-v0.1.md` (+13 −0)

| 위치 | 추가 |
| --- | --- |
| §3 Manager (3 항목) | 승인 메시지의 포함·제외 조건을 task 기록에 원문 그대로 인용하고 해석은 따로 적는다. 원문 조건끼리 또는 원문과 제안서가 충돌하면 구현 전에 충돌 조건을 인용한 bounded question 을 Director 에게 escalation 해 Owner 결정을 받고 질문과 답도 원문으로 남긴다. Reviewer assignment 에 Manager 요약과 Owner 승인 원문을 함께 전달한다 |
| §3 Reviewer (1 항목) | Manager 요약과 승인 원문을 함께 받고 diff 범위는 원문 기준으로 대조하며, 요약이 원문과 다르면 그 차이를 finding 으로 보고한다 |
| §6 (목록 뒤 1 문단) | 승인 원문 충돌은 기존 `gate_safety_conflict` 에 해당하고 별도 gate 없이 구현 전 §3 Manager bounded question 을 기존 경로대로 Manager → Director 로 escalation 해 처리한다 |

기존 줄은 한 줄도 바꾸거나 지우지 않았다. §6 gate 목록 문구는 validator 필수 문구라 그대로 두었다.

## 검증 (Implementer 보고, QA 재현 대상)

| # | 항목 | 결과 |
| --- | --- | --- |
| 1 | `python -B scripts/validate_multi_agent_sop.py` | `negative_checks=28`, `negative_failures=0`, `status=PASS` |
| 2 | `git diff --check` | PASS |
| 3 | diff 범위 | `docs/jarvis-multi-agent-sop-v0.1.md`, 이 기록 2 파일뿐 |
| 4 | Console smoke suite | self-test passed, smoke tests passed, exit 0 |

구현 중 한 번 validator 가 `status=FAIL` 이었다. §6 문단 첫 초안이 gate 문구
"기존 안전 계약과 승인된 요구의 충돌" 을 그대로 반복해, gate 줄을 지우는 negative
self-test(`gate_safety_conflict_removed`)가 반복된 문구 때문에 실패를 감지하지 못했다.
문단이 gate 문구를 반복하지 않고 `gate_safety_conflict` 이름으로 가리키도록 고쳐 PASS 가 됐다.
candidate 전의 Implementer 자체 수정이며 repair 가 아니다.

## Repair 이력

retry_budget=1, retry_count=0, repair_budget=1, repair_count=1

| # | 원인 | 조치 |
| --- | --- | --- |
| 1 | Reviewer minor 2 건: 첫 candidate `9c6e4b928b21ea0fa1b529c7f0c1f9504bf8cbf4` 에서 (a) 새 §3 Manager 조항과 §6 문단이 Manager 가 Owner 에게 직접 묻는 것처럼 읽혀 기존 Manager → Director → Owner escalation 경로(§3 Director, §6)와 어긋났다. (b) 이 기록의 Owner 답 인용 블록에 A1 과 Q2 사이 빈 줄이 있어 전달된 원문과 공백이 달랐다. 세 번째 minor 는 task-0132 이력 서술을 Reviewer scope 로 확인할 수 없다는 제한 보고였다 | (a) §3 Manager 조항과 §6 문단을 "Director 에게 escalation 해 Owner 결정을 받는다" 로 정정, (b) 빈 줄 제거. SOP diff 는 +13. 세 번째 항목은 파일을 바꾸지 않고 다음 Reviewer 에게 task-0132 기록과 handoff 를 참조 scope 로 준다. 새 candidate 에 fresh Reviewer → QA |

## 바꾸지 않은 것

- `scripts/validate_multi_agent_sop.py`, `.codex/agents/*.toml`, `.claude/agents/reviewer.md`
- repair/retry budget, candidate 무효화 규칙(§4, §5)
- task-0131 결과 기록 commit 취급의 일반화
- task-0132 기록, 기존 task, Console 코드, master-plan, handoff, Roadmap
- `jarvis.bat`
