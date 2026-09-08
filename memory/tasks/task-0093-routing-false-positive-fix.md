# task-0093-routing-false-positive-fix

- id: `task-0093-routing-false-positive-fix`
- title: `suggest_skill 부분문자열 라우팅 오탐 수정`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-08 05:10 UTC`
- updated_at: `2026-09-08 05:10 UTC`
- summary: `Chat/Command 에서 report 를 입력하면 tasks_reports 가 아니라 Hermes Manager 를 추천받던 문제를 고쳤다. suggest_skill 이 route keyword 를 단순 부분문자열로 매칭해 hermes 의 pr 이 approval 안에, repo 가 report 안에 걸렸고, 부분문자열 hit 가 정확한 hit 와 동점이 되면서 ROUTING_PRIORITY 0 인 hermes 가 항상 이겼다. ASCII keyword 에 토큰 경계를 적용해 매칭 규칙 자체를 고쳤고 한글 keyword 는 기존 의미를 보존했다. 목표 18/18 일치, Voice broad-hit 방어 6/6 보존, 기존 routing assert 19건 무손상. 구현 커밋 8bbd019, 변경 파일은 run_web_app.py 와 run_smoke_tests.py 둘뿐이다.`
- source_command: `routing 오탐 read-only 조사 후 옵션 D 채택 구현 지시`

## Scope

라우팅 **매칭 규칙만** 고쳤다. keyword 데이터, 우선순위, API 계약, Voice 정책은
건드리지 않았다.

| 항목 | 값 |
| --- | --- |
| 조사 기준선 | `4871243` |
| 구현 커밋 | **`8bbd019`** — `fix(console): prevent substring routing false positives` |
| 구현 커밋 부모 | `4871243` |
| 변경 파일 | `apps/jarvis-console/run_web_app.py`, `apps/jarvis-console/run_smoke_tests.py` — **이 둘뿐** |
| 변경 규모 | 2파일, **+92 / -1** |

## 문제

Chat/Command 탭에서 `report` 를 입력하면 `Tasks / Reports` 가 아니라
`Hermes Manager` 를 추천받았다. `tasks_reports` 에 `report` 가 **정확한 keyword 로
등록되어 있는데도** 그랬다.

같은 질의가 Voice 경로에서는 `unknown` 을 반환해, **진입점에 따라 답이 달라지고
Chat 쪽이 틀린 답을 줬다.**

## 원인 — 두 요소의 결합

### 1. ASCII keyword 부분문자열 매칭

```python
hits = [keyword for keyword in keywords if keyword in normalized]
```

`hermes_manager` 의 2글자 `pr` 이 `a`**pr**`oval`, `re`**pr**`oduce`, **pr**`int`,
**pr**`epare`, **pr**`ocess`, **pr**`ogress`, **pr**`iority` 안에 걸렸다.
4글자 `repo` 는 `report` 안에 걸렸다.
`research_council` 의 `idea` 는 `ideal` 안에, `tasks_reports` 의 `task` 는
`multitask` 안에 걸렸다.

### 2. 동점 시 ROUTING_PRIORITY 가 결정

```python
candidates.append((len(hits), -priority, skill, hits))
candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
```

`hermes_manager` 는 priority 0(최우선), `tasks_reports` 는 4다.

실측 계산:

```
입력 'report'
   hits=1 -priority=  0  hermes_manager   matched=['repo']      <- 부분문자열
   hits=1 -priority= -4  tasks_reports    matched=['report']    <- 정확 매칭
   => 선택: hermes_manager

입력 'approval'
   hits=1 -priority=  0  hermes_manager   matched=['pr']
   hits=1 -priority= -4  tasks_reports    matched=['approval']
   => 선택: hermes_manager

입력 'preview'
   hits=2 -priority=  0  hermes_manager   matched=['review', 'pr']
   => 선택: hermes_manager
