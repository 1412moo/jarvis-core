# task-0138-studyroom-content-expansion

- id: `task-0138-studyroom-content-expansion`
- title: `Studyroom 더블클릭 실행기와 콘텐츠 확장(Recordroom·Glossary·Learn·Technologies·Features) 사후 기록`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-09-23 15:29 UTC`
- updated_at: `2026-09-23 15:29 UTC`
- summary: `2026-09-23에 task 기록 없이 진행된 Studyroom 작업 6개 단위(더블클릭 실행기, Recordroom 26건, Glossary 47개, Learn 18개, Technologies 11개, Features 11개)의 사후 기록이다. 15개 commit(45b6926부터 887daa9까지)의 범위, Owner 승인 원문, 최종 candidate, Reviewer/QA 결과, repair/retry 이력과 수용한 minor를 정리한다. 이 기록 작성 자체는 문서 전용이라 다른 파일은 바꾸지 않으며, DONE은 Reviewer/QA 후 Owner가 Console Complete로 결정한다.`
- source_command: `Owner 지시: 오늘 Studyroom 콘텐츠 확장 작업의 사후 task 기록을 task-0138 하나로 남긴다`

## 왜 사후 기록인가

2026-09-23 세션에서 Studyroom 관련 commit 15개가 만들어지고 push됐지만 대응하는 task 기록이
없었다. Recordroom에 적은 rec-0018(task 파일 없이 병합된 구현을 사후 기록한 사건)과 같은 모양이라,
같은 방식으로 공백을 지우지 않고 사후 기록임을 밝혀 남긴다.

근거의 위치는 두 가지다.

| 근거 | 위치 |
| --- | --- |
| commit hash, 변경 파일, 줄 수, repair 사유 | git 기록(commit 메시지 포함) |
| Owner 승인 원문, Reviewer·QA 결과, Reviewer agent ID | 2026-09-23 Claude Code 세션 대화. 저장소 파일에는 없어 이 기록에 원문 그대로 옮긴다 |
| QA 검사 스크립트 | 세션 scratchpad 임시 파일. 저장소에 없으며 이 기록에는 확인 항목과 결과만 남긴다 |

## 기준선과 범위

| 항목 | 값 |
| --- | --- |
| 기준선 | `08bcfab781f4634a9fca38bb9f9b08c282b9bbf6` (task-0135 DONE 전환 commit) |
| 최종 commit | `887daa91893426961668f233dae6ce05cb7b0470` |
| commit 수 | 15 (commit 시각은 2026-09-23 15:00~23:39 +0900) |
| 변경 파일 | `apps/studyroom/run_web_app.py`, `apps/studyroom/studyroom.bat`(신규), `apps/studyroom/README.md`, `apps/studyroom/content/recordroom.json`, `glossary.json`, `learn.json`, `technologies.json`, `features.json` (8개, +1093/−17) |
| 변경하지 않은 것 | `apps/studyroom/web/*`(UI), 각 JSON 스키마, `jarvis.bat` |

## 작업 단위별 기록

### 1. 더블클릭 실행기

| 항목 | 값 |
| --- | --- |
| commit | `45b6926f41e62155d7d4978a8b3c94a24105c5f2` (최종 candidate) |
| 변경 | `run_web_app.py`에 서버 bind 후 `webbrowser.open`과 `--no-browser` 추가, Windows에서 `allow_reuse_address`를 끄는 `StudyroomServer` 추가 / `studyroom.bat` 신규 / README 4절 실행 방법 갱신 |
| Reviewer | `45b6926` PASS, findings 0 (agent `abf7146d49798d1a9`) |
| QA | PASS — HEAD 일치, 3개 파일, smoke 5/5, bat 실행 시 GET / 200, 브라우저 호출 확인(BROWSER 환경변수로 가로챔), 포트 사용 중 두 번째 서버 exit 1(WinError 10048), 종료 후 8080 listener 0 |
| repair / retry | 0 / 0 |
| push | `08bcfab..45b6926` |

구현 중 사실: 첫 포트 테스트에서 Windows는 `SO_REUSEADDR` 때문에 8080이 사용 중이어도 두 번째
서버가 bind됐다. 승인 조건 "사용 중이면 오류"를 맞추려고 Windows에서 이 옵션을 껐고, 원래 제안에
없던 변경이라 Reviewer 요약에 명시했다. 이 테스트가 남긴 서버 프로세스 1개를 종료했다.
제안 조사 중 보호 파일 `jarvis.bat`의 앞부분을 읽었다(`docs/codex-operating-rules.md`의 "명시적 별도
요청 없이는 열지 않는다" 위반). 수정·stage는 하지 않았고 당시 Owner에게 보고했다.

Owner 승인 원문:

```text
이 범위로 진행해.

- `apps/studyroom/run_web_app.py`: 브라우저 자동 실행 + `--no-browser`
- `apps/studyroom/studyroom.bat`: 추가
- README 실행 방법 업데이트
- bat 위치는 `apps/studyroom/`
- 포트는 8080 고정, 사용 중이면 오류
- `jarvis.bat`은 절대 건드리지 말 것

SOP대로 Implementer → Reviewer → QA 진행해.
결과는 필요한 내용만 짧게 보고해.
```

```text
push해
```

### 2. Recordroom (5 → 26건)

| candidate | 내용 | Reviewer |
| --- | --- | --- |
| `a482b2e945773cbc2ae3d71ae6467aedc7f58be2` | 26건 타임라인. rec-0001~0004 유지, rec-0005를 Console 축소 전체로 확장, rec-0006~0026 추가 | FINDINGS major 1, minor 3 (agent `acb22e65919e60cb5`). major: git만 근거인 rec-0007에 기록에 없는 교훈과 인과 연결 |
| `66c7dd5495bb386954efca81e316f659fe6e35a9` | repair 1: 교훈 7곳을 기록된 사실로 고침 | FINDINGS minor 5 (agent `aa6419e698e051b99`). 내용: rec-0025 교훈 출처(task-0125), rec-0006의 AGENTS.md 원칙 8 연결 |
| `5386fe544b525025fa7d3dd3cb2960d00dad13bb` | repair 2: 두 출처만 수정 | PASS, findings 0 (agent `ab9f640d83bbd282f`) |

QA(`5386fe5`) PASS — 26건, 스키마 키 동일, 날짜순, rec-0001~0004 기준선과 동일, learn.json 참조 5건 유효,
commit hash 18개 존재, 인용 commit 제목 7개 일치, 비병합 commit 수 21·31·68·116 일치, 링크 경로 전부 존재,
화면 카드 26개와 콘솔 오류 0, smoke 5/5. task-0062·0063은 task 파일이 없고 rec-0021에서 task-0064 기록의
인용으로만 언급된다.
repair 2 / retry 0 (repair budget 1 → Owner 승인으로 2). push `45b6926..5386fe5`.

Owner 승인 원문:

```text
26건 전체를 Recordroom 타임라인으로 반영해.

기존 5건의 ID는 유지하고 새 항목은 rec-0006부터 추가해.
시간순으로 정렬하고, 기존 JSON 스키마와 UI는 변경하지 마.

Git만 근거인 사건은 Git에서 확인된 사실만 쓰고, task 기록이 없다는 점을 필요하면 명시해.
실수·폐기·실패·방향 전환도 제외하지 말고, 실제 기록에 있는 교훈과 그 결과 생긴 규칙을 함께 기록해.
추측이나 과장은 금지하고 비밀값/개인 경로/세션 URL은 제외해.

수정 후 Reviewer → QA까지 진행하고,
나한테는 PASS/FINDINGS와 핵심 내용만 보고해.
```

```text
1번으로 진행해.
두 출처 오류만 수정하고 Reviewer → QA까지 진행해.
다른 내용은 수정하지 마.
```

```text
push 해
```

### 3. Glossary (15 → 47개)

| candidate | 내용 | Reviewer |
| --- | --- | --- |
| `32319dc66a6587661a8da741cb1fdaef364a356a` | 32개 추가(제안 30개에서 Implementer/Reviewer/QA 분리) | FINDINGS minor 8 (agent `a00adbee64a5424a7`). 내용 5건: 22b7398이 AGENTS.md를 수정(추가 아님), header-block 인용 비원문, escalation 인용 띄어쓰기, structured-field 이관 범위, approval-binding validator 대상 |
| `ab01158b403f2ff7c1c0ab542aa691ef31bebcbc` | repair 1: 위 5건 수정 | FINDINGS minor 4, 전부 Manager 요약·검증 범위 (agent `a8f575bcf19688b42`) → 요약만 고쳐 retry → PASS (agent `af8d741271ee6d3c6`) |
| `929d8b546d628bc9f788ddd3bc1b675df57f69c3` | repair 2: protected-file 인용의 백틱 2개 복구 | FINDINGS minor 3, 전부 Manager 요약 (agent `a467d20b79e815405`) → Owner 수용 |

QA(`ab01158`) FINDINGS minor 1 — protected-file 인용에서 `jarvis.bat` 주변 백틱 누락.
QA(`929d8b5`, 기준선 `5386fe5` 대비 누적) PASS — 47개, 기존 15개 동일, 새 32개 제안 순서, 키 5개, id 중복 0,
빈 필드 0, 인용 18개 전부 원문 일치, commit hash 6개 존재, 화면 카드 47개와 콘솔 오류 0, smoke 5/5.
task-0080은 task 파일이 없고 task-0081 기록의 인용으로만 언급된다.
repair 2 / retry 1 (repair budget 1 → Owner 승인으로 2). push `5386fe5..929d8b5`.

Owner 승인 원문:

```text
30개 전부 추가해.

Implementer / Reviewer / QA는 각각 별도 용어로 분리하고,
SO_REUSEADDR도 포함해. task 기록이 없는 경우 git 기록으로 확인되는 사실만 jarvis_example에 사용해.

기존 15개는 수정하지 말고,
glossary.json만 수정해. 스키마와 UI는 변경하지 마.

완료 후 Reviewer → QA까지 진행하고,
나에게는 PASS/FINDINGS와 핵심 내용만 보고해.
```

```text
1번으로 진행해.

QA FINDING의 백틱 2개만 정확히 복구하고,
다른 내용은 건드리지 마.

추가 repair 1회로 처리하고 Reviewer → QA 재진행해.
최종 결과는 PASS/FINDINGS와 핵심 내용만 보고해.
```

```text
2번으로 진행해.

summary minor 3건은 수용하고 바로 QA 진행해.
candidate 내용은 추가 수정하지 마.

QA에서는 전체 누적 변경(47개, 기존 15개 보존, 새 용어 32개, 인용/해시/스키마/화면/smoke)을 확인해.

최종 결과는 PASS/FINDINGS와 핵심 내용만 보고해.
```

```text
commit하고 push해.
```

### 4. Learn (10 → 18개)

| candidate | 내용 | Reviewer |
| --- | --- | --- |
| `5e579a106e76594682a4c70d46f512819790eb20` | 8개 추가, 퀴즈 각 1문제 | FINDINGS minor 4 (agent `af8e04944dfa22156`). 내용: README 한정어 누락(task-0123), Glossary와 거의 같은 문장 3곳 |
| `8bdc9b9530f306b1ea4367c98b99ad634cd0f29f` | repair 1: 위 내용 수정 | FINDINGS minor 4 (agent `a11f592f1b0e492dc`). 내용: task-0135 결과를 실제와 다르게 씀(계획을 결과로 옮김), Recordroom과 거의 같은 문장 2곳 |
| `87759b11c5b05dc851e722f13b3e09b62010dfc4` | repair 2: 위 3문장 수정 | FINDINGS minor 1 (agent `a501062c6e97af8af`). 내용: 새로 쓴 R3 문장이 task-0095와 다름(R3는 문서에서 고쳤고 R6만 별도 task) |
| `08af2371408d64d79f0d2092e672ff0c09e20d33` | repair 3: R3 문장 1개 수정 | FINDINGS minor 3, 전부 Manager 요약 (agent `a3c8edd7d2804d859`) → 요약만 고쳐 retry → FINDINGS minor 2, 전부 Manager 요약 (agent `a285a58f928f016ca`) → Owner 수용 |

QA(`08af237`, 기준선 `929d8b5` 대비 누적) FINDINGS minor 1 — learn-when-premises-break가 rec-0015와 59자 공통 구절
("2026-06-18 구글 정책 변경으로 Gemini Code Assist for individuals 계정"). Manager가 정한 기준은 40자였다.
나머지 PASS — learn.json만 변경, 기존 10개 바이트 동일, 새 8개, id 중복 0, 키 동일, 퀴즈 1문제·선택지 3개·유효 정답,
related_recordroom 전부 존재, 기존 learn-baseline-candidate 연결(rec-0004)은 지시대로 미수정, 화면 퀴즈 18개와
실제 정답 판정·저장 동작, 콘솔 오류 0, smoke 5/5. 화면 확인을 위해 테스트 포트(8093) origin의 localStorage를 비웠다.
Owner가 QA minor를 수용했다. repair 3 / retry 1 (repair budget 1 → Owner 승인으로 2 → 3). push `929d8b5..08af237`.

Owner 승인 원문:

```text
Learn 8개 전부 추가해.

범위:
- learn.json만 수정
- 기존 Learn 10개는 수정하지 마
- 새 항목 8개
- 각 항목 퀴즈는 기존 형식대로 1문제
- related_recordroom은 실제 Recordroom ID와 정확히 연결
- 기존 Glossary/Recordroom 내용과 중복을 최소화

이번 작업에서는 기존 learn 항목의 잘못된 related_recordroom이나 기존 퀴즈 수는 수정하지 마.

완료 후 Reviewer → QA까지 진행하고,
나에게는 PASS/FINDINGS와 핵심 내용만 보고해.
```

```text
1번으로 진행해.

repair 1회 추가 승인한다.
- learn-review-verify-separation의 task-0135 실제 결과를 정확히 수정
- Recordroom과 중복되는 문장 2곳도 수정
- 다른 내용은 건드리지 마

수정 후 fresh Reviewer → QA 진행해.
최종 결과는 PASS/FINDINGS와 핵심 내용만 보고해.
```

```text
1번으로 진행해.

repair 1회 추가 승인한다.
learn-docs-drift의 해당 한 문장만 실제 기록에 맞게 수정해:
"R3는 문서에서 주석과 함께 고쳤고, 원인인 코드 버그(R6)는 별도 task로 남겼다."

다른 내용은 건드리지 마.
수정 후 fresh Reviewer → QA 진행해.

최종 결과는 PASS/FINDINGS와 핵심 내용만 보고해.
```

```text
1번으로 진행해.

summary minor 2건은 수용하고 바로 QA 진행해.
candidate 내용은 추가 수정하지 마.

QA에서 기준선 대비 전체 누적 변경을 확인해:
- 기존 Learn 10개 보존
- 새 항목 8개
- 퀴즈 형식
- Recordroom 연결
- 기존 콘텐츠와 중복 여부
- JSON/schema
- smoke test
- Studyroom 화면

최종 결과는 PASS/FINDINGS와 핵심 내용만 보고해.
```

```text
1번으로 확정해.

QA minor 1건은 수용하고 candidate는 수정하지 마.
현재 candidate 그대로 commit하고 push해.

최종 결과는 commit hash와 push 결과만 간단히 보고해.
```

### 5. Technologies (4 → 11개)

| candidate | 내용 | Reviewer |
| --- | --- | --- |
| `a16a5efc74f0b55d90762cb4160c9d4787ca306d` | 7개 추가 | FINDINGS major 1, minor 1 (agent `a3eb3ae3c5063d00d`). major: OpenRouter 항목이 "golden 등 경로를 건드리지 않았다"고 썼으나 c7f2b99는 그 runner들을 수정해 LIVE를 막았음 |
| `bcdf5a197350beec73db6fbecf946c2576069d67` | repair 1: task-0029 Boundary 표 기준으로 문장 수정 | PASS, findings 0 (agent `ac71a026d5cebc15f`) |

QA(`bcdf5a1`, 기준선 `08af237` 대비 누적) PASS — technologies.json만 변경, 기존 4개 동일, 새 7개, 키 4개,
commit hash와 task 파일·참조 경로 존재, 최장 공통 구절 36자, 화면 카드 11개와 콘솔 오류 0, smoke 5/5.
repair 1 / retry 0. push `08af237..bcdf5a1`.

Owner 승인 원문:

```text
Technologies도 같은 방식으로 추가해
```

```text
push 해
```

### 6. Features (5 → 11개)

| candidate | 내용 | Reviewer |
| --- | --- | --- |
| `f96aef1792f9409b195270fb1d92bd59db66d318` | 6개 추가 | FINDINGS major 1, minor 4 (agent `aa32752b240517b52`). major: a54316f를 P2-1로 표기(실제 P2-1은 사후 provenance 기록). minor 내용: validator가 모순 문장도 검사함, 근거 없는 "구현 요청 전에", Buzz 결정 출처 |
| `887daa91893426961668f233dae6ce05cb7b0470` | repair 1: 위 4건 수정 | PASS, findings 0 (agent `a6eebf72fcbf34c0b`) |

QA(`887daa9`, 기준선 `bcdf5a1` 대비 누적) PASS — features.json만 변경, 기존 5개 동일, 새 6개, 키 6개,
related_tasks 전부 task 파일 존재, commit hash 5개와 참조 경로 존재, 최장 공통 구절 36자,
화면 카드 11개와 콘솔 오류 0, smoke 5/5.
repair 1 / retry 0. push `bcdf5a1..887daa9`.

Owner 승인 원문:

```text
Features도 같은 방식으로 추가해
```

```text
push 해
```

## 이력 요약

| 단위 | 최종 candidate | repair | retry | Owner가 수용한 minor |
| --- | --- | --- | --- | --- |
| 실행기 | `45b6926` | 0 | 0 | 없음 |
| Recordroom | `5386fe5` | 2 | 0 | 없음 |
| Glossary | `929d8b5` | 2 | 1 | Reviewer 요약 minor 3 |
| Learn | `08af237` | 3 | 1 | Reviewer 요약 minor 2, QA 59자 공통 구절 1 |
| Technologies | `bcdf5a1` | 1 | 0 | 없음 |
| Features | `887daa9` | 1 | 0 | 없음 |

반복된 문제로 기록에 남은 것: Reviewer FINDINGS 다수가 Manager 요약의 승인 조건 누락과, Implementer가 원문과
다르게 쓴 사실 서술(계획을 결과로 옮김, 한정어 누락, 출처 혼동)이었다. 여러 Reviewer가 기준선 대비 누적 diff와
`git show <hash>:<path>`를 허용 명령으로 실행할 수 없어 누적 확인을 QA로 넘겼다.

## 이 기록 작업의 Owner 승인 원문

```text
세 가지 모두 권장안으로 진행해.

1. 실행기 45b6926 포함.
2. task-0138은 DOING으로 생성하고, 검증 후 Console Complete로 DONE 처리.
3. 작업 단위별 Owner 승인 원문은 전부 원문 그대로 기록.

제안한 구성대로 task-0138만 새로 만들고,
다른 파일은 수정하지 마.

summary는 500자 이내, 백틱 없이 작성해.
기록에 없는 사실은 추측하지 마.

작성 후 Reviewer → QA까지 진행하고,
최종 결과는 PASS/FINDINGS와 핵심 내용만 보고해.
```

## 비범위

- Studyroom 코드·콘텐츠·UI 추가 수정
- task-0137 수정(Console에서 METADATA_REVIEW로 표시됨)
- learn-baseline-candidate의 related_recordroom(rec-0004) 수정, 기존 Learn 퀴즈 수 확장
- Reviewer 정의·허용 명령·validator 변경

## 후속 task 후보

- Reviewer 허용 명령에 기준선 대비 누적 diff와 `git show <hash>:<path>` 허용 여부 결정 (task-0135 후속 과제와 같은 주제)
- task-0137 header metadata 수정
- learn-baseline-candidate의 related_recordroom 연결 수정
- Reviewer 호출 조립에 jarvis-reviewer-call Skill(task-0136) 사용
