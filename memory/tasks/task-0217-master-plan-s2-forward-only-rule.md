# task-0217-master-plan-s2-forward-only-rule

- id: `task-0217-master-plan-s2-forward-only-rule`
- title: `master-plan 앞을 보는 필드에 앞으로 할 일만 적는 규칙`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-11-05 12:25 UTC`
- updated_at: `2026-11-05 12:25 UTC`
- summary: `master-plan의 Dashboard 현재 다음 작업·현재 결정 필요 줄과 §2 Recommended next step이 끝난 일을 계속 안고 있어 task마다 손으로 고쳐야 한다(task-0213, task-0216). §10 갱신 규칙에 앞을 보는 필드에는 앞으로 할 일과 남은 결정만 적는다는 규칙을 넣고, 세 필드에서 완료 이력을 빼며, 밀린 §2 Recent completed, Last verified, Verified implementation HEAD를 맞춘다. 코드와 validator는 바꾸지 않고 push는 하지 않는다.`
- source_command: `Owner 지시: n3하자 / 승인, 진행해 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `b69517482672b1fad16526af646f5d0689b4c62e` (등록 시점 main HEAD = origin/main) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |

## Owner 결정 (원문, 후보 선택)

```text
n3하자
```

직전 Manager 보고(Owner 원문 아님)가 task-0213 기록의 후보 중 남은 것으로 N2와 N3을 보였고, N3은 "master-plan §2 설명 필드가 손으로 갱신되다 보니 뒤처짐"이다.

## Owner 결정 (원문, 제안 승인)

```text
[Manager 제안]
범위: docs/master-plan.md 한 파일만 바꿉니다.
§10 갱신 규칙에 다음 규칙을 넣습니다.
"§2의 Recommended next step과 Dashboard의 '현재 결정 필요' 줄에는 앞으로 할 일과 아직 남은 결정만 적는다. 완료 사실은 날짜 항목과 Recent completed에만 적는다."
위 두 필드에서 완료 이력 문장을 빼고, 남은 결정만 남깁니다.
밀린 필드를 한 번 맞춥니다. Recent completed에 task-0211~0216을 넣고, Last verified와 HEAD를 갱신합니다.
범위 밖: validator 강제 검사, Console 변경, push/PR, jarvis.bat

[Owner 답]
승인, 진행해
```

## Owner 결정 (원문, 착수 전 bounded question)

```text
[Manager 질문]
master-plan을 보니 Dashboard의 '현재 다음 작업' 줄(115행)도 '현재 결정 필요' 줄이나 §2 Recommended next step처럼 완료 이력(task-0206~0212가 끝났다는 서술)을 안고 있습니다. 승인한 범위는 이 두 필드였는데, '현재 다음 작업' 줄도 새 규칙과 정리 대상에 넣을까요?

[Owner 답]
세 줄 모두 포함 (Recommended)
```

선택지 설명(Manager 문구, Owner 원문 아님): "'현재 다음 작업' 줄도 규칙 대상에 넣고, 완료 이력을 뺍니다. 이 문제의 나머지 원인까지 함께 없앱니다."

## Owner 결정 (원문, Recent completed 항목 빼기)

```text
[Manager 질문]
§2 Recent completed에는 500자 상한이 있어서, task-0210~0216을 넣으려면 기존 항목 세 개(/run·/retry 폐기 task-0179, /go 한정 task-0182, 사용량 기록 task-0199)를 빼야 합니다. 승인한 제안은 '넣는다'까지만 말했습니다. 세 항목은 Dashboard 날짜 항목(153·156·169행)에 그대로 남습니다. 이 세 항목을 빼도 될까요?

[Owner 답]
세 항목 빼기 (Recommended)
```

선택지 설명(Manager 문구, Owner 원문 아님): "Recent completed에서 세 항목을 빼고 task-0210~0216을 넣습니다. 날짜 항목에는 그대로 남습니다."

## 조사 (baseline 기준)

- 앞을 보는 필드 세 개가 끝난 일을 적고 있었다.
  - Dashboard `현재 다음 작업`(115행): task-0206~0212가 끝났다는 괄호, task-0042/0044 DONE과 task-0052 연결 문장, ③이 P2-5/P2-6으로 완료됐다는 괄호.
  - Dashboard `현재 결정 필요`(185행): task-0215에서 attempt branch를 지웠다는 문장, Phase 1·P2 결정이 모두 완료라는 구절, ③ 아웃바운드 완료 문장.
  - §2 `Recommended next step`(239행): task-0211·0212·0215로 끝난 일 문장.