```

**정확한 매칭이 부분문자열 매칭에 우선순위로 졌다.** 이것이 버그의 본질이다.

분기점: `/api/suggest-skill` 은 raw `suggest_skill()` 을 호출하고,
Voice 는 `voice_suggest_skill()` 을 거쳐 broad-hit 필터의 보호를 받았다.

## 옵션 D 선택 근거

조사 단계에서 네 가지 안을 실측 비교했다.

| 안 | 내용 | 결과 |
| --- | --- | --- |
| A | `/api/suggest-skill` 에서 `voice_suggest_skill()` 호출 | 오탐 8건이 `unknown` 이 될 뿐 **정답을 주지 못한다**. `ideal`/`multitask` 미해결. `voice_*` 함수를 Chat 이 호출하는 의미 왜곡 |
| B | `suggest_skill()` 에 broad-hit 정책 내장 | hermes 전용 특례를 범용 함수에 박는다. `voice_suggest_skill` 이 위에서 다시 필터 → 이중 적용. `ideal`/`multitask` 미해결 |
| C | 공통 helper | hermes 특례라는 본질은 그대로, 코드만 늘어남 |
| **D** | **매칭을 토큰 경계로** | **근본 원인 수정.** `report`/`approval` 이 **정답인 `tasks_reports` 로 간다**. 다른 skill 오탐도 함께 해결 |

D 를 택한 결정적 근거:

1. **코드베이스가 이미 같은 문제에 같은 해법을 쓰고 있었다.**
   `voice_has_context_term()` 의 docstring 이 문자 그대로
   *"Match short English routing terms as tokens to avoid preview/report
   overmatches."* 라고 적혀 있다. 토큰 경계 매칭을 context term 검사에만 쓰고
   1차 keyword 매칭에는 적용하지 않은 것이 누락이었다.
2. **A/B/C 는 오답을 `unknown` 으로 바꿀 뿐이고 D 만 정답을 준다.**
3. 시뮬레이션에서 **기존 routing assert 19건이 A/B/D 어느 쪽에서도 0건 깨지지 않았다.**
   D 를 택하는 데 추가 위험이 없었다.
4. 문제는 "broad-hit 정책을 어느 레이어에 둘까" 가 아니라
   **"매칭 규칙 자체가 틀렸다"** 였다.

## 구현

```python
def route_keyword_matches(normalized_message: str, keyword: str) -> bool:
    if keyword.isascii():
        pattern = rf"(?<![0-9a-z]){re.escape(keyword)}(?![0-9a-z])"
        return re.search(pattern, normalized_message) is not None
    return keyword in normalized_message
```

`suggest_skill()` 의 hits 계산이 이 helper 를 쓴다.
한글은 단어 경계 개념이 없으므로 **non-ASCII keyword 는 기존 부분문자열 매칭을
그대로 유지**했고, 한국어 routing 사례는 전부 보존됐다.

`voice_has_context_term()` 은 **손대지 않았다.** 같은 패턴을 재사용했을 뿐,
범위 밖 리팩터링을 하지 않기 위해 위임 구조로 바꾸지 않았다.

## 결과 — 목표 18/18 일치

| 입력 | 전 | 후 |
| --- | --- | --- |
| `report` | hermes_manager | **tasks_reports** |
| `approval` | hermes_manager | **tasks_reports** |
| `preview` | hermes_manager | **unknown** |
| `prepare` / `process` / `progress` / `priority` / `print` | hermes_manager | **unknown** |
| `ideal` | research_council | **unknown** |
| `multitask` | tasks_reports | **unknown** |
| `reproduce` | hermes_manager | **unknown** |
| `git` / `pr` / `repo` / `review` / `리뷰` / `repository` | hermes_manager | **hermes_manager** (유지) |
| `gitignore` | hermes_manager | **unknown** |

`gitignore` 는 토큰 경계 규칙의 자연스러운 결과로 수용했다.
**Owner Decision 없이 `route_keywords` 데이터를 늘리지 않았다.**

### Voice broad-hit 방어 6/6 보존

| 입력 | `voice_suggest_skill()` |
| --- | --- |
| `review` | unknown |
| `리뷰` | unknown |
| `git` | hermes_manager |
| `pr` | hermes_manager |
| `repo` | hermes_manager |
| `Codex 커밋 리뷰` | hermes_manager |

## 회귀 테스트

기존 routing assert 블록 안에 assert 테이블을 추가했다.
**새 파일이나 새 테스트 프레임워크를 만들지 않았다.**

- `run_web_app.py` self-test — routing 17건 + voice 6건
- `run_smoke_tests.py` — 동일 23건

### mutation probe — 테스트가 실제로 버그를 잡는다

메모리상에서 `route_keyword_matches` 를 옛 부분문자열 규칙으로 되돌린 뒤
self-test 를 실행했다. 파일은 건드리지 않았다.

```
[PASS] 옛 부분문자열 규칙 -> self-test 실패 (run_web_app.py:3808)
       assert suggest_skill(routing_message)["recommended_skill"] == expected_skill
