# task-0051-master-plan-structured-field-drift

- id: `task-0051-master-plan-structured-field-drift`
- title: `master-plan 구조화 필드에 산문이 섞여 jarvis-console 스모크가 6일간 실패하던 문제 수정`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-03 06:20 UTC`
- updated_at: `2026-09-03 09:38 UTC`
- summary: `docs/master-plan.md의 '## 2. 현재 기준점' 섹션에서 구조화 필드(enum / 정규화 ID) 두 개에 설명 산문이 덧붙어 apps/jarvis-console 스모크 테스트가 RegistryError로 실패하고 있었다. 2026-08-28 commit 8843488부터 6일간 깨진 상태였다. 필드 값을 파서 계약에 맞게 되돌리고 산문은 자유 텍스트 필드로 옮겨 해결했다. 전체 스모크 10종이 처음으로 전건 PASS.`
- source_command: `task-0042 회귀 테스트 중 발견 → Owner가 우선 수정 지시`

## 발견 경위

task-0042(역할별 서명키) 작업의 기존 회귀 테스트 단계에서 `apps/jarvis-console`만 실패했다.
task-0042의 변경이 원인인지 확인하기 위해 추적한 결과 **무관한 기존 결함**으로 판명됐다.

- 내 편집을 전부 되돌린 HEAD 상태에서도 동일하게 실패
- `git show 22b7398:docs/master-plan.md`로 바꿔 실행하면 통과(exit 0)
- 도입 커밋 `8843488` (2026-08-28, "record Phase 1 decisions and ON_HOLD state")

## 근본 원인

`docs/master-plan.md`의 `## 2. 현재 기준점` 섹션은 사람이 읽는 문서인 **동시에**
`apps/jarvis-console/run_web_app.py:read_master_plan_snapshot()`이 파싱하는 **구조화된
데이터 원천**이다. 파서는 `- <label>: <value>` 줄을 첫 콜론에서 쪼개 `MASTER_PLAN_FIELDS`로
매핑한 뒤, 일부 필드에 형식 제약을 강제한다.

| 필드 | 제약 | 위반 내용 |
| --- | --- | --- |
| `Approval state` | `{none, required, blocked}` enum | 407자 산문이 들어 있었음 |
| `Manager reporting next package ID` | `^[a-z0-9][a-z0-9._-]{0,127}$` | 유효 ID 뒤에 괄호 설명이 붙어 있었음 |

두 필드 모두 **자유 텍스트 짝(`Approval note`)이 이미 존재**하거나 설명이 들어갈 자리가
따로 있었는데, 산문이 구조화 필드 쪽에 들어갔다. 파서는 fail-closed라 한 필드만 어긋나도
Project Control 카드 전체가 `RegistryError`로 막힌다.

이 필드들이 UI에서 어떻게 쓰이는지가 의도를 확정해 준다 —
`apps/jarvis-console/web/app.js:3131`은 `approval_state`를 배지 라벨
(`No approval needed` / `Approval required` / `Blocked`)로만 쓰고, 산문은 바로 아래
`승인 필요 여부: <approval_note>`로 따로 렌더링한다.

## 수정 내용

`docs/master-plan.md` 3줄 변경. 코드는 건드리지 않았다.

1. `Approval state` → `required`로 환원.
2. 그 산문 중 **승인 관련 부분**을 `Approval note`로 이관(기존 note 내용 유지하며 병합,
   234/500자). 나머지(완료 이력)는 `Recent completed`와 §"현재 위치와 다음 체감 목표"에
   이미 동일 내용이 있어 중복이므로 이관하지 않았다.
3. `Manager reporting next package ID`의 괄호 설명 제거 → `buzz-bridge-phase2-slice1-increment-v0.1`.
   제거한 참조(task-0047/0048/0049/0050, P2-2~P2-6, director-dashboard-v0.1b, task-0038)가
   모두 문서 내 다른 곳에 남아 있음을 확인한 뒤 제거했다.

### `required`를 고른 근거 (Owner 확인 요망)

원래 산문이 "Phase 2 전체 통합 확대(task-0038 §6 남은 단계 ②/④/⑤)는 여전히 미승인 —
**착수 전 별도 승인 필요**"라고 명시하고 있었고, 이는 배지 라벨 `Approval required`와
1:1로 대응한다. 즉 새로운 거버넌스 판단을 만든 것이 아니라 **문서가 이미 하고 있던 진술을
필드 형식에 맞게 옮겨 적은 것**이다.

`blocked`을 쓰지 않은 이유는 배지가 "Blocked"로 표시되어 실제 상태를 과장하기 때문이다 —
작업이 막힌 것이 아니라 scope 확대에 승인이 필요한 상태다.

**이 한 단어는 Owner의 승인 상태 진술이므로, 다르게 보시면 값만 바꾸면 된다.**

## 검증

- `apps/jarvis-console` 스모크 **PASS** (이전: `RegistryError`)
- 전체 스모크 10종 **전건 PASS** — team-manager-bot, daily-ai-radar, hermes-manager-pilot,
  jarvis-console, research-council, discord-intake, discord-nl-intent, buzz-bridge,
  role-signing, validate_multi_agent_sop
- 섹션 내 19개 필드 전수 제약 검사: 위반 0건, 누락 0건
- task-0042 실제 서명키 무영향 (`verify-keys ok: true`)

## 남은 것

커밋만 남았다. Owner가 "커밋하지 말고 대기"를 지시해 working tree에만 반영되어 있다.

## 재발 방지 제안 (미구현, 별도 결정 필요)

`## 2. 현재 기준점`은 문서이면서 파서 계약이라 산문이 섞이기 쉽다. 실제로 그렇게 6일간
깨져 있었고, 그동안 아무도 알아채지 못했다. 다음 중 하나를 권한다.

1. `scripts/validate_multi_agent_sop.py`처럼 master-plan 필드 제약만 검사하는 가벼운
   검증 스크립트를 두고 문서 갱신 시 함께 돌린다.
2. `## 2. 현재 기준점` 안에 "이 섹션의 값은 파서 계약이며 설명은 `*note` 필드에 쓴다"는
   주석을 남긴다.

두 방법 모두 이번 수정 범위 밖이라 하지 않았다.
