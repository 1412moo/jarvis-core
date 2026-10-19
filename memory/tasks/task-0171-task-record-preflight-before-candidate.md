# task-0171-task-record-preflight-before-candidate

- id: `task-0171-task-record-preflight-before-candidate`
- title: `candidate 커밋 전 task 기록 사전 점검: 파서·Console 호환, 범위 표, updated_at, 파일 끝 줄바꿈`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-19 13:47 UTC`
- updated_at: `2026-10-19 14:36 UTC`
- summary: `최근 수동 task 10건 중 7건에서 첫 Reviewer가 task 기록 정합성 문제만으로 FINDINGS를 내 repair 예산을 소진했다. candidate 커밋 전에 기록을 canonical parser와 Console parser로 읽고, staged 변경 파일과 owned 행을 대조하고, updated_at 갱신과 파일 끝 줄바꿈을 확인해 결정론적 위반이면 candidate를 만들지 않게 한다. Owner가 D1 (a)·D2 차단·D3 참고로 Start를 승인해 scripts/check_task_record.py와 SOP 3·task-template·Reviewer 호출 Skill 변경을 구현했다. Reviewer minor를 repair 3회(Owner가 예산을 2, 다시 3으로 증액)로 고친 candidate 969f53b가 Reviewer PASS와 QA PASS를 받았다. DONE은 Owner Console Complete 대기. push 없음.`
- source_command: `Owner 요청: candidate 커밋 전 task 기록 사전 점검 강화 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `e79a2cb214e6b6c11eddd753f2bf17ed7452f261` (등록 시점 main HEAD = origin/main). Start 때 다시 확인한다 |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat` |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (기본값) |

## Owner 요청 (원문)

```text
다음 개발 작업으로 candidate 커밋 전 task 기록 사전 점검 강화를 진행해.
목표는 Reviewer가 반복적으로 task 기록 정합성 문제를 발견해 repair 예산을 소모하는 일을 줄이는 것이다. 기존 조사 결과를 재사용하고 같은 조사를 반복하지 마.
1. Task 등록 및 범위 확정

* 기존 SOP와 task 등록 절차를 따라 task를 등록해.
* task-0169의 기존 검사기와 관련 파서·검증기를 우선 재사용해.
* task 범위와 검증 계획을 기록한 다음 기존 승인 절차에 따라 진행해.
* Owner 승인이 필요한 단계에서는 승인 없이 구현을 시작하지 마.

2. 구현 목표
candidate 커밋 전에 다음 항목을 결정론적으로 검사하도록 해.

1. Canonical parser / Console 호환성: task 기록이 실제 파서와 Console에서 정상적으로 읽히는지 확인한다. task-0168의 summary 백틱 문제처럼 Complete 단계에서 뒤늦게 실패하는 사례를 사전에 잡는다.
2. 범위 표와 실제 변경 파일의 정합성: baseline 대비 변경 파일과 task 기록의 owned/scope 표를 대조한다. 정당한 신규 파일이나 문서 변경을 잘못 차단하지 않도록 기존 계약을 먼저 확인한다.
3. `updated_at`: task 기록 본문이 변경됐는데 해당 필드가 갱신되지 않은 경우를 검출한다. 기존 task-model §7 규칙을 따른다.
4. 파일 끝 줄바꿈: 기존 규칙에 어긋나는 경우 검출한다.
5. task-0169 원문 인용 검사: 기존 기능을 유지하고 중복 구현하지 않는다.

3. 차단 정책

* 결정론적 위반은 수정될 때까지 candidate 커밋을 차단한다.
* 검사 실패 시 위반 항목과 수정 방법을 구체적으로 출력한다.
* 검사기가 정상적인 신규 파일이나 허용된 변경을 차단하지 않도록 기존 계약과 실제 사용 사례를 확인한다.
* summary의 의미상 최신성 등 기계적으로 판정할 수 없는 사항은 Reviewer의 판단으로 남긴다.
* Reviewer와 QA의 역할, repair 예산, SOP §8, Owner 승인 절차는 변경하거나 완화하지 않는다.

4. 구현 및 검증

* 최소 diff를 우선하고 SOP·task-template 변경은 꼭 필요한 부분만 한다.
* 정상 사례뿐 아니라 파서 오류, 범위 불일치, `updated_at` 누락, 줄바꿈 오류, 정상 신규 파일 및 문서 변경 사례를 테스트한다.
* 기존 테스트와 관련 smoke, validator, Reviewer, QA를 프로젝트 절차에 따라 실행한다.
* 테스트를 통과했다고 추정하지 말고 실제 결과를 기록한다.

5. Git 및 완료 절차

* 저장소의 기존 checkpoint·commit·Console Complete 절차를 따른다.
* `jarvis.bat`은 보호 대상이므로 열람·수정·삭제·스테이징하지 않는다.
* 다른 worktree와 smoke 임시 폴더는 건드리지 않는다.
* push는 별도 Owner 승인 없이 하지 않는다.
* task 기록을 직접 수정해 임의로 DONE 처리하지 않는다. 정식 완료 절차를 사용한다.

6. 최종 보고

* 변경된 파일과 핵심 변경 사항
* 추가된 검사와 테스트 결과
* Reviewer·QA 결과
* candidate 및 checkpoint 커밋
* Console Complete 상태
* main과 origin/main 상태
* 다음에 줄어들 것으로 예상되는 Owner 개입과 남아 있는 한계