[PASS] 복원 후 self-test 통과
       파일 byte-identical: True
```

**부분문자열 규칙이 되돌아오면 테스트가 반드시 깨진다.**

## 전체 테스트

`8bbd019` 작업 당시 **순차 실행**한 결과다. fixture 경합을 피하려고
병렬 실행하지 않았다.

| 검증 | 결과 |
| --- | --- |
| Console self-test | PASS |
| Console smoke + browser shell | PASS |
| KEEP route probe | 13/13 |
| canonical 전수 | 80/80 PASS |
| SOP | status=PASS |
| bot self-check | 92/92 PASS |
| discord-intake | 103/103 PASS |
| audit-chain | 7 passed, 0 failed |
| buzz-bridge | total 37, failed 0 |
| discord-nl-intent | total 35, failed 0 |
| hermes-manager-pilot | PASS (단독) |
| research-council | PASS (단독) |
| check_no_secrets --self-test | PASS |
| node --check app.js | OK |
| git diff --check | clean |

line ending 유지 — `run_web_app.py` CRLF, `run_smoke_tests.py` LF.

## 금지 항목 무변경 (실측)

| 항목 | 변경 |
| --- | --- |
| `skills.json` 의 `route_keywords` | **0** |
| `ROUTING_PRIORITY` | **0** |
| `VOICE_HERMES_BROAD_HITS` | **0** |
| `voice_suggest_skill()` 본문 | **0** |
| `voice_has_context_term()` | **0** |
| `/api/suggest-skill` 핸들러 | **0** — `voice_suggest_skill()` 로 우회시키지 않았다 |
| `suggest_skill()` signature | **0** |
| API response schema | **0** |
| `web/` | **0** |
| `contracts/` | **0** |
| `docs/` | **0** |
| `jarvis.bat` | 접근·수정·staging **없음** |

`suggest_skill()` 에 새로운 broad-hit 정책을 넣지 않았다.

## Commit / push

| 항목 | 값 |
| --- | --- |
| 구현 커밋 | **`8bbd019`** (부모 `4871243`) |
| 변경 파일 | `run_web_app.py`, `run_smoke_tests.py` **2개뿐** |
| push | `4871243..8bbd019  main -> main` |
| push 후 HEAD | `8bbd0191c936d7543887e46d23de74952f493ece` = `origin/main` |
| working tree | tracked 변경 0 |
| `jarvis.bat` | `??` untracked 유지 |

amend 나 rebase 는 하지 않았다.
이 기록은 **별도 커밋**으로 남기며 구현 코드를 다시 수정하지 않았다.

## Out of scope

- `gitignore` 를 `route_keywords` 에 추가하는 것 — 별도 Owner Decision
- `ROUTING_PRIORITY` 동점 처리 정책 자체의 재설계
- 한글 keyword 에 대한 토큰 경계 도입 — 단어 경계 개념이 없어 별도 설계 필요
- `voice_has_context_term()` 을 공통 helper 로 위임시키는 리팩터링
