# task-0172-structured-self-review-before-candidate

- id: `task-0172-structured-self-review-before-candidate`
- title: `candidate 전 구조화된 self-review: staged diff와 task 기록을 Reviewer 관점으로 1회 읽기 전용 검토`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-19 15:57 UTC`
- updated_at: `2026-10-19 16:38 UTC`
- summary: `task-0170·0171에서 candidate 뒤 Reviewer 지적이 repair 예산을 소진했다. 첫 candidate 전 1회, 읽기 전용 self-reviewer(Read·Grep·Glob만)가 staged diff와 기록을 Reviewer 관점으로 보는 jarvis-self-review Skill과 SOP 3 항목을 더했다. 과거 상태 4개 재현에서 실제 지적 9건 중 7건을 미리 찾았다. Reviewer 지적은 Owner 해석 승인과 예산 증액(1→2) 뒤 repair 2회로 반영했다. push 없음.`
- source_command: `Owner 요청: candidate 전 구조화된 self-review 등록 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `8bb7026c9cd54d007e5719fa27b9a68b03f6a789` (등록 시점 main HEAD = origin/main). Start 때 다시 확인한다 |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat` |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (기본값) |

## Owner 요청 (원문)

```text
이번 추천은 방향이 좋습니다. 저도 candidate 전 구조화된 self-review를 다음 작업으로 진행하는 데 찬성합니다.
task-0171에서 드러난 문제는 단순한 검사 누락이 아니었습니다. 기계적으로 검사할 수 있는 형식 오류는 사전에 잡기 시작했지만, 승인된 범위와 실제 변경 내용이 맞는지, 작업 기록이 최신 상태를 반영하는지 같은 의미적 문제는 candidate를 만든 뒤 Reviewer가 발견했습니다. 이 문제를 candidate 전에 줄이는 것이 다음 단계로 적절합니다.
권장 결정 3가지
1. 실행 방식: (a) 읽기 전용 self-review
권장
Reviewer 관점으로 staged diff와 작업 기록을 검토하되, candidate 커밋은 만들지 않습니다. 기존 Reviewer의 정확한 candidate hash 고정 규칙도 그대로 유지됩니다.
이유: 새로운 임시 커밋이나 ref 개념을 만들 필요 없이 최소 변경으로 검증할 수 있습니다.
2. 수정의 성격: repair가 아닌 사전 수정
SOP §5의 정의에 따라 공식 Reviewer finding이나 QA 실패에 대응하는 수정이 아니라, candidate 생성 전 self-review에서 발견해 고친 수정은 repair 예산에 포함하지 않습니다.
단, 공식 Reviewer가 candidate 이후 새로운 지적을 내면 기존 repair 예산과 승인 규칙을 그대로 적용합니다. self-review를 이유로 repair 예산을 우회하지 않습니다.
3. 실행 횟수와 기록: 1회, 결과 기록

* candidate 생성 전 self-review는 최대 1회 실행합니다.
* 발견 사항과 수정 여부, 최종 결과를 task 기록에 남깁니다.
* 수정 후 task-0171 사전 점검을 다시 통과해야 candidate를 생성할 수 있습니다.
* self-review가 Reviewer 판정을 대신하지 않는다는 점을 SOP에 명시합니다.

추가로 꼭 지킬 조건
과거 task-0170·0171 사례를 재현해 효과를 측정하는 계획도 유지하겠습니다. 특히 단순히 지적을 몇 개 찾았는지만 세지 말고, 다음을 구분해야 합니다.

* 실제 Reviewer 지적 중 candidate 전에 발견한 항목
* self-review가 놓친 항목
* 잘못된 지적 때문에 불필요한 수정이 발생한 항목

