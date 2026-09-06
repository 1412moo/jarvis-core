# task-0064-audit-scope-console-transition-note

- id: `task-0064-audit-scope-console-transition-note`
- title: `콘솔 상태 전이가 감사 범위 밖인 이유를 task-0044 설계에 명시`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-06 17:37 UTC`
- updated_at: `2026-09-06 17:37 UTC`
- summary: `task-0062에서 내가 콘솔 전이를 감사 범위 공백으로 오독했고, task-0063에서 그것이 공백이 아니라 분류임을 확인했다. 판단 근거가 네 문서에 흩어져 있어 다음 사람도 같은 오독을 하게 되므로, 분류 규칙이 사는 task-0044 설계 3.3절에 연결을 한곳으로 모았다. 콘솔은 NEEDS_APPROVAL을 출발로도 도착으로도 갖지 않아 승인성 전이가 발생할 수 없고, 일반 전이는 보류 중인 task-0041 소관이라 제외가 의도된 범위라는 사실만 적었다. 새 결정은 없다.`
- source_command: `task-0062/0063 후속 문서 정합성 작업 승인 (Owner)`

## 기준선

HEAD `05d3a57` = `origin/main`. 변경은 `docs/task-0044-audit-hash-chain-design.md`에
**절 하나 추가**와 이 기록뿐이다. 삭제 0줄, 코드 0줄.

## 왜 이 작업이 필요했나 — 내가 직접 오독했다

task-0062에서 나는 콘솔 전이 경로를 발견하고 **"감사 범위 공백"**으로 보고했다.
task-0063에서 근거를 추적한 결과 그것은 공백이 아니라 **분류**였다. 판단을 뒤집은 근거가
네 문서에 흩어져 있었다.

| 조각 | 위치 |
| --- | --- |
| A는 `/approve`로 인한 전이로 한정된다 | task-0044 §3.1 |
| 일반 상태 전이는 G이고 task-0041 소관이다 | task-0044 §3.1, §7.1 |
| 결정 2가 범위를 A+B로 확정했다 | task-0044 §10 |
| task-0041 구현은 Owner 결정 ③으로 보류됐다 | task-0041 기록 |

네 조각을 모으기 전에는 "콘솔이 task 상태를 바꾸는데 감사 기록이 없다"가 결함으로 읽힌다.
**한 번 오독한 것은 다음 사람도 오독한다.** 그래서 결론이 아니라 결론에 이르는 연결을
한곳에 적었다.

## 어디에 적었는가

`docs/task-0044-audit-hash-chain-design.md` **§3.3**, `### 3.2` 바로 뒤.

이 문서를 고른 이유는 세 가지다.

1. **분류 규칙 자체가 여기 산다.** §3.1의 A~G 표와 "G는 task-0041 소관"이라는 문장이
   §3.2 끝에 이미 있다. 새 절은 그 문장을 콘솔에 적용한 것에 지나지 않는다.
2. **오독이 일어나는 지점이다.** "감사 범위가 무엇인가"를 묻는 사람이 도달하는 절이다.
3. **사후 주석 선례가 이 문서 안에 있다.** §9가 `> 이 절은 설계 단계 기준으로 작성됐다`
   블록인용으로 시작한다. 같은 형식을 따랐다.

대안으로 검토하고 버린 곳:

| 후보 | 버린 이유 |
| --- | --- |
| task-0052 §8 비범위 | 그 절은 task-0052 단계의 비범위다. C~F 줄이 이미 task-0044 결정 2를 가리키므로 여기 적으면 **약한 사본**이 하나 더 생긴다 |
| `docs/execution-status-transition-policy.md` | 실행 결과 → 상태 전이 정책이라 주제가 다르다 |
| `docs/jarvis-console.md` | 전이 기능이 생기기 전의 v0.1 설계 문서다. transition 언급이 0회 |
| `docs/master-plan.md` | Owner 지시가 범위 확장을 금지했다 |
| `docs/task-model.md` | 파일 형식 계약이지 감사 범위 문서가 아니다 |

## 적은 내용

- 봇 `/approve`는 `NEEDS_APPROVAL → DOING`/`→ FAILED`, 콘솔은 `TODO → DOING`/
  `DOING → DONE` — **전이 교집합이 없다**
- A의 정의가 `/approve`로 한정돼 있고 콘솔은 `TASK_TRANSITION_ACTIONS`가 `start`와
  `complete` 둘뿐이라 `NEEDS_APPROVAL`을 출발로도 도착으로도 갖지 않는다. **콘솔에서는
  승인성 전이가 발생할 수 없다**
- 따라서 콘솔 전이는 G이고, G는 task-0041 소관이며, task-0041은 Owner 결정 ③으로 구현
  보류 중이다 — **누락이 아니라 의도된 범위다**
- `Record Completion Evidence`는 `status`를 바꾸지 않으므로 상태 전이가 아니고 감사 범위
  논의 대상도 아니다
- **결정 2(A+B 한정)를 재개방하지 않는다.** 확장하려면 결정 2와 `ALLOWED_KINDS`를 함께
  여는 별도 Owner 설계 결정이 필요하고 그 판단은 이 문서 범위 밖이다

**새 결정을 만들지 않았다.** 절 첫머리 블록인용에 그 사실을 명시했다.

## 검증

| 검증 | 결과 |
| --- | --- |
| 헤딩 구조 | `### 3.3`이 `## 3` 아래, `3.1`/`3.2` 다음. **중복 절 번호 0** |
| 내부 참조 | 새로 쓴 `§3.1`·`§2.2`·`§7.1`·`§10` 전부 이 문서에 존재 |
| 외부 참조 | `docs/task-model.md` §11 실재 확인. 기존 `task-0042 §5.4`와 같은 표기 규약 |
| 줄 너비 | 새 절 최대 83자 (문서 나머지 최대 171자) |
| 이 문서를 파싱하는 코드 | **없음** — SOP validator 대상은 `AGENTS.md`/SOP/`master-plan.md` 3개뿐 |
| diff | 30줄 추가, **삭제 0** |
| `git diff --check` | clean |
| `validate_multi_agent_sop` | `status=PASS` |
| canonical 전수 | **62/62 PASS** |
| `discord-intake` 스모크 | **85/85 PASS** |
| `audit-chain` 스모크 | **7/7 PASS** |

## 이번 단계 비범위

- 코드·audit schema·`ALLOWED_KINDS`·`ALLOWED_ACTORS`·콘솔 동작 — 전부 무변경
- cross-check / list-entries 도구 — 만들지 않았다(task-0062 결론 유지)
- 과거 audit 기록 생성 — 하지 않았다. 실제 체인은 여전히 비어 있다
- `master-plan.md` — 건드리지 않았다
- `jarvis.bat` — 건드리지 않았다