- 뒤처진 필드: §2 `Last verified` 2026-10-29, `Verified implementation HEAD` `7b03f6f`, `Recent completed`는 task-0209까지.
- 빼는 완료 사실은 다른 곳에 남아 있다. task-0206~0216은 Owner Dashboard 날짜 항목에, task-0042/0044 완료는 Dashboard `최근 완료` 줄("선택적 잔여 항목이던 task-0042/0044도 이후 완료")에, task-0052 연결은 2026-09-06 날짜 항목에 있다.
- Console은 §2 값을 텍스트로 읽고 값마다 500자 상한(`MASTER_PLAN_VALUE_MAX_CHARS`)이 있다. Dashboard 줄을 읽는 코드는 없다. validator `_validate_master_plan`은 옛 HEAD `7d4394e…` 문자열을 요구하며 그 값은 Dashboard "최근 검증 결과" 줄에 남는다. `Verified implementation HEAD`는 현재 branch의 조상이어야 한다(task-0126).

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `docs/master-plan.md`(Dashboard `현재 다음 작업`·`현재 결정 필요` 줄, §2 `Last verified`·`Verified implementation HEAD`·`Recommended next step`·`Recent completed`, §10 규칙 한 문단), 이 task 기록 |
| deny | master-plan의 다른 줄·필드·날짜 항목, 코드, validator, 다른 task 기록, `jarvis.bat`, `.env`, push |

## Start

Console Create Local Task Preview(Title·Summary·TODO·경로 확인, raw transcript 저장 안 함)를 확인하고 Confirm해 TODO 기록을 만들었다. 이어 Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `Confirm Start`로 Confirm했다(status·updated_at 줄만 바뀜, updated_at `2026-11-05 12:25 UTC`). Console은 수정 전에 껐다. 그 뒤 title·summary·source_command를 이 task 내용으로 고쳤다(Console 요약이 500자에서 잘렸기 때문).

## 구현

- `docs/master-plan.md` Dashboard `현재 다음 작업`: 완료 괄호와 task-0042/0044/0052 문장을 빼고, ③ 괄호를 "③승인 게시 흐름의 인바운드는 범위 밖이라 이 목록에 없다"로 바꿨다. 보류 문장은 그대로다.
- 같은 파일 `현재 결정 필요`: attempt branch 완료 문장과 "그 외 … 모두 완료" 구절을 빼고, ③ 문장을 "③승인 게시 흐름의 인바운드는 범위 밖이라 결정 대상이 아니다"로 바꿨다. 남은 결정(다음 package 승인, bridge·supervisor·승인자 ID와 그 조건)은 그대로다.
- §2 `Recommended next step`: 완료 문장만 뺐다. `Last verified` `2026-11-05`, `Verified implementation HEAD` baseline `b69517482672b1fad16526af646f5d0689b4c62e`. `Recent completed`에 task-0210~0216을 넣고 500자 상한 때문에 /run·/retry 폐기(task-0179), /go 한정(task-0182), 사용량 기록(task-0199)을 뺐다(Owner 결정, 날짜 항목 153·156·169행에 남음).
- §10 "이 문서 갱신 규칙"에 앞을 보는 필드 규칙 한 문단을 넣었다.

## Implementer 검증 (작업 트리)

- §2 값 길이(백틱·`**` 제외): Last verified 10, Verified HEAD 40, Recommended next step 280, Recent completed 495(상한 500).
- SOP validator PASS, `run_web_app.py --self-test` 통과, Console smoke PYTHONUTF8=1과 없음 모두 rc=0, `git diff --check` 통과.

## Self-review

staged 변경에 self-reviewer를 한 번 돌렸다(Reviewer 판정 아님). 지적 세 건과 처리:

1. major: Recent completed에서 기존 세 항목(task-0179·0182·0199)을 뺀 것을 승인 원문이 다루지 않는다. Owner bounded question으로 확인받았고(Owner 결정 원문, Recent completed 항목 빼기), 세 항목이 날짜 항목 153·156·169행에 남는 것을 확인해 구현 절과 요약 A9·A17~A22에 적었다.
2. minor: 요약 행 번호 참조가 어긋났다(첫 행 "n3하자"를 넣어 한 칸씩 밀림). A12(승인)·A3~A10(제안)·A16(세 줄 포함 답)으로 고쳤다.
3. minor: A8 행이 자기 자신을 가리켰다. 충족 내용(§2 세 필드 갱신, A9)을 적었고, A15도 "A16 답의 질문"으로 고쳤다.