이미 확인된 사실을 불필요하게 재조사하지 말고, 정책상 필요한 승인 지점에서만 멈춰. 목표는 검사기를 하나 더 만드는 것이 아니라 Reviewer의 repair 예산을 기록 오류가 아닌 실제 개발 문제에 사용할 수 있도록 하는 것이다.
```

## 조사 결과 (read-only, 등록 전 확인)

1. 최근 수동 SOP task 10건(task-0160~0170, Worker 경로 task-0166 제외) 중 7건(0160·0161·0162·0163·0164·0168·0170)에서 첫 Reviewer가
   "FINDINGS, 모두 이 기록"이었다. 코드 지적은 0165·0167뿐이다. 기록 지적은 repair 예산 1을 쓰고, 다음 지적이 Owner의 예산 증액
   (0156·0157·0160·0161·0164·0167)이나 SOP §8 수용(0161·0164·0167·0168)으로 이어졌다.
2. 지적 유형과 현재 대책: Owner 조건 인용 누락(0160·0161·0163·0164·0168)은 task-0169 검사가 잡는다(0169는 첫 Reviewer PASS, 0170은 이 유형 없음).
   남은 유형은 범위 표와 diff 불일치(0164, 0170 F2), `updated_at` 미갱신(0170 QA Q10, task-model §7), Console이 읽지 못하는 메타데이터
   (0168 summary 안 백틱, 별도 커밋 `4010721`), 파일 끝 줄바꿈 누락(0161), summary의 의미상 최신성(0161, 0170 F1), 정의 문제(0162)다.
   뒤의 둘은 결정론적으로 판정할 수 없다.
3. 재사용할 구현:
   - canonical parser `task_file_writer._transition_metadata(raw, file_name)`(`orchestrator/discord-intake/task_file_writer.py:458`). intake smoke가 모든 기록에 쓴다.
   - Console parser `parse_task_view_text(file_name, text)`(`apps/jarvis-console/run_web_app.py:1603`). Start·Complete 경로가 쓰고, 백틱 문제를 `invalid_text`로 거절한 것이 이것이다.
   - task-0169 `scripts/check_summary_quotes.py`(`check_record`, `--self-test`, 종료 코드 0/1/2).
4. 범위 표: 제목은 기록마다 다르지만("File ownership", "범위", "변경 예정 파일", "범위와 영향 파일") task-0160~0170 중 9건에
   `| owned | … |` 행이 있고 경로는 백틱으로 적혀 있다. 없는 것은 task-0168뿐이다. 신규 파일도 owned에 적혀 왔다(0169의 `scripts/check_summary_quotes.py`(신규)).
   "QA 뒤 별도 commit" 행(0169 master-plan)은 candidate 밖이다.
5. 파일 끝 줄바꿈: 문서화된 규칙은 찾지 못했지만 정식 writer `_render_task_markdown`이 마지막에 빈 줄을 붙여 항상 줄바꿈으로 끝낸다
   (`task_file_writer.py:211-212`). 현재 줄바꿈 없이 끝나는 기록은 task-0136 하나다(history).
6. task-model §7: `status`가 바뀌거나 `summary`·`title`·`repo` 등 본문 의미가 바뀌면 `updated_at`를 갱신한다.

## Start 전에 정할 항목

| # | 결정 | 선택지 | Manager 권고 |
| --- | --- | --- | --- |
| D1 | 차단 방식 | (a) 스크립트 + SOP §3 규칙: Manager는 검사 종료 코드가 0이 아니면 candidate 커밋을 만들지 않는다 / (b) (a) + 로컬 git pre-commit hook 설치 | (a). hook은 저장소 밖 상설 설정이라 별도 결정으로 미룬다 |
| D2 | 범위 표 계약 | owned 행이 없는 기록은 (a) 위반으로 차단 / (b) 경고만 | (a), 단 task-template에 owned 행 형식 한 줄을 적는다. Worker 경로 기록(`source_command: /task`)은 대상이 아니다 |
| D3 | task-0169 인용 검사의 효력 | 지금처럼 참고 출력 유지 / 차단으로 승격 | 참고 유지. 목록에 조건이 아닌 소제목·표 머리가 섞여 차단하면 정상 기록을 막는다 |

## 검사 설계 (Start 승인 시)

대상은 staged candidate다: `git diff --cached --name-only <baseline>`(baseline 이후 커밋 + staged). 작업 트리의 untracked 파일과 `jarvis.bat`은 읽지 않는다.

| # | 검사 | 판정 | 위반 시 출력 |
| --- | --- | --- | --- |
| C1 | canonical parser | staged 기록을 `_transition_metadata`로 읽어 오류가 없어야 함 | 오류 코드와 "메타데이터 줄 형식을 고친다" |
| C2 | Console parser | `parse_task_view_text`가 유효한 view를 돌려줘야 함(`invalid_text` 등 없음) | 실패 필드 이름과 원인(예: summary 안 백틱) |
| C3 | 범위 표 | staged 변경 파일이 모두 owned 행(디렉터리는 `/`로 끝나는 접두어)이나 이 기록 자신이어야 함. owned에 있으나 바뀌지 않은 경로는 경고만 | owned 밖 파일 목록과 "owned 행에 추가하거나 stage에서 뺀다" |
| C4 | `updated_at` | HEAD의 같은 기록과 staged 기록이 다르면 `updated_at`도 달라야 함. HEAD에 없는 새 기록은 통과 | 이전·현재 값과 "현재 UTC로 갱신한다" |
| C5 | 파일 끝 줄바꿈 | staged 기록이 `\n`으로 끝나야 함 | "마지막 줄 뒤에 줄바꿈을 넣는다" |
| C6 | 원문 인용(task-0169) | `check_summary_quotes.check_record` 결과를 참고로 그대로 출력(D3) | 기존 출력 그대로 |

종료 코드: 0 위반 없음, 1 위반 있음(candidate 금지), 2 입력·환경 오류. 파일을 쓰지 않고 네트워크를 쓰지 않는다.

## Manager 요약

| # | Owner 원문 | Manager 해석 |
| --- | --- | --- |
| M1 | "다음 개발 작업으로 candidate 커밋 전 task 기록 사전 점검 강화를 진행해." / "목표는 Reviewer가 반복적으로 task 기록 정합성 문제를 발견해 repair 예산을 소모하는 일을 줄이는 것이다." / "기존 조사 결과를 재사용하고 같은 조사를 반복하지 마." | 조사 1·2를 근거로 쓰고 다시 조사하지 않는다 |
| M2 | "기존 SOP와 task 등록 절차를 따라 task를 등록해." / "task-0169의 기존 검사기와 관련 파서·검증기를 우선 재사용해." / "task 범위와 검증 계획을 기록한 다음 기존 승인 절차에 따라 진행해." / "Owner 승인이 필요한 단계에서는 승인 없이 구현을 시작하지 마." | 등록 단계에서는 이 기록(TODO)만 만들었다(Start 승인 뒤 S4가 대체). 재사용 대상은 조사 3 |
| M3 | "candidate 커밋 전에 다음 항목을 결정론적으로 검사하도록 해." / "1. Canonical parser / Console 호환성: task 기록이 실제 파서와 Console에서 정상적으로 읽히는지 확인한다." / "task-0168의 summary 백틱 문제처럼 Complete 단계에서 뒤늦게 실패하는 사례를 사전에 잡는다." | C1·C2 |
| M4 | "2. 범위 표와 실제 변경 파일의 정합성: baseline 대비 변경 파일과 task 기록의 owned/scope 표를 대조한다." / "정당한 신규 파일이나 문서 변경을 잘못 차단하지 않도록 기존 계약을 먼저 확인한다." | C3. 신규 파일·문서도 owned에 있으면 통과, 기록 자신은 항상 허용, 바뀌지 않은 owned 경로는 경고만(조사 4) |
| M5 | "3. `updated_at`: task 기록 본문이 변경됐는데 해당 필드가 갱신되지 않은 경우를 검출한다." / "기존 task-model §7 규칙을 따른다." | C4(조사 6) |
| M6 | "4. 파일 끝 줄바꿈: 기존 규칙에 어긋나는 경우 검출한다." | C5. 근거는 정식 writer의 출력 형식(조사 5) |
| M7 | "5. task-0169 원문 인용 검사: 기존 기능을 유지하고 중복 구현하지 않는다." | C6. 기존 함수를 부르고 다시 구현하지 않는다 |
| M8 | "결정론적 위반은 수정될 때까지 candidate 커밋을 차단한다." / "검사 실패 시 위반 항목과 수정 방법을 구체적으로 출력한다." / "검사기가 정상적인 신규 파일이나 허용된 변경을 차단하지 않도록 기존 계약과 실제 사용 사례를 확인한다." | 종료 코드 1이면 candidate 금지(D1). 위반마다 수정 방법 출력. 기존 기록 9건 형식으로 회귀 확인 |
| M9 | "summary의 의미상 최신성 등 기계적으로 판정할 수 없는 사항은 Reviewer의 판단으로 남긴다." / "Reviewer와 QA의 역할, repair 예산, SOP §8, Owner 승인 절차는 변경하거나 완화하지 않는다." | summary 의미는 검사하지 않는다. Reviewer·QA·budget·§8·승인 무변경 |
| M10 | "최소 diff를 우선하고 SOP·task-template 변경은 꼭 필요한 부분만 한다." / "정상 사례뿐 아니라 파서 오류, 범위 불일치, `updated_at` 누락, 줄바꿈 오류, 정상 신규 파일 및 문서 변경 사례를 테스트한다." / "기존 테스트와 관련 smoke, validator, Reviewer, QA를 프로젝트 절차에 따라 실행한다." / "테스트를 통과했다고 추정하지 말고 실제 결과를 기록한다." | 아래 검증 계획 T1~T10(기존 회귀는 T10). SOP §3 한 항목, task-template 한 줄 |
| M11 | "저장소의 기존 checkpoint·commit·Console Complete 절차를 따른다." / "`jarvis.bat`은 보호 대상이므로 열람·수정·삭제·스테이징하지 않는다." / "다른 worktree와 smoke 임시 폴더는 건드리지 않는다." / "push는 별도 Owner 승인 없이 하지 않는다." / "task 기록을 직접 수정해 임의로 DONE 처리하지 않는다." / "정식 완료 절차를 사용한다." | Console Start·Complete, candidate → Reviewer → QA → 기록 checkpoint. push·임의 DONE 없음 |
| M12 | "이미 확인된 사실을 불필요하게 재조사하지 말고, 정책상 필요한 승인 지점에서만 멈춰." / "목표는 검사기를 하나 더 만드는 것이 아니라 Reviewer의 repair 예산을 기록 오류가 아닌 실제 개발 문제에 사용할 수 있도록 하는 것이다." | 등록 단계에서는 Start 승인 지점에서 멈췄다(S4가 대체). 효과는 기록 지적 감소로 판단(QA에서 과거 사례 재현) |
| M13 | "변경된 파일과 핵심 변경 사항" / "추가된 검사와 테스트 결과" / "Reviewer·QA 결과" / "candidate 및 checkpoint 커밋" / "Console Complete 상태" / "main과 origin/main 상태" / "다음에 줄어들 것으로 예상되는 Owner 개입과 남아 있는 한계" | 최종 보고의 7개 항목 |
| S1 | "task-0171의 Owner 결정을 다음과 같이 확정한다." / "D1: (a) 스크립트와 SOP 규칙으로 차단한다." / "로컬 Git pre-commit hook은 설치하지 않는다." / "검사 종료 코드가 0이 아니면 Manager는 candidate를 만들지 않는다." | SOP §3 규칙과 종료 코드로 차단. hook 없음 |
| S2 | "D2: 차단." / "검사 대상 기록에 `owned` 행이 없으면 위반으로 처리한다." / "Worker 경로 기록은 기존 계획대로 제외한다." / "정상적인 신규 파일과 허용된 문서 변경이 잘못 차단되지 않도록 범위 대조 로직을 검증한다." | owned 행 없음 = C3 위반. `source_command: /task` 기록은 대상 외(종료 2로 안내). T5·T9로 오차단 확인 |
| S3 | "D3: 참고 출력 유지." / "원문 인용 검사는 실행하되 종료 코드에는 영향을 주지 않는다." | C6은 출력만 |
| S4 | "이 결정으로 task-0171 Start를 승인한다." / "등록된 범위와 검증 계획 안에서 구현 및 테스트를 진행한다." / "추가 범위 확장 없이 최소 diff를 유지하고, 기존 Reviewer·QA·repair 예산·SOP §8 및 승인 정책을 그대로 지킨다." | Console Start → 범위 표대로 구현 → T1~T10 |
| S5 | "테스트 결과와 실제 위반 사례 재현을 근거로 완료 절차를 진행하고, push는 별도 승인 전까지 하지 않는다." / "추가 Owner 결정이 필요한 문제가 생기면 임의로 범위를 확장하지 말고 해당 지점에서 멈춰 보고한다." | QA 뒤 Console Complete·checkpoint·master-plan까지. push 없음. 새 결정이 필요하면 멈춤 |
| R1 | "task-0171의 repair 예산을 기존 1회에서 총 2회로 늘리는 것을 승인한다." / "Reviewer 2의 minor 지적 2건을 모두 수정해." / "변경 파일 목록을 얻는 Git 명령에 `--no-renames`를 적용해 파일 이동 전후 경로가 모두 검사되도록 한다." / "범위 밖 파일을 `owned` 경로로 이동하는 사례를 self-test에 추가한다." / "Git 설정에 따라 검사 결과가 달라지지 않는지 확인한다." / "task-0171 기록의 T10 및 관련 검증 항목에 repair 1 이후 실제 결과를 반영한다." / "self-test 14/0, T9 재현 결과, validator, intake smoke, diff 검사, 사전 점검 결과를 실제 실행 로그와 대조해 기록한다." | repair 2: `--no-renames`, 이동 사례와 `diff.renames` true·false·copies 비교 self-test, 아래 repair 1·2 실제 결과 표 |
| R2 | "변경 후 사전 점검을 통과한 경우에만 candidate를 생성한다." / "새 candidate hash를 고정해 Reviewer를 다시 호출하고, 이후 QA와 기존 완료 절차를 진행한다." / "남은 지적이 있으면 임의로 추가 repair하거나 SOP §8로 수용하지 말고 중단해 보고한다." / "기존 승인·검증 정책은 유지한다." | 사전 점검 종료 0일 때만 commit → 새 Reviewer → QA → Console Complete. 지적이 남으면 멈춤 |
| R3 | "`jarvis.bat`은 건드리지 않는다." / "push는 하지 않는다." / "다른 worktree와 smoke 임시 폴더는 건드리지 않는다." / "task 기록을 직접 DONE으로 변경하지 않는다." / "Console Complete 절차를 사용한다." / "완료 보고에는 최종 테스트 결과, Reviewer·QA 판정, checkpoint 커밋, Console Complete 상태, main과 origin/main의 차이를 포함해라." | 보호 대상 무접촉, push 없음, DONE은 Console Complete. 최종 보고 항목 |
| R4 | "Owner 결정: 선택지 1 승인." / "repair 예산을 총 3회로 한정해 증액합니다." / "이번 repair는 Reviewer 3의 H1(minor, 기록 누락)만 수정합니다." / "실행 로그로 확인된 candidate 3 사전 점검 결과를 task-0171 기록에 한 행으로 추가하세요." / "1차: `staged_files=5`, `violations=0`, `status=PASS`, `preflight_exit=0`" / "2차: `violations=0`, `status=PASS`, `exit=0`" / "2차 실행에서 확인되지 않은 staged 파일 수는 기재하지 마세요." / "기록 수정 후 preflight를 다시 실행하고 PASS 여부를 확인하세요." / "새 Reviewer 검토를 진행하세요." / "Reviewer가 PASS하면 QA를 진행하고, 기존 SOP에 따라 checkpoint와 Console Complete까지 진행하세요." | repair 3: 기록에 사전 점검 결과 한 행만. 재점검 → Reviewer 4 → PASS면 QA → checkpoint → Console Complete |
| R5 | "이번 증액은 총 repair 3회 한도입니다." / "추가 FINDINGS가 나오면 임의로 더 수정하거나 SOP §8로 수용하지 말고 중단해 보고하세요." / "코드·SOP·Skill·template은 변경하지 마세요." / "기존 검증 결과를 재사용할 수 있는 경우 불필요하게 반복하지 말고, 이번 변경에 필요한 검증만 수행하세요." / "`jarvis.bat`은 열람·수정·스테이징하지 마세요." / "다른 worktree와 임시 폴더도 건드리지 마세요." / "`git push`는 하지 마세요." / "task 파일을 직접 DONE으로 바꾸지 말고 Console의 공식 Complete 절차를 따르세요." / "수정·검증 결과와 최종 Git 상태를 보고하세요." | 기록만 변경. 이 변경에 필요한 검증(사전 점검, 기록 파서)만 다시. FINDINGS가 나오면 멈춤 |

## Start 승인 (원문)

```text
task-0171의 Owner 결정을 다음과 같이 확정한다.

