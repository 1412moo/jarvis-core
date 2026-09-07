# task-0074-skills-json-memory-skills-ghost-removal

- id: `task-0074-skills-json-memory-skills-ghost-removal`
- title: `skills.json 에서 memory_skills 유령 항목 제거 (D6-d)`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-07 07:44 UTC`
- updated_at: `2026-09-07 07:44 UTC`
- summary: `task-0071 이 기능을 지운 뒤에도 skill registry 에 21필드짜리 memory_skills 항목이 남아 존재하지 않는 기능으로 라우팅될 수 있었다. 서식을 보존하려고 JSON 재직렬화 대신 중괄호 깊이로 객체 59줄만 잘라냈다. 라우팅이 데이터 기반이라 결과가 바뀌므로 실제 반환값을 측정해 단언 9개를 맞췄다. 기준선 대조 테스트는 약화시키지 않고 기준선에서도 같은 객체를 제거해 가드 강도를 유지했다. 작업 중 git checkout 이 만든 CRLF 오염도 되돌렸다.`
- source_command: `D6-d Owner 결정 — skills.json 유령 항목 정정`

## 기준선

HEAD `5094b95` = `origin/main`. Console 3파일.

## 무엇이 유령이었나

task-0071 이 `memory_skills` 기능군을 제거했지만 skill registry 에는 항목이 남아 있었다.
`status: planned`, `route_keywords` 12개, `docs`/`tests` 경로까지 갖춘 21필드 객체가
**존재하지 않는 기능**을 가리키고 있었다. `suggest_skill()` 이 이 항목의 키워드로
라우팅했으므로 사용자에게 없는 기능을 추천할 수 있었다.

## 제거한 것

`skills.json` 의 `memory_skills` 객체 **59줄**(264~322행). skill 6 -> **5**.

서식을 보존하려고 **JSON 재직렬화를 쓰지 않았다.** 첫 시도에서 `json.dumps(indent=2)` 로
다시 쓰자 무관한 배열 서식까지 바뀌어 +38/-97 diff 가 나왔다. 되돌리고 **중괄호 깊이로
객체 범위만 잘라내** +0/-59 로 만들었다.

## 갱신한 단언 9개

라우팅은 레지스트리 데이터를 순회하므로(`suggest_skill` 이 `registry_skills()` 를 돈다)
항목이 사라지면 결과가 바뀐다. 실제 반환값을 측정해 기대값을 맞췄다.

| 입력 | 전 | 후 | 근거 |
| --- | --- | --- | --- |
| `remember this repeated workflow as a skill` | `memory_skills` | `unknown` | 매칭되는 키워드가 없다 |
| 반복 작업 skill로 기억 (2곳) | `memory_skills` | `tasks_reports` | 일반 키워드 "작업" 에 걸린다 |
| Voice Inbox 반복 작업 문장 (2곳) | `memory_skills` | `tasks_reports` | 동일 |
| skill 개수 (4곳) | `6` | `5` | |

> 한국어 두 건이 `tasks_reports` 로 가는 것은 **의도된 라우팅이 아니라 부수 효과**다.
> 원래 의도("반복 작업 문장은 memory_skills 로")는 기능과 함께 사라졌고, 지금 이 단언들은
> 부수적 라우팅을 기록할 뿐이다. 주변 단언(`needs_confirmation`, `saved` 부재)은 기능과
> 무관하게 유효해 그대로 뒀다. **이 두 건을 삭제할지는 별도 판단 사안이다.**

## 🔴 registry copy-drift 테스트 — 약화시키지 않고 살렸다

`_test_tasks_reports_registry_copy`(200줄)는 기준 커밋의 `skills.json` 과 현재 파일을
**위치 경로 단위 문자열 전수 비교 + 바이트 단위 복원 비교**로 대조한다. 항목 하나를 지우면
이후 모든 인덱스가 밀려 전면 실패한다.

세 갈래 중 **가장 강한 것을 골랐다.**

| 안 | 평가 |
| --- | --- |
| 인덱스에 `-1` 보정 | 불투명하고 바이트 비교는 여전히 깨진다 |
| 바이트 비교 단언 삭제 | **가드 약화** |
| **기준선에서도 같은 객체를 제거** | 남은 skill 에 대해 가드가 **원래 강도 그대로** 유지된다 |

`baseline_raw` 에서 같은 중괄호 깊이 방식으로 객체를 잘라내고, 파싱된
`baseline_registry["skills"]` 에서도 걸러냈다. 인덱스 단언은 손대지 않아도 저절로 맞았다.

## 작업 중 잡은 것 — CRLF 오염

중간에 `git checkout --` 로 되돌렸더니 autocrlf 때문에 working copy 가 **LF -> CRLF** 로
바뀌었고, 커밋된 blob(LF)과 바이트 비교하는 테스트가 전면 실패했다. 원인을 오해하고
테스트를 고칠 뻔했으나 실제 바이트를 세어 확인한 뒤 파일을 LF 로 되돌려 해결했다.
**테스트가 아니라 내 작업이 만든 오염이었다.**

## 남긴 것과 근거

| 잔여 | 근거 |
| --- | --- |
| `run_web_app.py:518` `ROUTING_PRIORITY["memory_skills"]: 3` | Owner 가 registry 로직을 범위 밖으로 지정했다. `.get(..., 99)` 조회라 **동작에 영향 없음**(항목이 없으니 매칭 자체가 안 된다). 정리하려면 별도 승인 |
| `ALLOWED_CATEGORIES` 의 `"memory"` | 검증 allowlist 축소는 로직 변경이다 |
| `docs/memory-skills-v0.1-design.md` | 제거된 기능의 설계 문서 — **역사 기록** |
| `docs/jarvis-console-v0.1-checkpoint.md` 라우팅 표 2줄 | 당시 체크포인트 기록 |
| `run_smoke_tests.py` 의 이름 언급 4곳 | 기준선 필터가 이름으로 대상을 지목해야 한다 |

## 검증

| 검증 | 결과 |
| --- | --- |
| `jarvis-console` 스모크 + browser shell self-test | **PASS** |
| registry copy-drift 테스트 | **PASS** (가드 강도 유지) |
| canonical 전수 | **66/66 PASS** |
| `validate_multi_agent_sop` | `status=PASS` |
| `bot_minimal` self-check | **92/92 PASS** |
| `discord-intake` | **89/89 PASS** |
| `audit-chain` | PASS |
| `buzz-bridge` | failed 0 |
| `discord-nl-intent` | 35/35 PASS |
| `check_no_secrets --self-test` | `status=PASS` |
| `git diff --check` | clean |

## diff

```
apps/jarvis-console/skills.json        59 ----------  (+0 / -59, 서식 보존)
apps/jarvis-console/run_web_app.py     12 +++---      (단언 6곳)
apps/jarvis-console/run_smoke_tests.py 32 ++++++--    (단언 3곳 + 기준선 필터)
3 files changed, 35 insertions(+), 68 deletions(-)
```

## 이번 단계 비범위

- skill_registry 구조·`run_web_app.py` registry 로직 — 무변경
- evaluate_idea / suggestedActionPanel / task_lifecycle / overview_status / UI 구조 — 무변경
- hermes-manager-pilot — 무변경
- D6-b·D6-c — 미결 유지
- `jarvis.bat` — 건드리지 않았다