이렇게 해야 검토 단계를 하나 더 추가하는 데 그치지 않고, 실제로 repair 예산 소모를 줄이는지 판단할 수 있습니다.
위 세 가지를 승인합니다. 다음 단계는 이 조건으로 task를 등록하고, 구현에 앞서 범위와 검증 계획을 정리하는 것입니다. 기존 Reviewer·QA·repair 예산·Owner 승인 정책은 변경하지 않습니다.
```

## 조사 결과 (read-only, 등록 전 확인)

1. task-0171 기록에 따르면 Reviewer 3회에서 지적 7건이 나왔고 Owner가 repair 예산을 두 번 늘렸다(1→2, 2→3). 기록 문구·결과 누락 3건(F4, G2, H1), Skill·설계 문구 3건(F1, F2, F3), 코드 1건(G1)이다. task-0170 기록에 따르면 첫 Reviewer가 기록 지적 2건(F1 summary 최신성, F2 owned 설명)을 냈다. 모두 candidate 전 staged diff와 기록에서 보이는 내용이었다.
2. G2와 H1은 repair 결과를 기록하는 과정에서 생긴 누락이다(repair가 다음 지적을 낳는 연쇄).
3. task-0171 사전 점검(C1~C5)은 형식만 판정하고 의미(승인 범위 대비 구현, 기록의 최신 단계 반영)는 Reviewer 몫으로 남겼다.
4. 현재 규칙: SOP §3 Implementer "self-review와 결정론적 validation 뒤 명시된 파일만 stage한다", 운영 규칙 §3 "self-review에 actionable finding이 없다". self-review의 방법은 정해져 있지 않다. SOP §5 repair 정의는 "Reviewer finding 또는 QA 실패를 해결하기 위해 tracked source를 바꾸는 correction"이다.
5. Reviewer 정의(`.claude/agents/reviewer.md:10`)는 정확한 candidate commit에만 고정되므로 staged diff 검토에 그대로 쓸 수 없다.
6. SOP validator는 `.codex/agents`의 파일 집합을 정확히 고정하고(`AGENT_SPECS`) `.claude/agents`는 `reviewer.md` 경로만 검사한다. Claude 쪽 읽기 전용 agent 정의 추가는 validator와 충돌하지 않지만 Codex 쪽 짝은 만들 수 없다.

## Owner 결정 (원문 블록의 권장 결정 3가지, 등록 시 승인됨)

| # | 결정 |
| --- | --- |
| A1 | 실행 방식 (a): 읽기 전용 self-review가 staged diff와 task 기록을 Reviewer 관점으로 검토. candidate 커밋을 만들지 않고 Reviewer의 candidate hash 고정 규칙은 그대로 |
| A2 | self-review에서 고친 수정은 repair 예산에 넣지 않음. candidate 뒤 공식 Reviewer 지적에는 기존 예산·승인 규칙 그대로 |
| A3 | candidate 전 최대 1회, 발견·수정 여부·최종 결과를 기록, 수정 뒤 task-0171 사전 점검 재통과, SOP에 "Reviewer 판정을 대신하지 않음" 명시 |

## Start 전에 정할 항목

| # | 결정 | 선택지 | Manager 권고 |
| --- | --- | --- | --- |
| D1 | 읽기 전용을 보장하는 수단 | (a) 새 `.claude/agents/self-reviewer.md`: 도구를 `Read`, `Grep`, `Glob`과 `git diff --cached`·`git show :<path>`·`git status` 형태로 제한 / (b) 기존 범용 agent에 지시문만 전달(도구 제한 없음) | (a). 쓰기 도구가 없어 검토가 파일을 바꿀 수 없다. Codex 표면에는 짝이 없음을 SOP에 적는다 |
| D2 | 호출문 조립 | (a) `jarvis-reviewer-call` Skill에 "self-review 모드" 단계 추가 / (b) 새 Skill `jarvis-self-review` | (b). 기존 Reviewer 호출 Skill의 BLOCKED 규칙·고정 hash 문구와 섞지 않는다 |
| D3 | self-review 결과 기록 형식 | 기록에 "Self-review" 절 하나: 지적 목록, 각 지적의 처리(수정·수정 안 함과 이유), 수정 뒤 사전 점검 결과 | 그대로 |

## 설계 (Start 승인 시)

| # | 내용 |
| --- | --- |
| S1 | 시점: 구현과 결정론적 검증 → 변경 파일과 기록 stage → task-0171 사전 점검 통과 → self-review 1회 → 지적 수정 → 기록에 Self-review 절 → 다시 stage → 사전 점검 재통과 → candidate 커밋 |
| S2 | 입력: `git diff --cached <baseline>`(baseline 이후 커밋 + staged), staged task 기록(Owner 원문, Manager 요약, 범위, 검증 결과), task-0171 사전 점검 출력 |
| S3 | 관점: `reviewer.md`의 검토 항목을 그대로 쓴다. 승인 원문 대비 요약과 diff, 범위(owned·deny), 기록이 현재 단계를 반영하는지(summary, 최신 결과 표, 대체된 요약 행), 설계 대비 구현 범위, 문서와 코드 일치 |
| S4 | 출력: Reviewer와 같은 지적 형식(severity, evidence, impact, minimum_correction). 판정 단어(PASS/FINDINGS)는 쓰지 않고 "self-review 결과"로만 부른다 |
| S5 | 효력: 참고 자료. 공식 Reviewer·QA·repair 예산·§8·승인은 바뀌지 않는다. 고친 것은 repair가 아니다(A2). 수정하지 않기로 한 지적은 이유와 함께 기록하고 그대로 candidate를 만들 수 있다 |
| S6 | 1회 상한: 수정 뒤 self-review를 다시 돌리지 않는다. 사전 점검만 다시 통과하면 된다(A3) |

## Manager 요약

| # | Owner 원문 | Manager 해석 |
| --- | --- | --- |
| M1 | "이번 추천은 방향이 좋습니다." / "저도 candidate 전 구조화된 self-review를 다음 작업으로 진행하는 데 찬성합니다." / "task-0171에서 드러난 문제는 단순한 검사 누락이 아니었습니다." / "기계적으로 검사할 수 있는 형식 오류는 사전에 잡기 시작했지만, 승인된 범위와 실제 변경 내용이 맞는지, 작업 기록이 최신 상태를 반영하는지 같은 의미적 문제는 candidate를 만든 뒤 Reviewer가 발견했습니다." / "이 문제를 candidate 전에 줄이는 것이 다음 단계로 적절합니다." | 대상은 의미 판정(승인 범위 대비 변경, 기록의 최신성). 형식은 task-0171 몫 |
| M2 | "1. 실행 방식: (a) 읽기 전용 self-review" / "Reviewer 관점으로 staged diff와 작업 기록을 검토하되, candidate 커밋은 만들지 않습니다." / "기존 Reviewer의 정확한 candidate hash 고정 규칙도 그대로 유지됩니다." / "이유: 새로운 임시 커밋이나 ref 개념을 만들 필요 없이 최소 변경으로 검증할 수 있습니다." | A1, S2·S3. 임시 commit·ref 없음. 읽기 전용 보장 수단은 D1 |
| M3 | "2. 수정의 성격: repair가 아닌 사전 수정" / "SOP §5의 정의에 따라 공식 Reviewer finding이나 QA 실패에 대응하는 수정이 아니라, candidate 생성 전 self-review에서 발견해 고친 수정은 repair 예산에 포함하지 않습니다." / "단, 공식 Reviewer가 candidate 이후 새로운 지적을 내면 기존 repair 예산과 승인 규칙을 그대로 적용합니다." / "self-review를 이유로 repair 예산을 우회하지 않습니다." | A2, S5 |
| M4 | "3. 실행 횟수와 기록: 1회, 결과 기록" / "candidate 생성 전 self-review는 최대 1회 실행합니다." / "발견 사항과 수정 여부, 최종 결과를 task 기록에 남깁니다." / "수정 후 task-0171 사전 점검을 다시 통과해야 candidate를 생성할 수 있습니다." / "self-review가 Reviewer 판정을 대신하지 않는다는 점을 SOP에 명시합니다." | A3, S1·S6, D3. SOP §3에 명시 |
| M5 | "과거 task-0170·0171 사례를 재현해 효과를 측정하는 계획도 유지하겠습니다." / "특히 단순히 지적을 몇 개 찾았는지만 세지 말고, 다음을 구분해야 합니다." / "실제 Reviewer 지적 중 candidate 전에 발견한 항목" / "self-review가 놓친 항목" / "잘못된 지적 때문에 불필요한 수정이 발생한 항목" / "이렇게 해야 검토 단계를 하나 더 추가하는 데 그치지 않고, 실제로 repair 예산 소모를 줄이는지 판단할 수 있습니다." | 검증 계획 V5~V7: 발견·누락·오지적 세 가지로 나눠 기록 |
| M6 | "위 세 가지를 승인합니다." / "다음 단계는 이 조건으로 task를 등록하고, 구현에 앞서 범위와 검증 계획을 정리하는 것입니다." / "기존 Reviewer·QA·repair 예산·Owner 승인 정책은 변경하지 않습니다." | 등록 시점에는 이 기록(TODO)만 만들었다(Start 승인 요약 행 P1~P6으로 대체). 정책 무변경 |
| P1 | "Owner 결정 — task-0172 Start 및 D1~D3 승인" / "D1 — 읽기 전용 agent" / "`.claude/agents/self-reviewer.md`를 새로 정의합니다." / "파일 읽기·diff 확인 등 검토에 필요한 읽기 전용 도구만 허용하도록 구성합니다." / "실제 실행 환경에서 쓰기 도구가 제한되는지 확인합니다." / "agent 정의의 지시문만으로 제한이 보장된다고 가정하지 마세요." / "읽기 전용을 기술적으로 보장할 수 없다면 self-review 실행 전에 중단하고 보고하세요." / "Codex agent에 짝이 없다는 한계를 task 기록에 명시합니다." | agent 정의의 도구 목록 자체를 읽기 전용으로 두고, 실제 호출에서 쓰기 시도가 거부되는지 확인(V4). 보장 못 하면 멈춤. Codex 짝 없음 기록 |
| P2 | "D2 — 별도 Skill" / "새 Skill `jarvis-self-review`를 만듭니다." / "공식 `jarvis-reviewer-call`과 분리해 기존 Reviewer의 BLOCKED 처리, candidate hash 고정, PASS/FINDINGS 판정 규칙에 영향을 주지 않도록 합니다." / "self-review 결과가 공식 Reviewer 판정을 대신하지 않는다는 점을 명시합니다." | 새 Skill. `jarvis-reviewer-call`·`reviewer.md` 무변경 |
| P3 | "D3 — 기록 형식" / "task 기록에 `Self-review` 절을 둡니다." / "발견 사항, 수정·미수정 여부와 이유, 수정 후 task-0171 사전 점검 결과를 기록합니다." / "self-review는 최대 1회 실행합니다." / "발견 사항을 수정한 뒤 사전 점검을 다시 통과해야 candidate를 생성할 수 있습니다." / "self-review에서 candidate 전에 수정한 사항은 SOP §5 정의에 따라 repair 예산에 포함하지 않습니다." / "공식 Reviewer 이후의 수정은 기존 예산과 승인 규칙을 그대로 적용합니다." | D3, A2·A3 그대로 |
| P4 | "진행 범위와 제한" / "1. Console의 공식 Start 절차로 task-0172를 시작합니다." / "2. 승인된 범위에서 agent 정의, 새 Skill, 필요한 SOP 및 task 기록만 최소한으로 수정합니다." / "3. task-0170·0171의 지정된 candidate 상태를 대상으로 과거 Reviewer 지적의 사전 발견 여부, 놓친 항목, 잘못된 지적을 항목별로 측정합니다." | Console Start, owned 범위만, V5~V7 |
| P5 | "4. V9 중단 조건을 적용합니다." / "발견 항목이 0개이거나 잘못된 지적이 발견 항목보다 많으면 SOP 반영을 완료 처리하지 말고 중단해 보고합니다." / "5. 공식 Reviewer, QA, repair 예산, §8, Owner 승인 정책은 변경하지 않습니다." / "6. 구현 후 기존 validator·smoke 및 관련 검증을 실행하고 결과를 기록합니다." | V9, 정책 무변경, V8 |
| P6 | "7. task-0172를 직접 DONE으로 편집하지 말고 기존 SOP의 Reviewer → QA → checkpoint → Console Complete 절차를 따릅니다." / "8. `jarvis.bat`은 열람·수정·스테이징하지 마세요." / "다른 worktree와 임시 폴더도 건드리지 말고, `git push`는 별도 Owner 승인 없이 하지 마세요." / "승인된 범위를 벗어나는 문제가 생기면 임의로 확장하지 말고 중단해 보고하세요." | 공식 완료 절차, push 없음, 범위 밖이면 멈춤. 8항의 "다른 worktree와 임시 폴더"는 기존에 있던 다른 worktree와 smoke 임시 폴더를 바꾸거나 지우지 말라는 뜻이다(R1, Owner 해석 승인). 이 task가 검증용으로 저장소 밖에 만든 임시 clone과 요청 파일은 분리해 쓰고 검증 뒤 정리한다 |
| R1 | "Owner 결정 — task-0172 Start 승인 8항의 해석 확인" / "해석을 승인합니다." / "Start 승인 8항의 "다른 worktree와 임시 폴더도 건드리지 말고"는 기존에 존재하던 다른 worktree와 smoke 임시 폴더를 변경하거나 삭제하지 말라는 의미로 적용합니다." / "이번 task에서 검증 목적으로 별도 생성한 임시 clone과 요청 파일은 기존 작업 환경과 분리하고, 검증 종료 후 정리하는 것을 허용합니다." / "기존 worktree와 smoke 임시 폴더를 수정·삭제하거나 그 내용을 변경해서는 안 됩니다." / "이 해석과 이번 task의 실제 처리 결과를 task-0172 기록에 남기세요." / "이 승인은 이번 task의 임시 환경 사용에 대한 확인이며, 다른 task의 보호 조건을 포괄적으로 변경하는 승인은 아닙니다." | P6 해석에 반영, 아래 "임시 환경 처리" 절. 이 task에만 적용 |
| R2 | "남은 Reviewer 지적도 처리하세요." / "1. Skill의 `allowed-tools`에서 `Write`를 제거해 self-review agent의 쓰기 권한을 부여하지 마세요." / "2. 저장소 밖 경로 제한이 지시문에만 의존하는 부분은 사실대로 기록하고, 기술적으로 보장되는 권한 제한과 구분하세요." / "3. repair 예산 1회 범위에서 수정한 뒤 task-0171 사전 점검, 새 Reviewer, QA를 진행하세요." / "4. 추가 FINDINGS가 나오면 임의로 repair 예산을 늘리지 말고 중단해 보고하세요." / "`jarvis.bat`은 열람·수정·스테이징하지 마세요." / "기존 worktree와 smoke 임시 폴더를 건드리지 말고, `git push`는 별도 승인 없이 하지 마세요." / "Console Complete를 포함한 기존 SOP를 준수하세요." | repair 1: Skill allowed-tools에서 `Write` 제거, Skill에 보장되는 제한(도구 목록)과 지시문 의존(저장소 밖 경로 등) 구분. 사전 점검 → Reviewer 2 → QA. FINDINGS가 남으면 멈춤 |
| R3 | "Owner 결정: task-0172 repair 예산을 총 2회로 증액합니다." / "현재 repair 1/2이며, 이번 수정이 마지막 repair입니다." / "1. `jarvis-self-review` Skill의 `allowed-tools`에서 `Bash(git diff:*)`를 제거하세요." / "`git diff --output=<파일>`처럼 파일을 쓸 수 있는 경로가 일반 권한 확인 없이 허용되지 않도록 합니다." / "2. Skill과 task 기록에서 기술적으로 보장되는 제한과 지시문에만 의존하는 제한을 구분해 기록하세요." / "`git diff` 출력 옵션처럼 파일 쓰기가 가능한 사례도 명시합니다." / "3. 코드와 SOP는 수정하지 마세요." / "이번 repair는 Skill과 필요한 task 기록만 대상으로 합니다." | repair 2: Skill allowed-tools에서 `Bash(git diff:*)` 제거, Skill과 아래 "제한 구분" 절에 보장·지시문 의존·남은 쓰기 경로를 적음. SOP·agent 무변경 |
| R4 | "task-0171 사전 점검을 통과시킵니다." / "같은 candidate의 Reviewer 재검토가 아니라, 수정 내용을 반영한 새 candidate를 만들고 새 Reviewer 검토를 진행합니다." / "Reviewer PASS 후 QA를 수행하고 기존 SOP에 따라 checkpoint 및 Console Complete를 진행합니다." / "추가 FINDINGS가 나오면 예산을 더 늘리거나 SOP §8로 임의 수용하지 말고 중단해 보고하세요." / "`self_deviations`가 있는 검토는 SOP §5에 따라 유효성을 판단하세요." / "무효 검토의 허용된 재검토 절차와 repair 예산을 혼동하지 마세요." | 새 candidate → Reviewer 3 → PASS면 QA → checkpoint → Console Complete. FINDINGS면 멈춤. Reviewer 2 유효성 판단은 아래 Reviewer 2 절 |
| R5 | "`jarvis.bat`은 열람·수정·스테이징하지 마세요." / "기존 worktree 4개와 smoke 임시 폴더 47개를 변경하거나 삭제하지 마세요." / "이번 task에서 만든 scratchpad 파일은 QA 증거로 보존하고, QA 완료 후 이번 task가 생성한 파일만 정리하세요." / "`git push`는 하지 마세요." / "task 상태를 직접 DONE으로 편집하지 말고 Console의 공식 Complete 절차를 따르세요." | 보호 대상 무접촉, scratchpad 파일은 QA 뒤 이 task가 만든 것만 삭제, push 없음 |

## Start 승인 (원문)

```text
Owner 결정 — task-0172 Start 및 D1~D3 승인
D1 — 읽기 전용 agent