* D1: (a) 스크립트와 SOP 규칙으로 차단한다. 로컬 Git pre-commit hook은 설치하지 않는다. 검사 종료 코드가 0이 아니면 Manager는 candidate를 만들지 않는다.
* D2: 차단. 검사 대상 기록에 `owned` 행이 없으면 위반으로 처리한다. Worker 경로 기록은 기존 계획대로 제외한다. 정상적인 신규 파일과 허용된 문서 변경이 잘못 차단되지 않도록 범위 대조 로직을 검증한다.
* D3: 참고 출력 유지. 원문 인용 검사는 실행하되 종료 코드에는 영향을 주지 않는다.

이 결정으로 task-0171 Start를 승인한다. 등록된 범위와 검증 계획 안에서 구현 및 테스트를 진행한다.
추가 범위 확장 없이 최소 diff를 유지하고, 기존 Reviewer·QA·repair 예산·SOP §8 및 승인 정책을 그대로 지킨다. 테스트 결과와 실제 위반 사례 재현을 근거로 완료 절차를 진행하고, push는 별도 승인 전까지 하지 않는다.
추가 Owner 결정이 필요한 문제가 생기면 임의로 범위를 확장하지 말고 해당 지점에서 멈춰 보고한다.
```

Start 전 확인(2026-10-19 14:06 UTC): main HEAD `e79a2cb214e6b6c11eddd753f2bf17ed7452f261`(기준선과 같음), tracked 변경 없음, untracked `jarvis.bat`과 이 기록.

## 범위 (Start 승인 시)

| 구분 | 경로 |
| --- | --- |
| owned | `scripts/check_task_record.py`(신규, C1~C6과 `--self-test`), `docs/jarvis-multi-agent-sop-v0.1.md`(§3 Manager의 task-0169 항목을 candidate 전 실행·종료 코드 규칙으로 교체), `memory/tasks/task-template.md`(owned 행 형식 한 줄), `.claude/skills/jarvis-reviewer-call/SKILL.md`(3단계 실행 명령을 새 스크립트로, allowed-tools 1개), 이 기록 |
| deny | `jarvis.bat`, `.env`, `scripts/check_summary_quotes.py`(재사용만), `orchestrator/discord-intake/task_file_writer.py`·`apps/jarvis-console/run_web_app.py`(import만), `.claude/agents/reviewer.md`, `.codex/agents/*.toml`, `scripts/validate_multi_agent_sop.py`(대조 값이 바뀌지 않으면), 다른 task 기록, `docs/master-plan.md`(Complete 뒤) |

비범위: Reviewer·QA 역할, repair 예산, SOP §8, 승인 절차, git hook 설치(D1 (b)), Worker 파이프라인 기록, push, worktree·smoke 정리.

## 검증 계획

| # | 사례 | 기대 |
| --- | --- | --- |
| T1 | 정상 기록(새 기록, owned에 신규 스크립트·문서, 줄바꿈 있음) | 종료 코드 0 |
| T2 | 메타데이터 줄 형식 오류 | C1 위반, 종료 1 |
| T3 | summary 안 백틱(task-0168 형태) | C2 위반(Console `invalid_text`), 종료 1 |
| T4 | owned 밖 파일 stage | C3 위반과 파일 목록 |
| T5 | 정상 신규 파일·문서 변경, 디렉터리 접두어 owned | 통과 |
| T6 | 기록 본문만 바꾸고 `updated_at` 그대로 | C4 위반. 새 기록은 통과 |
| T7 | 파일 끝 줄바꿈 없음 | C5 위반 |
| T8 | 인용 누락 | C6 참고 출력만, 종료 코드에 영향 없음 |
| T9 | 과거 기록 재현: task-0160~0170 기록과 각 candidate 범위로 돌려 실제 지적(0164·0170 범위, 0168 백틱, 0170 `updated_at`, 0161 줄바꿈)이 잡히는지, 정상 기록이 막히지 않는지 | 결과를 그대로 기록 |
| T10 | 기존 회귀 | task-0169 self-test, SOP validator, discord-intake smoke, Console smoke, `check_no_secrets`, `git diff --check` |

## 구현

| 파일 | 변경 |
| --- | --- |
| `scripts/check_task_record.py` | 신규. `git show :<기록>`(staged)과 `git diff --cached --name-only <baseline>`을 대상으로 C1 `_transition_metadata`, C2 `parse_task_view_text`, C3 `owned` 행 대조(경로와 `/`로 끝나는 디렉터리; `*` 패턴은 어떤 파일도 덮지 않음(repair 1); 이 기록 자신은 허용; 백틱 안이라도 `/`·`*`·확장자가 없는 이름은 경로로 보지 않음; 바뀌지 않은 owned 경로는 경고), C4 HEAD 대비 `updated_at`, C5 파일 끝 줄바꿈, C6 `check_summary_quotes.check_text` 참고 출력. 위반마다 `fix:` 줄. 종료 코드 0/1/2. `source_command: /task` 기록은 종료 2. `--json`, `--self-test`(임시 git 저장소, repair 1 뒤 14건, repair 2 뒤 16건). 변경 목록은 `--no-renames`로 얻는다(repair 2) |
| `docs/jarvis-multi-agent-sop-v0.1.md` | §3 Manager의 task-0169 항목을 "candidate(repair 포함) 커밋 전 staged 상태로 실행, 종료 코드 0이 아니면 candidate를 만들지 않음, 인용 목록은 참고"로 교체 |
| `memory/tasks/task-template.md` | 맨 위 주석 한 줄: 수동 SOP task 범위 표의 `owned` 행 형식 |
| `.claude/skills/jarvis-reviewer-call/SKILL.md` | 3단계 실행 명령을 새 스크립트로(BLOCKED면 호출문을 만들지 않음, 인용 목록은 그대로 전달), allowed-tools 1개 교체 |

`scripts/check_summary_quotes.py`, `task_file_writer.py`, `run_web_app.py`는 import만 하고 바꾸지 않았다. git hook은 설치하지 않았다(D1).

## Implementer 검증 (작업 트리 기준, candidate 전)

| # | 검사 | 결과 |
| --- | --- | --- |
| T1·T5 | 새 기록 + 신규 파일 + `docs/guide/` 디렉터리, 함수 이름 백틱 | PASS(종료 0), `run_tool`은 owned 경로로 읽지 않음. repair 1 뒤: `docs/*.txt` 패턴은 `docs/notes.txt`를 덮지 않아 C3 |
| T2 | 메타데이터 줄 형식 오류 | C1 |
| T3 | summary 안 백틱(task-0168 형태) | C2 |
| T4 | owned 밖 파일 stage | C3, 파일 이름 출력 |
| D2 | owned 행 없음 | C3 "no `\| owned \|` row" |
| T6 | 기록 변경 + `updated_at` 그대로 / 새 값 | C4 / PASS. HEAD에 없는 새 기록은 C4 대상 아님 |
| T7 | 파일 끝 줄바꿈 없음 | C5 |
| T8 | 인용 누락 | 참고 목록만, 종료 0 |
| 기타 | stage 안 된 기록 / Worker 경로 기록 | 종료 2 |
| 변형 | C1·C2·C3(범위 밖)·C3(행 없음)·C4·C5를 각각 끄거나 C6을 차단으로 바꾸면 | 7가지 모두 self-test 실패(검사가 실제로 잡음) |
| T9 | task-0160~0170 기록을 바꾼 커밋 48개(검사 49회, `beb2b92`는 두 기록을 함께 바꿈)를 그 시점 그대로(HEAD = 부모, index = 그 커밋, 임시 clone) 재현 | 아래 표 |
| T10 | (candidate 1 기준) `check_task_record --self-test` 13/0, `check_summary_quotes --self-test` PASS, SOP validator PASS, discord-intake smoke 146/0, Console smoke 통과, `git diff --check` 통과, 변경 파일 `check_no_secrets` 0건, self-test 임시 폴더 남지 않음 | 통과 |

template을 canonical parser에 넣으면 `task_file_invalid_id`인데, 수정 전 HEAD의 template도 같다(자리표시 id). 이번 변경과 무관하다.

### T9 과거 사례 재현 결과

| 구분 | 커밋 | 결과 |
| --- | --- | --- |
| Reviewer가 실제로 지적한 기록 문제 | task-0161 `0abdf86`(파일 끝 줄바꿈), task-0168 `c77897e`(summary 백틱, Console Complete 실패), task-0170 `5cc55cc`(`updated_at` 미갱신, QA Q10) | 세 건 모두 잡음(C5, C1·C2, C4) |
| 지적되지 않았던 §7 위반 | task-0164 `922712f`·`42c126c`, task-0165 `9546e3a`·`e57fed0`, task-0167 `bf87a66`(`updated_at`), task-0167 `5cff917`(줄바꿈) | 잡음 |
| 정상 candidate | task-0160 `d77c01c`, 0162 `10f7904`, 0163 `dcd69d8`, 0164 `6faffb7`·`bfdbce9`·`7003cb5`, 0165 `5f79152`, 0167 `ad79cee`·`429d5c8`, 0169 `c7ff349`, 0170 `0fc1236` 등 | PASS(오차단 없음) |
| owned 행 없는 기록 | task-0168 전 커밋 | C3(D2 결정대로 차단 대상) |
| candidate가 아닌 시점 | task-0169 DONE checkpoint `8e93fea`(별도 커밋한 master-plan이 baseline 이후에 있음), task-0167 기록을 바꾼 task-0168 커밋 3건 | C3. 이 검사는 candidate 전용이라 SOP에 "candidate(repair 포함) 커밋 전"으로 적었다 |
| 잡지 못한 것 | task-0170 F1(summary 의미), F2(owned 설명 문구 — 파일 단위로는 일치), task-0162 정의 문제, Manager 요약의 조건 누락(C6 참고 목록에만 나옴) | Reviewer 몫(M9) |

## Candidate 1

`1c74364c60baf5a0de7c3129a4c09a9e83459868` (parent = baseline `e79a2cb`). 커밋 전 이 task의 사전 점검(staged 5개) 위반 0, 종료 0.

## Reviewer 1 (`1c74364`, 유효, FINDINGS minor 4)

| # | 지적 | repair 1 처리 |
| --- | --- | --- |
| F1 | Skill 3단계가 스크립트 결과를 그 candidate의 결과처럼 쓰지만 스크립트는 index와 HEAD만 읽는다 | Skill: HEAD가 candidate이고 staged 변경이 없을 때만 유효, 아니면 BLOCKED |
| F2 | Skill이 `status=ERROR`(종료 2)를 다루지 않는다 | Skill: 0이 아닌 종료(BLOCKED·ERROR)는 모두 호출 중단 |
| F3 | C3의 `*` 패턴 매칭(fnmatch, `/`도 넘음)이 등록 설계("경로, `/`로 끝나는 디렉터리")보다 넓다 | 스크립트에서 패턴 매칭 제거. `*` 토큰은 어떤 파일도 덮지 않음. self-test에 그 경우 추가(14건) |
| F4 | 기록의 M2·M12가 Start 뒤에도 그대로이고 M10이 T1~T9 | M2·M12에 S4 대체 표시, M10을 T1~T10으로 |

`self_deviations` 없음. `unverified` 6건(T10 결과, T9 재현, `shutil.rmtree(onexc=…)`의 Python 3.12 의존, SOP validator, `run_web_app` import 부작용, hook·push 없음)은 QA에서 확인한다.
repair는 Manager가 예산 안에서 진행했다(`repair_count=1`, 예산 1 소진).

## Candidate 2 (repair 1)

`0d4a05d7fba27808c7394cb1ff4dd005529f42f2` (parent `1c74364`). Candidate 1의 Reviewer 결과는 무효.

### repair 1 뒤 실제 결과 (candidate 2 커밋 전, 작업 트리·staged 기준)

| 검사 | 결과 |
| --- | --- |
| `check_task_record --self-test` | checks=14, failures=0 |
| T9 재현 | 49회 출력이 candidate 1 때와 한 줄도 다르지 않음 |
| SOP validator | PASS |
| discord-intake smoke | failed 0 |
| `git diff --cached --check` | 통과 |
| 사전 점검 | violations=0, status=PASS(그 실행에서는 staged 파일 수를 출력하지 않음) |
| Console smoke, `check_summary_quotes --self-test`, `check_no_secrets` | 이 시점에는 다시 실행하지 않음 |

## Reviewer 2 (`0d4a05d`, 유효, FINDINGS minor 2)

| # | 지적 | 처리 |
| --- | --- | --- |
| G1 | C3 변경 목록의 `git diff --cached --name-only`에 `--no-renames`가 없어 파일 이동은 새 경로만 비교되고 결과가 `diff.renames` 설정에 따라 달라진다 | Manager가 저장소 밖 임시 저장소에서 사실 확인(기본 설정은 새 경로만, `--no-renames`는 두 경로). repair 예산 소진으로 Owner에게 보고 |
| G2 | 기록 T10이 "self-test 13/0"으로 남고 repair 1 뒤 실제 결과가 없다 | 위 "repair 1 뒤 실제 결과" 표 |

`self_deviations` 없음. Owner가 repair 예산을 2로 늘리고 두 건 수정을 승인했다(아래 원문).

## Owner 결정: repair 예산 증액 1→2 (원문)

```text
task-0171의 repair 예산을 기존 1회에서 총 2회로 늘리는 것을 승인한다.
Reviewer 2의 minor 지적 2건을 모두 수정해.

1. C3 파일 이동 결함
   * 변경 파일 목록을 얻는 Git 명령에 `--no-renames`를 적용해 파일 이동 전후 경로가 모두 검사되도록 한다.
   * 범위 밖 파일을 `owned` 경로로 이동하는 사례를 self-test에 추가한다.
   * Git 설정에 따라 검사 결과가 달라지지 않는지 확인한다.
2. 작업 기록 갱신
   * task-0171 기록의 T10 및 관련 검증 항목에 repair 1 이후 실제 결과를 반영한다.
   * self-test 14/0, T9 재현 결과, validator, intake smoke, diff 검사, 사전 점검 결과를 실제 실행 로그와 대조해 기록한다.
3. 검증 및 완료
   * 변경 후 사전 점검을 통과한 경우에만 candidate를 생성한다.
   * 새 candidate hash를 고정해 Reviewer를 다시 호출하고, 이후 QA와 기존 완료 절차를 진행한다.
   * 남은 지적이 있으면 임의로 추가 repair하거나 SOP §8로 수용하지 말고 중단해 보고한다.
   * 기존 승인·검증 정책은 유지한다.
4. 보호 사항
   * `jarvis.bat`은 건드리지 않는다.
   * push는 하지 않는다.
   * 다른 worktree와 smoke 임시 폴더는 건드리지 않는다.
   * task 기록을 직접 DONE으로 변경하지 않는다. Console Complete 절차를 사용한다.

완료 보고에는 최종 테스트 결과, Reviewer·QA 판정, checkpoint 커밋, Console Complete 상태, main과 origin/main의 차이를 포함해라.
```

budget: `repair_budget=2`(Owner 증액), `repair_count=2`(이 repair 뒤).

## Repair 2

| 파일 | 변경 |
| --- | --- |
| `scripts/check_task_record.py` | C3 변경 목록에 `--no-renames`. self-test 2건 추가: 범위 밖 `README.md`를 owned 디렉터리로 `git mv`하면 원래 경로로 C3, `diff.renames`가 true·false·copies일 때 판정이 같음 |
| 이 기록 | summary·`updated_at`, T10 행 시점 표시, repair 1·2 실제 결과, Reviewer 2, Owner 결정 원문, R1~R3 요약 행 |

### repair 2 뒤 실제 결과 (candidate 3 커밋 전)

| 검사 | 결과 |
| --- | --- |
| `check_task_record --self-test` | checks=16, failures=0. 변형: `--no-renames`를 빼면 새 검사 2건이 실패(설정에 따라 `[]`와 C3로 갈림) |
| `check_summary_quotes --self-test` | checks=16, failures=0 |
| T9 재현 | 49회 출력이 candidate 1 때와 같음 |
| SOP validator | PASS(negative 133, 실패 0) |
| discord-intake smoke | total 146, failed 0 |
| Console smoke | 통과 |
| `git diff --check` | 통과 |
| `check_no_secrets`(`scripts/check_task_record.py`) | findings 0 |
| self-test 임시 폴더 | 남지 않음(0) |
| Python | 3.12.10(`shutil.rmtree(onexc=…)` 지원) |

## Candidate 3 (repair 2)

`d7d1d84715dccc3b37d6fc58bdb2ef5999acae20` (parent `0d4a05d`). Candidate 2의 Reviewer 결과는 무효.

| 검사 | 결과(실행 로그 그대로) |
| --- | --- |
| candidate 3 커밋 전 사전 점검 | 1차: `staged_files=5`, `violations=0`, `status=PASS`, `preflight_exit=0`. 2차(확인되지 않은 수치 문구를 고친 뒤): `violations=0`, `status=PASS`, `exit=0` |

## Reviewer 3 (`d7d1d84`, 유효, FINDINGS minor 1)

| # | 지적 | 처리 |
| --- | --- | --- |
| H1 | "repair 2 뒤 실제 결과" 표에 candidate 3 커밋 전 사전 점검 결과가 없고 "Candidate 3" 절도 없다 | repair 3: 위 "Candidate 3 (repair 2)" 절과 사전 점검 행 추가(기록만) |

`self_deviations` 없음. 코드·SOP·Skill·template 지적 없음. repair 예산 2회 소진으로 Owner에게 보고했고 Owner가 예산을 3으로 늘려 H1만 고치도록 승인했다(아래 원문).

## Owner 결정: repair 예산 증액 2→3 (원문)

```text
Owner 결정: 선택지 1 승인. repair 예산을 총 3회로 한정해 증액합니다. 이번 repair는 Reviewer 3의 H1(minor, 기록 누락)만 수정합니다.

1. 실행 로그로 확인된 candidate 3 사전 점검 결과를 task-0171 기록에 한 행으로 추가하세요.
   * 1차: `staged_files=5`, `violations=0`, `status=PASS`, `preflight_exit=0`
   * 2차: `violations=0`, `status=PASS`, `exit=0`
   * 2차 실행에서 확인되지 않은 staged 파일 수는 기재하지 마세요.
2. 기록 수정 후 preflight를 다시 실행하고 PASS 여부를 확인하세요.
3. 새 Reviewer 검토를 진행하세요.
4. Reviewer가 PASS하면 QA를 진행하고, 기존 SOP에 따라 checkpoint와 Console Complete까지 진행하세요.
5. 이번 증액은 총 repair 3회 한도입니다. 추가 FINDINGS가 나오면 임의로 더 수정하거나 SOP §8로 수용하지 말고 중단해 보고하세요.
6. 코드·SOP·Skill·template은 변경하지 마세요. 기존 검증 결과를 재사용할 수 있는 경우 불필요하게 반복하지 말고, 이번 변경에 필요한 검증만 수행하세요.
7. `jarvis.bat`은 열람·수정·스테이징하지 마세요. 다른 worktree와 임시 폴더도 건드리지 마세요.
8. `git push`는 하지 마세요. task 파일을 직접 DONE으로 바꾸지 말고 Console의 공식 Complete 절차를 따르세요.

수정·검증 결과와 최종 Git 상태를 보고하세요.
```

budget: `repair_budget=3`(Owner 증액), `repair_count=3`(이 repair 뒤). repair 3은 이 기록만 바꾼다.

| 검사 | 결과(실행 로그 그대로) |
| --- | --- |
| candidate 4(repair 3) 커밋 전 사전 점검 | 이 표를 쓰기 전: `staged_files=5`, `violations=0`, `status=PASS`, `preflight_exit=0`. 이 표를 쓴 뒤 다시 실행해 같은 판정(`violations=0`, `status=PASS`, 종료 0)이 나온 것을 확인하고 커밋했다. discord-intake smoke failed 0 |

## Reviewer 4 (`969f53b`, 유효)

| 항목 | 내용 |
| --- | --- |
| 호출 | 전체 hash, baseline `e79a2cb`, commit 구조(candidate 1~3 무효), file scope 5개, evidence 5개, Manager 요약(M1~M13·S1~S5·R1~R5)과 승인 원문 네 블록 |
| verdict | PASS, findings `[]`, `self_deviations` `[]` |
| unverified | candidate 3·4 사전 점검 결과, 테스트 결과, C1·C2·C5 실행, hook·push·보호 대상 무접촉 → 아래 QA |
| budget | `retry_count=0`, `repair_count=3`(예산 3, 소진) |

## QA (candidate `969f53b94726da605a7880331451656fde29846d`)

main HEAD = candidate, staged 변경 없음, tracked 변경 없음(untracked `jarvis.bat`만)에서 실행했다. repair 3은 이 기록만 바꿨다(`git diff --name-only d7d1d84 969f53b` = 이 기록 1개). 그래서 코드에만 걸리는 T9 재현은 repair 2 뒤 결과(49회, candidate 1과 같음)를 재사용했다.

| # | 검사 | 결과 |
| --- | --- | --- |
| Q1 | 사전 점검(이 기록, baseline `e79a2cb`) | `staged_files=5`, `violations=0`, `status=PASS`, 종료 0 |
| Q2 | `check_task_record --self-test` | checks=16, failures=0 |
| Q3 | `check_summary_quotes --self-test` | failures=0 |
| Q4 | SOP validator | PASS |
| Q5 | discord-intake smoke | total 146, failed 0 |
| Q6 | Console smoke | 통과 |
| Q7 | `git diff --check e79a2cb 969f53b` | 통과 |
| Q8 | `jarvis.bat` | candidate tree에 없음, 작업 트리 untracked 그대로 |
| Q9 | git hook | `.git/hooks`에 `.sample` 아닌 파일 0개(D1: hook 없음) |
| Q10 | `check_no_secrets`(baseline..candidate 변경 파일) | findings 0 |
| Q11 | self-test 임시 폴더 | 남지 않음(0) |
| Q12 | T9 재현 | 재사용(위 사유). 실제 지적 0161 줄바꿈·0168 백틱·0170 `updated_at`을 잡고 정상 candidate는 막지 않음 |

판정: QA PASS. DONE은 Owner Console Complete로만 한다. push 없음.
