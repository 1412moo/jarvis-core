# task-0123-readme-scope-consistency-repair

- id: `task-0123-readme-scope-consistency-repair`
- title: `루트 README 의 bootstrap 시절 범위 서술을 현재 구현에 맞게 정정`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-11 02:20 UTC`
- updated_at: `2026-09-11 02:20 UTC`
- summary: `루트 README 는 master-plan 포인터 한 줄을 빼면 저장소 최초 커밋 원문 그대로였고 5 개월 넘게 갱신되지 않았다. Discord 봇과 웹 UI 를 비범위로 적고 디렉터리 여섯 개를 초기 빈 구조라고 기술하며 apps 를 아예 빠뜨리고 있었다. audit 이 승인한 C1 부터 C5 까지만 고쳤다. 여러 저장소 서술과 멀티 에이전트 비범위 문장은 Owner 판단 대기라 손대지 않았고 GitHub 자동화 등 아직 유효한 잠금 세 건도 그대로 뒀다. README 를 읽는 코드는 0 건이며 production 변경 0.`
- source_command: `README 정합성 audit 후 Owner 가 승인한 C1~C5 수정 지시`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | **`f20a9b7`** = `origin/main` |
| 직전 작업 | task-0122 (T2 — master-plan drift 정리) |
| 변경 파일 | `README.md` + 이 기록 |
| production · test · schema | **무변경** |

## 왜 필요했나

audit 이 확인한 사실이다. 루트 `README.md` 는 **커밋이 세 개뿐**이다.

| 커밋 | 날짜 | 변경 |
| --- | --- | --- |
| `81359b1` | 2026-04-03 | 저장소 최초 커밋 — 본문 전체 |
| `a8de65e` | 2026-04-04 | 개발 루프 절 추가 |
| `fb95bf4` | 2026-07-22 | **master-plan 포인터 한 줄만** 추가 |

즉 본문은 bootstrap 당일 원문 그대로이며 그 뒤 120 개가 넘는 커밋 동안 한 번도
갱신되지 않았다. task-0090 이 고친 README 는 `apps/jarvis-console/README.md`
였고 루트 README 가 아니다.

## 무엇을 고쳤나

| 항목 | 문제 | 근거 | 수정 |
| --- | --- | --- | --- |
| **C1** | 비범위에 `Discord 봇 구현` | `adapters/discord/bot_minimal.py` **3,476 줄**, `adapters/team-manager-bot/` 6 파일 | 비범위 목록에서 제거 |
| **C2** | 비범위에 `웹 UI 구현` | `apps/jarvis-console/run_web_app.py` **4,716 줄** + `web/{app.js,index.html,styles.css}` | 비범위 목록에서 제거 |
| **C3** | 디렉터리 여섯 개가 `(초기 빈 구조)` | tracked 파일 `prompts` 10 · `orchestrator` 49 · `adapters` 14 · `configs` 3 · `memory` 77 · `scripts` 5 | 각각 실제 역할로 교체 |
| **C4** | 디렉터리 개요에 `apps/` 누락 | 앱 4 개 존재 | `apps/` 한 줄 추가 |
| **C5** | "기능 구현보다 문서를 우선" · "현재 범위 (Bootstrap 단계)" | master-plan §3 이 0·1·2·4 단계를 **사용자 기능**으로 기록 | 각각 현재와 모순 없는 표현으로 교체 |

C3 은 "구현됨" 같은 모호한 말로 바꾸지 않고 실제 하위 모듈 이름을 적었다.
C4 의 앱 목록도 실재하는 네 개만 적었다.

### 부수 수정 1 건 — 보고

`## 비범위 (이번 단계에서 제외)` 의 제목을 `## 비범위 (현재 범위 밖)` 으로
바꿨다. C5 가 "Bootstrap 단계" 라는 이름을 완료 범위로 옮겼기 때문에, 그 제목이
가리키던 "이번 단계" 가 문서 안에 더는 존재하지 않게 됐다. C1·C2·C5 의 직접
귀결이며 목록 내용은 건드리지 않았다.

## 손대지 않은 것

| 대상 | 이유 |
| --- | --- |
| **C6** — "여러 프로젝트/서브 저장소를 운영하기 위한 메인 지휘 저장소" | `AGENTS.md` 의 "Jarvis-Core 단일 저장소" 와 충돌하지만 어느 쪽이 현재 방침인지 **Owner 확인 대기** |
| **C7** — 비범위 `멀티 에이전트 실구현` | Phase 2 통합이 여전히 미승인이라 혼동 위험. 기존 문장 유지 |
| 비범위 `GitHub 자동화 구현` · `배포 및 인프라 자동화` · `Docker/DB 확장 설계` | **아직 유효한 잠금.** master-plan §6·§7 이 push/PR 자동화를 명시적으로 잠근다 |
| master-plan 포인터 한 줄 | canonical 지목, 유지 |
| 운영 원칙 요약 · 개발 루프 | 정확함 |
| `docs/master-plan.md` · production · 테스트 · `jarvis.bat` | 이번 범위 밖 |

README 전체 재작성은 하지 않았다. 문장 교체만 했고 절 구성과 목적은 그대로다.

## 검증

| 항목 | 결과 |
| --- | --- |
| 루트 README 를 읽는 코드 | **0 건** — `apps/*/README.md` 참조와 NL 라우팅 픽스처 문자열뿐 |
| C6 · C7 · 잠금 3 건 · 포인터 · 운영 원칙 · 개발 루프 | 수정 스크립트가 **전후로 존재를 단언**해 무변경 확인 |
| `(초기 빈 구조)` 잔존 | **0 건** |
| diff | `README.md` 1 파일, **+13 / −14** |
| `git diff --check` | clean |
| Console self-test · smoke | **PASS** (exit=0) |
| task record canonical | 전수 PASS |

## 남은 것

| 항목 | 상태 |
| --- | --- |
| C6 저장소 성격 서술 | **Owner 확인 대기** — README 와 `AGENTS.md` 중 어느 쪽이 현재 방침인가 |
| C7 멀티 에이전트 비범위 | Phase 2 통합 승인 여부에 종속 |
| T3 selected-state production 구현 | **별도 Owner 승인 필요** |
| §4 rolling window audit | read-only 후보 |