* `.claude/agents/self-reviewer.md`를 새로 정의합니다.
* 파일 읽기·diff 확인 등 검토에 필요한 읽기 전용 도구만 허용하도록 구성합니다.
* 실제 실행 환경에서 쓰기 도구가 제한되는지 확인합니다. agent 정의의 지시문만으로 제한이 보장된다고 가정하지 마세요.
* 읽기 전용을 기술적으로 보장할 수 없다면 self-review 실행 전에 중단하고 보고하세요.
* Codex agent에 짝이 없다는 한계를 task 기록에 명시합니다.

D2 — 별도 Skill

* 새 Skill `jarvis-self-review`를 만듭니다.
* 공식 `jarvis-reviewer-call`과 분리해 기존 Reviewer의 BLOCKED 처리, candidate hash 고정, PASS/FINDINGS 판정 규칙에 영향을 주지 않도록 합니다.
* self-review 결과가 공식 Reviewer 판정을 대신하지 않는다는 점을 명시합니다.

D3 — 기록 형식

* task 기록에 `Self-review` 절을 둡니다.
* 발견 사항, 수정·미수정 여부와 이유, 수정 후 task-0171 사전 점검 결과를 기록합니다.
* self-review는 최대 1회 실행합니다. 발견 사항을 수정한 뒤 사전 점검을 다시 통과해야 candidate를 생성할 수 있습니다.
* self-review에서 candidate 전에 수정한 사항은 SOP §5 정의에 따라 repair 예산에 포함하지 않습니다. 공식 Reviewer 이후의 수정은 기존 예산과 승인 규칙을 그대로 적용합니다.