수정 뒤 사전 점검(`check_task_record.py --require-quotes`) 결과는 아래 candidate 직전 실행과 같다(PASS, violations 0).

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다. 오른쪽 칸에서 "Manager 해석"이라고 적은 부분은 승인 원문에 없는 내용이다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문, 후보 선택) | "n3하자" | 후보 선택. task-0213 기록의 N3(master-plan §2 설명 필드가 손으로 갱신돼 뒤처짐)을 고른 것이다. 착수 승인은 A12다 |
| A2 | Owner 결정 (원문, 제안 승인) | "[Manager 제안]" | 제안의 표지. 아래 A3~A10은 Manager가 쓴 제안 문장이다 |
| A3 | Owner 결정 (원문, 제안 승인) | "범위: docs/master-plan.md 한 파일만 바꿉니다." | `docs/master-plan.md`만 바꿨다. 이 task 기록은 SOP 기록으로 Manager가 넣었다(범위 표 owned) |
| A4 | Owner 결정 (원문, 제안 승인) | "§10 갱신 규칙에 다음 규칙을 넣습니다." | §10 "이 문서 갱신 규칙"에 한 문단을 넣었다(구현 절) |
| A5 | Owner 결정 (원문, 제안 승인) | ""§2의 Recommended next step과 Dashboard의 '현재 결정 필요' 줄에는 앞으로 할 일과 아직 남은 결정만 적는다." | 규칙 문단이 이 두 필드를 대상으로 적는다. A16에 따라 `현재 다음 작업` 줄도 대상에 넣었다 |
| A6 | Owner 결정 (원문, 제안 승인) | "완료 사실은 날짜 항목과 Recent completed에만 적는다."" | 규칙 문단이 완료 사실의 자리를 날짜 항목과 §2 `Recent completed`로 적는다. Manager 해석: Dashboard `최근 완료` 줄은 `Recent completed`의 Dashboard 쪽 짝이라 같은 자리로 함께 적었다 |
| A7 | Owner 결정 (원문, 제안 승인) | "위 두 필드에서 완료 이력 문장을 빼고, 남은 결정만 남깁니다." | `현재 결정 필요`와 `Recommended next step`에서 완료 문장을 뺐고 남은 결정·보류 문장은 그대로다(구현 절) |
| A8 | Owner 결정 (원문, 제안 승인) | "밀린 필드를 한 번 맞춥니다." | §2 `Last verified`·`Verified implementation HEAD`·`Recent completed`를 갱신했다(A9) |
| A9 | Owner 결정 (원문, 제안 승인) | "Recent completed에 task-0211~0216을 넣고, Last verified와 HEAD를 갱신합니다." | `Recent completed`에 task-0211~0216을 넣었다. Manager 해석: 목록에 없던 task-0210(master-plan 동기화)도 같은 밀린 항목이라 함께 넣었다. `Last verified` `2026-11-05`, HEAD는 baseline `b695174`의 40자 hash다. 기존 항목 세 개를 뺀 것은 A17~A22의 Owner 결정이다 |
| A10 | Owner 결정 (원문, 제안 승인) | "범위 밖: validator 강제 검사, Console 변경, push/PR, jarvis.bat" | 코드·validator·Console을 바꾸지 않았고 push·PR은 하지 않았다. `jarvis.bat`는 손대지 않았다 |
| A11 | Owner 결정 (원문, 제안 승인) | "[Owner 답]" | 답의 표지 |
| A12 | Owner 결정 (원문, 제안 승인) | "승인, 진행해" | A3~A10 제안의 착수 승인 |
| A13 | Owner 결정 (원문, 착수 전 bounded question) | "[Manager 질문]" | 질문의 표지 |
| A14 | Owner 결정 (원문, 착수 전 bounded question) | "master-plan을 보니 Dashboard의 '현재 다음 작업' 줄(115행)도 '현재 결정 필요' 줄이나 §2 Recommended next step처럼 완료 이력(task-0206~0212가 끝났다는 서술)을 안고 있습니다." | A16 답의 질문 배경. 조사 절과 같다 |
| A15 | Owner 결정 (원문, 착수 전 bounded question) | "승인한 범위는 이 두 필드였는데, '현재 다음 작업' 줄도 새 규칙과 정리 대상에 넣을까요?" | A16 답의 질문 |
| A16 | Owner 결정 (원문, 착수 전 bounded question) | "세 줄 모두 포함 (Recommended)" | `현재 다음 작업` 줄도 규칙 대상에 넣고 완료 이력을 뺐다(구현 절) |
| A17 | Owner 결정 (원문, Recent completed 항목 빼기) | "[Manager 질문]" | 질문의 표지 |
| A18 | Owner 결정 (원문, Recent completed 항목 빼기) | "§2 Recent completed에는 500자 상한이 있어서, task-0210~0216을 넣으려면 기존 항목 세 개(/run·/retry 폐기 task-0179, /go 한정 task-0182, 사용량 기록 task-0199)를 빼야 합니다." | A22 답의 질문 배경. self-review major 지적(승인이 기존 항목 삭제를 말하지 않음)에서 나온 질문이다 |
| A19 | Owner 결정 (원문, Recent completed 항목 빼기) | "승인한 제안은 '넣는다'까지만 말했습니다." | A22 답의 질문 배경 |
| A20 | Owner 결정 (원문, Recent completed 항목 빼기) | "세 항목은 Dashboard 날짜 항목(153·156·169행)에 그대로 남습니다." | 날짜 항목 153·156·169행이 세 task를 그대로 적는 것을 확인했다 |
| A21 | Owner 결정 (원문, Recent completed 항목 빼기) | "이 세 항목을 빼도 될까요?" | A22 답의 질문 |
| A22 | Owner 결정 (원문, Recent completed 항목 빼기) | "세 항목 빼기 (Recommended)" | `Recent completed`에서 task-0179·0182·0199 세 항목을 빼고 task-0210~0216을 넣었다(495자) |