진행 범위와 제한

1. Console의 공식 Start 절차로 task-0172를 시작합니다.
2. 승인된 범위에서 agent 정의, 새 Skill, 필요한 SOP 및 task 기록만 최소한으로 수정합니다.
3. task-0170·0171의 지정된 candidate 상태를 대상으로 과거 Reviewer 지적의 사전 발견 여부, 놓친 항목, 잘못된 지적을 항목별로 측정합니다.
4. V9 중단 조건을 적용합니다. 발견 항목이 0개이거나 잘못된 지적이 발견 항목보다 많으면 SOP 반영을 완료 처리하지 말고 중단해 보고합니다.
5. 공식 Reviewer, QA, repair 예산, §8, Owner 승인 정책은 변경하지 않습니다.
6. 구현 후 기존 validator·smoke 및 관련 검증을 실행하고 결과를 기록합니다.
7. task-0172를 직접 DONE으로 편집하지 말고 기존 SOP의 Reviewer → QA → checkpoint → Console Complete 절차를 따릅니다.
8. `jarvis.bat`은 열람·수정·스테이징하지 마세요. 다른 worktree와 임시 폴더도 건드리지 말고, `git push`는 별도 Owner 승인 없이 하지 마세요.

승인된 범위를 벗어나는 문제가 생기면 임의로 확장하지 말고 중단해 보고하세요.
```

Start 전 확인(2026-10-19 16:11 UTC): main HEAD `8bb7026c9cd54d007e5719fa27b9a68b03f6a789`(기준선과 같음), tracked 변경 없음, untracked `jarvis.bat`과 이 기록.

## 범위 (Start 승인 시)

| 구분 | 경로 |
| --- | --- |
| owned | `.claude/agents/self-reviewer.md`(신규, D1 (a)), `.claude/skills/jarvis-self-review/SKILL.md`(신규, D2 (b)), `docs/jarvis-multi-agent-sop-v0.1.md`(§3 Implementer에 self-review 항목 1개 추가), 이 기록 |
| deny | `jarvis.bat`, `.env`, `.claude/agents/reviewer.md`, `.codex/agents/*.toml`, `scripts/validate_multi_agent_sop.py`(대조 값이 바뀌지 않으면), `scripts/check_task_record.py`, `.claude/skills/jarvis-reviewer-call/SKILL.md`, 다른 task 기록, `docs/master-plan.md`(Complete 뒤) |

비범위: Reviewer 정의·판정, QA, repair 예산, SOP §5·§8, Owner 승인, Worker 파이프라인, Codex agent 추가, push.

## 검증 계획

| # | 검사 | 기대 |
| --- | --- | --- |
| V1 | agent 정의 | 허용 도구에 쓰기 도구(Edit, Write, NotebookEdit)와 임의 Bash가 없다(정의 파일 대조) |
| V2 | Skill | 호출문이 Owner 원문·Manager 요약·범위·baseline·사전 점검 출력을 담고, 출력에 PASS/FINDINGS를 쓰지 않으며, 1회 상한과 "Reviewer 판정 대신 아님"을 적는다 |
| V3 | SOP | §3 Implementer에 순서(사전 점검 → self-review 1회 → 수정 → 사전 점검 재통과 → candidate), A2(repair 아님, 공식 Reviewer 지적에는 기존 예산), "Reviewer 판정을 대신하지 않음", Codex 표면 짝 없음이 있다. validator PASS |
| V4 | 실행 확인 | 임시 clone에서 self-review가 파일을 바꾸지 않는다(실행 전후 `git status`·파일 해시 동일) |
| V5 | 재현: 발견 | task-0170 candidate 1(`0fc1236`) 직전 staged 상태와 task-0171 candidate 1(`1c74364`) 직전 staged 상태에서 self-review를 1회씩 돌려, 실제 Reviewer 지적(0170 F1·F2, 0171 F1~F4) 중 candidate 전에 찾은 항목을 센다. 같은 방법으로 0171 repair 1·2 직전 상태(G1·G2, H1)도 돌린다 |
| V6 | 재현: 누락 | 같은 실행에서 self-review가 놓친 실제 지적을 항목별로 적는다 |
| V7 | 재현: 오지적 | 실제 Reviewer가 내지 않았고 고칠 필요도 없는 지적, 그대로 고쳤다면 불필요한 수정이 됐을 항목을 항목별로 적는다(판단 근거 포함) |
| V8 | 회귀 | SOP validator, discord-intake smoke, Console smoke, `check_task_record --self-test`, `git diff --check`, `check_no_secrets` |
| V9 | 판정 기준 | V5~V7 결과를 그대로 기록한다. 발견이 0이거나 오지적이 발견보다 많으면 Owner에게 보고하고 SOP 반영 전에 멈춘다 |

## 구현

| 파일 | 변경 |
| --- | --- |
| `.claude/agents/self-reviewer.md` | 신규. `tools: Read, Grep, Glob`(쓰기·셸 도구 없음). 입력은 Manager가 붙인 staged diff 텍스트, 기록 경로, baseline, 사전 점검 출력. `reviewer.md`의 검토 관점(승인 원문 대 요약·diff·범위, 기록의 현재 단계 반영, 설계 대비 구현, 문서·코드 일치)을 staged 상태에 적용. 사전 점검이 이미 보는 항목은 반복하지 않음. 출력은 `self_review_findings` 목록과 `files_read`, 판정어(verdict·PASS·FINDINGS·BLOCKED)를 쓰지 않음 |
| `.claude/skills/jarvis-self-review/SKILL.md` | 신규. 전제 조건(사전 점검 종료 0, 작업 트리 = index, `## Self-review` 절이 아직 없음 = task당 1회), 요청 형식, 실행 `claude -p --agent self-reviewer --tools Read,Grep,Glob --output-format json`, 결과 처리(기록, 다시 stage, 사전 점검 재통과 뒤 candidate). 판정을 내리지 않고 Reviewer·`jarvis-reviewer-call`을 대신하지 않으며 repair 예산·§8·승인을 바꾸지 않음 |
| `docs/jarvis-multi-agent-sop-v0.1.md` | §3 Implementer에 7줄: 수동 SOP task는 첫 candidate 전에 한 번, 순서, 기록, repair 아님(A2), Reviewer 판정을 대신하지 않음, Codex 짝 없음 |

`reviewer.md`, `jarvis-reviewer-call`, `scripts/check_task_record.py`, `.codex/agents`는 바꾸지 않았다.

등록 설계 D1 (a)와의 차이: D1은 `git diff --cached`·`git show :<path>`·`git status` 형태의 읽기 명령을 허용하자고 적었지만, 구현은 셸 도구를 하나도 주지 않고 staged diff와 사전 점검 출력을 요청 본문으로 전달한다. 셸 도구가 0개라 읽기 전용을 도구 목록만으로 보장할 수 있고(V4), 작업 트리 = index 조건으로 Read가 staged 내용을 읽는다.

Manager 해석: "candidate 생성 전 self-review는 최대 1회"를 task당 1회, 첫 candidate 전으로 읽었다. repair candidate 전에는 self-review를 다시 돌리지 않고 task-0171 사전 점검만 거친다(Skill 전제 조건 3이 이를 강제한다).

## 한계

- Codex 표면에는 `self-reviewer`의 짝이 없다. validator가 `.codex/agents`의 파일 집합을 고정하므로 이 task에서 추가하지 않았다. Codex Manager가 같은 절차를 따르려면 별도 결정이 필요하다.
- 이 세션처럼 이미 시작된 Claude Code 세션의 Agent 도구는 새 agent 정의를 바로 쓰지 못했다("Agent type 'self-reviewer' not found"). 그래서 Skill은 새 `claude -p` 프로세스로 실행하게 했다.
- self-review는 모델 판단이라 모든 지적을 잡는다는 보장이 없다(아래 V6).

## Implementer 검증 (작업 트리 기준, candidate 전)

| # | 검사 | 결과 |
| --- | --- | --- |
| V1 | agent 정의의 도구 | `tools: Read, Grep, Glob` 한 줄. Edit·Write·NotebookEdit·Bash 없음 |
| V2 | Skill | 요청 형식에 기록 경로·baseline·staged diff·사전 점검 출력(Owner 원문·Manager 요약·범위는 계획처럼 요청에 직접 넣지 않고 기록 경로로 전달해 self-reviewer가 Read로 읽는다), 실행 명령의 `--tools Read,Grep,Glob`, task당 1회 조건, "Reviewer 판정을 대신하지 않음". PASS/FINDINGS/BLOCKED는 "그런 판정을 내지 않는다"는 문장에만 1회 나옴 |
| V3 | SOP | §3 Implementer 7줄 추가, validator PASS(negative 133, 실패 0) |
| V4 | 실제 실행에서 읽기 전용 | 저장소 밖 임시 clone에서 두 번 실행했다. (1) `claude -p --agent self-reviewer --tools Read,Grep,Glob`: 사용 가능 도구 `Read`·`Grep`·`Glob`, 파일 생성·명령 실행 시도 불가, 파일 생기지 않음, clone `git status` 불변. (2) 대조: CLI에는 `--tools Read,Grep,Glob,Write,Bash --permission-mode acceptEdits`를 주고 agent 정의만 제한: 여전히 `Read`·`Grep`·`Glob`만 주어지고 파일 생기지 않음, clone 불변. agent 정의의 도구 목록과 `--tools` 두 층이 모두 실제로 제한한다 |
| V5~V7 | 재현 측정 | 아래 표 |
| V8 | 회귀 | discord-intake smoke total 147·failed 0, Console smoke 통과, `check_task_record --self-test` 16/0, `git diff --check` 통과, 변경 파일 `check_no_secrets` 0건 |
| V9 | 중단 조건 | 찾음 7 > 0. 잘못된 지적은 V7 정의(Reviewer가 내지 않았고 고칠 필요도 없는 지적)대로 셀 때 해석이 갈리는 4건을 모두 넣으면 4, 빼면 0이다. 어느 쪽이든 4 < 7이라 중단 조건에 걸리지 않아 SOP를 반영했다 |

### V5~V7 재현 측정

방법: 저장소 밖 임시 clone마다 작업 트리·index를 그 candidate의 tree로, HEAD를 부모로 맞춰 candidate 직전 staged 상태를 만들고, Skill과 같은 요청으로 `self-reviewer`를 1회 실행했다. 네 실행 모두 종료 0, clone 불변, 임시 폴더 삭제.

| 상태 | 실제 Reviewer 지적 | candidate 전 발견(V5) | 놓침(V6) |
| --- | --- | --- | --- |
| task-0170 candidate 1 `0fc1236` | F1 summary 최신성, F2 owned 설명 | F1, F2 | 없음 |
| task-0171 candidate 1 `1c74364` | F1 Skill이 index·HEAD만 읽음, F2 ERROR 미처리, F3 `*` 패턴, F4 M2·M12·M10 | F2, F3, F4 | F1 |
| task-0171 repair 1 `0d4a05d` | G1 `--no-renames`(코드), G2 repair 1 결과 미기재 | G2 | G1 |
| task-0171 repair 2 `d7d1d84` | H1 candidate 3 사전 점검 결과 미기재 | H1 | 없음 |
| 합계 | 9 | 7 | 2(둘 다 Skill·코드 동작의 세부) |

V7 잘못된 지적(Owner 조건 "잘못된 지적 때문에 불필요한 수정이 발생한 항목"): 아래 해석이 갈리는 4건을 모두 잘못된 지적으로 세면 4건, 타당하다고 보면 0건이다. 실제와 다른 사실을 주장한 지적은 0건이다. Reviewer가 내지 않은 추가 지적은 13건이다. 그중 9건은 근거가 확인되는 타당한 지적이다(예: 0170 T3 결과가 실제 검사보다 넓게 적힘, 0171 C6 설계 행의 함수 이름 불일치, 기준선 budget 행이 이후 증액과 다름, 0171 기록의 "그 실행에서는 staged 파일 수를 출력하지 않음"은 사실과 다름 — 스크립트는 그 줄을 항상 출력하며 당시 Manager가 출력을 걸러 보았다). 4건은 해석에 따라 갈린다: 근거 10개 상한에 task 기록을 넣는지(0170 1건), task-0171 SOP 문장에 "수동 SOP task" 한정이 없다는 지적(0171 세 상태에서 반복 3건). 이 13건을 모두 따랐다면 기록·문서 수정이 그만큼 늘었을 것이다.

## Self-review (첫 candidate 전 1회)

`jarvis-self-review` 절차대로 저장소 루트에서 `claude -p --agent self-reviewer --tools Read,Grep,Glob --output-format json`에 요청 파일(저장소 밖 scratchpad)을 넘겨 1회 실행했다. 실행 전 사전 점검: `staged_files=4`, `violations=0`, `status=PASS`, 종료 0, 작업 트리 = index. 실행 종료 0, 실행 전후 `git status --porcelain` 동일.

| # | 지적(요지) | 처리 |
| --- | --- | --- |
| SR1 (major) | V7·V9·summary가 Owner 조건 "잘못된 지적 때문에 불필요한 수정"을 "사실과 다른 지적"으로 좁혀 셈 | 수정: V7·V9·summary에 해석이 갈리는 4건을 넣은 수(4)와 뺀 수(0)를 적고 어느 쪽이든 4 < 7임을 명시 |
| SR2 | owned 설명("task-0171 항목 순서 한 곳")이 실제 diff(Implementer 항목 추가만)와 다름 | 수정: owned 설명을 "§3 Implementer에 self-review 항목 1개 추가"로 |
| SR3 | SOP·Skill이 지적을 고치는 주체를 Manager로 적어 "Implementer만 source writer" 규칙과 어긋남 | 수정: SOP와 Skill에서 주체를 Implementer(수동 SOP task에서는 Manager 역할을 겸하는 세션)로 |
| SR4 | 등록 설계 D1(git 읽기 명령 허용)과 구현(셸 도구 0개, diff를 본문으로 전달)의 차이 설명 없음 | 수정: 구현 절에 차이와 이유 한 문단 |
| SR5 | V2 계획(원문·요약·범위를 요청에 직접)과 결과(기록 경로로 전달)의 차이 설명 없음 | 수정: V2 결과에 그 차이를 적음 |
| SR6 | Skill 허용 도구로는 stdin 요청을 조립할 수 없음 | 수정: Skill에 저장소 밖 임시 파일에 요청을 쓰고 `< <request file>`로 넘긴다고 적고 allowed-tools에 `Write` 추가. "writes no file"을 "writes no repository file"로 |
| SR7 | M6 해석이 등록 단계 문구 그대로 | 수정: "등록 시점에는 …(Start 승인 요약 행 P1~P6으로 대체)" |
| SR8 | Manager 요약 S1~S6과 설계 S1~S6 ID가 겹침 | 수정: Manager 요약의 Start 승인 행을 P1~P6으로 |

8건 모두 수정했고 수정하지 않은 지적은 없다. 이 수정들은 candidate 전이라 repair가 아니다(A2). self-review는 이 task에서 다시 실행하지 않는다(task당 1회).

수정 뒤 사전 점검(candidate 1 커밋 전): `staged_files=4`, `violations=0`, `status=PASS`, 종료 0, 작업 트리 = index. 이 줄을 쓴 뒤 다시 stage하고 실행해 같은 판정이 나온 것을 확인하고 candidate를 만들었다. SOP validator PASS, discord-intake smoke failed 0, `git diff --cached --check` 통과.

## Candidate 1

`6f86321c60a8828690a36de603dcf07a06481a38` (parent = baseline `8bb7026`).

## Reviewer 1 (`6f86321`, 유효, FINDINGS major 1·minor 1)

| # | 지적 | 처리 |
| --- | --- | --- |
| F1 (major) | Start 승인 8항 "다른 worktree와 임시 폴더도 건드리지 말고"를 P6가 "보호 대상 무접촉"으로만 해석하고, 이 task가 임시 clone을 만들고 지우며 요청 파일을 쓴 일(그리고 Skill이 그것을 표준 절차로 둔 일)과의 관계를 설명하지 않음 | 승인 조건 해석이라 repair 전에 멈추고 Owner에게 확인을 받음(아래 원문). P6에 Owner가 승인한 해석을 반영하고 R1 행과 "임시 환경 처리" 절 추가 |
| F2 (minor) | Skill allowed-tools의 `Write`에 경로 제한이 없어 "저장소 밖에만 쓴다"가 지시문에만 의존함 | Skill allowed-tools에서 `Write` 제거. Skill에 도구 목록으로 보장되는 제한과 지시문에만 의존하는 제한을 나눠 적음 |

`self_deviations` 없음. 이 수정으로 Self-review 절 SR6 행의 "allowed-tools에 `Write` 추가"는 repair 1에서 되돌려졌다(요청 파일 쓰기는 Skill이 미리 허용하지 않고 세션의 일반 권한 확인을 거친다).

## Owner 결정: Start 승인 8항 해석 확인 (원문)

```text
Owner 결정 — task-0172 Start 승인 8항의 해석 확인
해석을 승인합니다. Start 승인 8항의 "다른 worktree와 임시 폴더도 건드리지 말고"는 기존에 존재하던 다른 worktree와 smoke 임시 폴더를 변경하거나 삭제하지 말라는 의미로 적용합니다.
이번 task에서 검증 목적으로 별도 생성한 임시 clone과 요청 파일은 기존 작업 환경과 분리하고, 검증 종료 후 정리하는 것을 허용합니다. 기존 worktree와 smoke 임시 폴더를 수정·삭제하거나 그 내용을 변경해서는 안 됩니다.
이 해석과 이번 task의 실제 처리 결과를 task-0172 기록에 남기세요. 이 승인은 이번 task의 임시 환경 사용에 대한 확인이며, 다른 task의 보호 조건을 포괄적으로 변경하는 승인은 아닙니다.
남은 Reviewer 지적도 처리하세요.

1. Skill의 `allowed-tools`에서 `Write`를 제거해 self-review agent의 쓰기 권한을 부여하지 마세요.
2. 저장소 밖 경로 제한이 지시문에만 의존하는 부분은 사실대로 기록하고, 기술적으로 보장되는 권한 제한과 구분하세요.
3. repair 예산 1회 범위에서 수정한 뒤 task-0171 사전 점검, 새 Reviewer, QA를 진행하세요.
4. 추가 FINDINGS가 나오면 임의로 repair 예산을 늘리지 말고 중단해 보고하세요.

`jarvis.bat`은 열람·수정·스테이징하지 마세요. 기존 worktree와 smoke 임시 폴더를 건드리지 말고, `git push`는 별도 승인 없이 하지 마세요. Console Complete를 포함한 기존 SOP를 준수하세요.
```

## 임시 환경 처리 (R1에 따른 실제 처리 결과)

| 대상 | 위치 | 처리 |
| --- | --- | --- |
| V4 읽기 전용 확인용 clone | 세션 scratchpad `probe/clone`(저장소 밖) | V4 두 실행 뒤 남아 있던 것을 repair 1 전에 삭제(삭제 확인) |
| V5~V7 재현용 clone 4개 | OS 임시 폴더 `jarvis_self_review_replay_*`(저장소 밖) | 재현 스크립트가 끝에서 삭제(삭제 확인, 남은 폴더 0) |
| self-review 요청·출력 파일과 재현 결과 | 세션 scratchpad(저장소 밖) | QA 근거로 QA 끝까지 두고, QA 뒤 삭제해 그 결과를 QA 절에 적는다 |
| 기존 worktree | `jarvis-core-worktrees` 4개 | 건드리지 않음(`git worktree list` 5줄 그대로) |
| 기존 smoke 임시 폴더 | `%TEMP%\jarvis_worker_smoke_*` 47개 | 건드리지 않음(작업 전후 47개) |

## Repair 1

| 파일 | 변경 |
| --- | --- |
| `.claude/skills/jarvis-self-review/SKILL.md` | allowed-tools에서 `Write` 제거. 요청 파일 쓰기는 Skill이 미리 허용하지 않고 세션 권한 확인을 거친다고 적음. 3단계에 "도구 목록으로 보장되는 것(self-reviewer는 Read·Grep·Glob만, V4)"과 "지시문에만 의존하는 것(요청 파일을 저장소 밖에 쓰기, 저장소 루트에서 실행, 다른 실행 없음)"을 나눠 적음 |
| 이 기록 | summary·`updated_at`, P6 해석, R1·R2 요약 행, Candidate 1, Reviewer 1, Owner 결정 원문, 임시 환경 처리, 이 절 |

budget: `repair_budget=1`, `repair_count=1`(예산 소진). self-review는 이 task에서 다시 실행하지 않는다(task당 1회).

repair 1 사전 점검 첫 실행은 `violations=2`(C1 `task_file_field_too_long`, C2 `field_too_long` summary), 종료 1로 막혔다. summary가 532자로 canonical 상한 500자를 넘었기 때문이다. summary를 줄인 뒤 다시 실행했다(아래 행). 이때 출력된 수정 안내 문구("a value cannot contain a backtick")는 백틱 사례용 고정 문구라 길이 초과에는 맞지 않았다(task-0171 스크립트의 한계, 이 task 범위 밖).

| 검사 | 결과(실행 로그 그대로) |
| --- | --- |
| repair 1 candidate 커밋 전 사전 점검(summary 정정 뒤) | 이 표를 쓰기 전과 쓴 뒤 각각 실행해 같은 판정을 확인하고 커밋했다. 값은 이 표 아래 줄 |

값: `staged_files=4`, `violations=0`, `status=PASS`, 종료 0, 작업 트리 = index.

## Candidate 2 (repair 1)

`5720ea5d470ac15c971b35907e00838e87daa5aa` (parent `6f86321`). Candidate 1의 Reviewer 결과는 무효.

## Reviewer 2 (`5720ea5`, FINDINGS minor 1, `self_deviations` 1건)

| # | 지적 | 처리 |
| --- | --- | --- |
| G1 | Skill allowed-tools의 `Bash(git diff:*)`는 접두어 허용이라 `git diff --output=<파일>`도 권한 확인 없이 통과할 수 있는데, Skill은 쓰기를 미리 허용하지 않는다고 적었고 보장·지시문 의존 목록에도 이 경로가 없음 | Manager가 저장소 밖 임시 저장소에서 `git diff --output=<파일>`이 실제로 파일을 쓰는 것을 확인했다(Claude Code 접두어 매칭이 이 형태를 자동 허용하는지는 실행하지 않음). repair 예산 1회 소진으로 Owner에게 보고, Owner가 예산을 2로 늘려 repair 2 승인(아래 원문) |

유효성(SOP §5): 보고의 `self_deviations`에 1건(허용된 `git show` 출력이 커서 저장 파일로 넘어갔고, 그 파일은 열지 않고 다시 `git grep`으로 읽었다는 고지)이 있으므로 §5에 따라 이 검토는 무효다. 무효 검토의 같은 candidate 재검토(retry, repair 예산 미사용)는 하지 않았다. 지적 G1이 사실로 확인돼 같은 candidate를 다시 검토해도 같은 결과가 나올 것이고, Owner가 수정한 새 candidate의 새 Reviewer 검토를 지시했기 때문이다. `retry_count=0`.

## Owner 결정: repair 예산 증액 1→2 (원문)

```text
Owner 결정: task-0172 repair 예산을 총 2회로 증액합니다. 현재 repair 1/2이며, 이번 수정이 마지막 repair입니다.
수정 범위

1. `jarvis-self-review` Skill의 `allowed-tools`에서 `Bash(git diff:*)`를 제거하세요. `git diff --output=<파일>`처럼 파일을 쓸 수 있는 경로가 일반 권한 확인 없이 허용되지 않도록 합니다.
2. Skill과 task 기록에서 기술적으로 보장되는 제한과 지시문에만 의존하는 제한을 구분해 기록하세요. `git diff` 출력 옵션처럼 파일 쓰기가 가능한 사례도 명시합니다.
3. 코드와 SOP는 수정하지 마세요. 이번 repair는 Skill과 필요한 task 기록만 대상으로 합니다.

검증 및 완료

* task-0171 사전 점검을 통과시킵니다.
* 같은 candidate의 Reviewer 재검토가 아니라, 수정 내용을 반영한 새 candidate를 만들고 새 Reviewer 검토를 진행합니다.
* Reviewer PASS 후 QA를 수행하고 기존 SOP에 따라 checkpoint 및 Console Complete를 진행합니다.
* 추가 FINDINGS가 나오면 예산을 더 늘리거나 SOP §8로 임의 수용하지 말고 중단해 보고하세요.
* `self_deviations`가 있는 검토는 SOP §5에 따라 유효성을 판단하세요. 무효 검토의 허용된 재검토 절차와 repair 예산을 혼동하지 마세요.

보호 조건

* `jarvis.bat`은 열람·수정·스테이징하지 마세요.
* 기존 worktree 4개와 smoke 임시 폴더 47개를 변경하거나 삭제하지 마세요.
* 이번 task에서 만든 scratchpad 파일은 QA 증거로 보존하고, QA 완료 후 이번 task가 생성한 파일만 정리하세요.
* `git push`는 하지 마세요. task 상태를 직접 DONE으로 편집하지 말고 Console의 공식 Complete 절차를 따르세요.
```

## Repair 2

| 파일 | 변경 |
| --- | --- |
| `.claude/skills/jarvis-self-review/SKILL.md` | allowed-tools에서 `Bash(git diff:*)` 제거. 3단계 목록에 "세션이 아직 할 수 있는 쓰기" 항목 추가 |
| 이 기록 | summary·`updated_at`, R3~R5 요약 행, Candidate 2, Reviewer 2와 유효성 판단, Owner 결정 원문, 이 절, 아래 제한 구분 |

### 제한 구분 (repair 2 뒤)

| 구분 | 내용 |
| --- | --- |
| 도구 목록으로 보장 | self-reviewer 프로세스는 Read·Grep·Glob만 갖는다. agent 정의의 `tools:`와 `--tools` 두 층 모두 쓰기·셸 도구를 빼며, CLI가 Write·Bash를 허용해도 agent 정의가 막는 것을 V4에서 확인했다 |
| Skill이 미리 허용하는 것 | `Read`, `Bash(git status:*)`, `Bash(python -B scripts/check_task_record.py:*)`, `Bash(claude -p --agent self-reviewer:*)` |
| 미리 허용하지 않아 일반 권한 확인을 거치는 것 | 요청 파일 쓰기, 1·2단계의 `git diff` 두 명령. `git diff`는 `--output=<파일>`로 파일을 쓸 수 있어서 뺐다 |
| 지시문에만 의존 | 요청 파일을 저장소 밖에 쓰기, 저장소 루트에서 실행, self-review로 다른 것을 실행하지 않기 |
| 남은 쓰기 경로 | 미리 허용된 `git status`가 `.git/index`(추적 파일이 아닌 저장소 메타데이터)를 갱신할 수 있다. Skill의 설정으로는 막지 않는다 |

budget: `repair_budget=2`(Owner 증액), `repair_count=2`(예산 소진).

repair 2 candidate 커밋 전 사전 점검: 이 줄을 쓰기 전 `staged_files=4`, `violations=0`, `status=PASS`, 종료 0. 이 줄을 쓴 뒤 다시 stage하고 실행해 같은 판정을 확인하고 커밋했다. 작업 트리 = index.
