# task-0175-team-manager-holds-to-on-hold

- id: `task-0175-team-manager-holds-to-on-hold`
- title: `보류 중인 Team Manager task 5건의 ON_HOLD 전환 (패키지 B)`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-20 15:05 UTC`
- updated_at: `2026-10-20 16:07 UTC`
- summary: `task-0156에서 Owner가 보류한 Team Manager task 중 NEEDS_APPROVAL 5건(0030, 0032, 0033, 0034, 0036)의 summary에 보류 주체·근거·사유·재개 조건을 승인된 문구로 기록했고(task-model §9, 0033·0036은 축약하고 원문을 본문에 보존), Reviewer·QA 뒤 공식 Console Hold로 ON_HOLD(hold_from NEEDS_APPROVAL)로 옮긴다. DOING인 task-0031은 그대로 둔다. Reviewer 1 지적(T8 인용 불일치)을 repair 1로 고쳤고 검토·Hold 결과는 본문에 기록한다.`
- source_command: `Owner 결정: 패키지 B A안, task-0175 등록과 계획 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `7cf5c850256c63945026f8d086fc9cb88f5694f5` (등록 시점 main HEAD = origin/main, fetch 후 확인). Start 때 다시 확인한다 |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat` |
| 등록 방식 | 이 기록을 `TODO`로 작업 트리에만 만들었다(커밋·stage 없음). task-0173·0174와 같이 Start 승인 뒤 candidate에 포함한다 |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=1` (기본값. repair 1 사용, 아래 "Repair 1") |

## Owner 결정 (원문)

```text
패키지 B의 다음 단계로 A안을 승인합니다. 새 task-0175를 등록하되, 우선 등록과 계획 수립까지만 진행하고 실제 기존 task 기록 수정이나 Hold 전환은 별도 단계로 진행하세요.
목표: `task-0175 — 보류 중인 Team Manager task 5건의 ON_HOLD 전환`
1. task 등록

* 현재 SOP와 task 등록 절차를 확인하고 공식 경로로 task-0175를 등록해.
* 범위는 task-0030, 0032, 0033, 0034, 0036의 보류 사유·재개 조건 기록 및 공식 Hold 전환으로 한정해.
* task-0031은 DOING 상태로 유지하며 전환 대상에서 제외해.
* 기존 task-0156의 실제 기록을 읽어 보류 결정과 근거를 정확히 확인해. 근거를 추측하거나 새로 만들지 마.

2. 기록 문구 계획
각 대상 summary에 다음 정보를 명확하게 남기는 방안을 작성해.

* 결정 주체: Owner
* 보류 결정 근거: task-0156
* 보류 사유: 외부 API, credential, 비용 및 상시 실행 관련 작업을 별도 Owner 결정 전까지 진행하지 않음
* 재개 조건: 별도 Owner 결정

위 문구는 task-0156 원문과 대조한 뒤 확정해. 기존 summary의 의미 있는 내용을 삭제하거나 왜곡하지 마.
task-0033은 summary가 496/500자이므로 특별히 주의해. 500자 제한을 넘기지 않도록 기존 문구에서 중복·불필요한 표현을 최소한으로 줄이는 후보를 제시하고, 원래 의미가 보존되는지 설명해. 다른 네 건도 수정 전후 summary와 글자 수를 제시해.
3. 검토 및 실행 계획

* 기록 수정이 SOP §4에 따라 Reviewer와 QA를 거쳐야 하는지 확인하고, 필요한 검토 단계를 task 계획에 포함해.
* 기록 수정 검토가 완료되기 전에는 기존 task를 Hold하지 마.
* 기록 수정 후에는 각 task의 공식 Console Hold Preview를 열고, Owner·사유·재개 조건·`hold_from: NEEDS_APPROVAL`을 확인한 뒤에만 Confirm하도록 계획해.
* Hold 후 상태와 `hold_from`, `/report` 집계, smoke test를 검증하고 checkpoint를 남기는 절차를 포함해.

4. 이번 단계의 제한

* 지금은 task-0175 등록과 계획까지만 진행해.
* 기존 5건의 summary나 상태를 수정하지 마.
* task-0031, task-0035, `jarvis.bat`, 보존 worktree는 건드리지 마.
* Reviewer/QA 완료 전 Hold하지 마.
* 커밋과 push는 별도 승인 전까지 하지 마.

등록 결과, task ID, 제안된 summary 문구와 글자 수, 검토·전환 계획을 보고하고 멈춰.
```

등록 전 확인: fetch 뒤 `main` = `origin/main` = `7cf5c85`. `memory/tasks`에 task-0175 파일 없음, `0175` branch 없음.

## 근거 (read-only)

### task-0156의 결정 (기록 그대로)

`memory/tasks/task-0156-team-manager-direction-hold-decision.md`의 "결정" 절:

> task-0030, task-0031, task-0032, task-0033, task-0034, task-0036의 Team Manager 방향은 **보류**한다.
> - 외부 API, credential, 비용, 상시 실행 관련 작업은 재개하지 않는다.
> - 재개하려면 별도 Owner 결정이 필요하다.
> - task-0035는 이 결정의 대상이 아니다.

결정 주체는 Owner(같은 기록의 "Owner 결정 (원문)" 절, 2026-10-14)다. Owner 지시의 보류 사유 표현("별도 Owner 결정 전까지 진행하지 않음")과 task-0156 원문("재개하지 않는다", "재개하려면 별도 Owner 결정이 필요하다")은 같은 뜻이며, 제안 문구는 task-0156 원문 쪽 표현을 쓴다.

### 대상 상태 (baseline `7cf5c85`)

| task | status | updated_at | blob | Console Task View | writer 검증 | 판정 |
| --- | --- | --- | --- | --- | --- | --- |
| 0030 | NEEDS_APPROVAL | 2026-08-26 11:08 UTC | `5bae2580d369` | 표시 | 통과 | 대상 |
| 0031 | DOING | 2026-08-26 11:29 UTC | `5d7dbb80335c` | 표시 | 통과 | **제외**(DOING은 Hold 불가, task-0173 E2) |
| 0032 | NEEDS_APPROVAL | 2026-08-26 11:32 UTC | `ede13b3278fe` | 표시 | 통과 | 대상 |
| 0033 | NEEDS_APPROVAL | 2026-08-26 11:42 UTC | `999c8e29a6b3` | 표시 | 통과 | 대상 |
| 0034 | NEEDS_APPROVAL | 2026-08-26 11:46 UTC | `d22b5656479e` | 표시 | 통과 | 대상 |
| 0036 | NEEDS_APPROVAL | 2026-08-26 12:26 UTC | `d11c6ce0bd55` | 표시 | 통과 | 대상 |
| 0035 | DONE | 2026-08-26 12:23 UTC | `d494ed175848` | 표시 안 됨 | 통과 | 보호(변경 없음) |

다섯 대상 모두 summary에 보류 주체·근거·사유·재개 조건이 없어 task-model §9의 Hold 전 조건을 채우지 못한다.

## 제안 summary (D1·D2로 확정)

공통 추가 문장(87자, task-0156 결정을 압축): "보류: Owner 결정(task-0156). 외부 API·credential·비용·상시 실행 작업은 재개하지 않고, 재개는 별도 Owner 결정이 필요하다." 결정 주체(Owner), 근거(task-0156), 사유(외부 API·credential·비용·상시 실행 작업 재개 안 함), 재개 조건(별도 Owner 결정)을 모두 담는다. 기존 summary 뒤에 붙이고, NEEDS_APPROVAL 사유 문장은 그대로 둔다(Resume하면 NEEDS_APPROVAL로 돌아가므로 여전히 필요하다).

### task-0030 (`task-0030-codex-chatgpt-team-manager-discord.md`)

- 현재(404자): ChatGPT/Codex를 Discord에 연결된 팀장 에이전트로 만드는 방안을 조사·설계했다(구현 없음). work-order: prompts/task-0030-codex-chatgpt-team-manager-discord-work-order.md. 결론: 실질 구현은 신규 OpenAI API credential, 비용, (상시 구동 시) 배포가 필요하며 docs/master-plan.md §6의 "Hermes의 자동 Codex/ChatGPT 호출" 잠긴 기능 재오픈 대상이다. NEEDS_APPROVAL 사유: 어느 대안으로 진행할지, credential/비용/배포를 승인할지, 잠긴 기능 재오픈 여부를 Owner가 결정해야 한다. 승인되면 바로 할 다음 작업은 선택된 대안의 최소 스캐폴딩(토큰/배포 제외) 설계.
- 제안(492자): ChatGPT/Codex를 Discord에 연결된 팀장 에이전트로 만드는 방안을 조사·설계했다(구현 없음). work-order: prompts/task-0030-codex-chatgpt-team-manager-discord-work-order.md. 결론: 실질 구현은 신규 OpenAI API credential, 비용, (상시 구동 시) 배포가 필요하며 docs/master-plan.md §6의 "Hermes의 자동 Codex/ChatGPT 호출" 잠긴 기능 재오픈 대상이다. NEEDS_APPROVAL 사유: 어느 대안으로 진행할지, credential/비용/배포를 승인할지, 잠긴 기능 재오픈 여부를 Owner가 결정해야 한다. 승인되면 바로 할 다음 작업은 선택된 대안의 최소 스캐폴딩(토큰/배포 제외) 설계. 보류: Owner 결정(task-0156). 외부 API·credential·비용·상시 실행 작업은 재개하지 않고, 재개는 별도 Owner 결정이 필요하다.

### task-0032 (`task-0032-chatgpt-team-manager-integration-research.md`)

- 현재(326자): OpenAI API로 무엇이 가능한지, ChatGPT 웹 세션과 OpenAI API의 차이, Discord->Team Manager->Claude Code->Discord 메시지 흐름, Phase B 발급 항목·비용 범위를 조사·설계했다(구현/발급/호출 없음). work-order: prompts/task-0032-chatgpt-team-manager-integration-research-work-order.md. NEEDS_APPROVAL 사유: Phase B에서 실제로 무엇을 발급하고 얼마까지 비용을 승인할지는 Owner 결정 사항이며, 이 조사는 그 결정을 위한 입력이다.
- 제안(414자): OpenAI API로 무엇이 가능한지, ChatGPT 웹 세션과 OpenAI API의 차이, Discord->Team Manager->Claude Code->Discord 메시지 흐름, Phase B 발급 항목·비용 범위를 조사·설계했다(구현/발급/호출 없음). work-order: prompts/task-0032-chatgpt-team-manager-integration-research-work-order.md. NEEDS_APPROVAL 사유: Phase B에서 실제로 무엇을 발급하고 얼마까지 비용을 승인할지는 Owner 결정 사항이며, 이 조사는 그 결정을 위한 입력이다. 보류: Owner 결정(task-0156). 외부 API·credential·비용·상시 실행 작업은 재개하지 않고, 재개는 별도 Owner 결정이 필요하다.

### task-0033 (`task-0033-local-llm-team-manager.md`)

- 현재(496자): Owner PC 하드웨어(AMD Ryzen 5 7530U 6C/12T, RAM ~13.9GB, 통합 GPU만, 디스크 여유 351GB)를 확인하고, Ollama/llama.cpp/LM Studio/vLLM을 비교해 이 하드웨어에는 Ollama(llama.cpp 기반) + 7B급 4-bit 양자화 모델을 권고했다. 모델 다운로드/credential 발급/외부 연결/코드 구현 없음. work-order: prompts/task-0033-local-llm-team-manager-work-order.md. NEEDS_APPROVAL 사유: OpenAI API 경로(task-0032) 대비 로컬 경로를 택할지, 모델 후보 중 무엇을 쓸지, master-plan.md §6 잠긴 기능("자동 Codex/ChatGPT 호출", "background worker/unattended execution")이 로컬 모델 기반에도 그대로 적용되는지 해석이 필요해 Owner/ChatGPT 결정 대기.
- 제안(491자): Owner PC 하드웨어(Ryzen 5 7530U, RAM ~13.9GB, 통합 GPU만)를 확인하고, Ollama/llama.cpp/LM Studio/vLLM을 비교해 이 하드웨어에는 Ollama(llama.cpp 기반) + 7B급 4-bit 양자화 모델을 권고했다. 모델 다운로드/credential 발급/외부 연결/코드 구현 없음. NEEDS_APPROVAL 사유: OpenAI API 경로(task-0032) 대비 로컬 경로를 택할지, 모델 후보 중 무엇을 쓸지, master-plan.md §6 잠긴 기능("자동 Codex/ChatGPT 호출", "background worker/unattended execution")이 로컬 모델 기반에도 그대로 적용되는지 해석이 필요해 Owner/ChatGPT 결정 대기. 보류: Owner 결정(task-0156). 외부 API·credential·비용·상시 실행 작업은 재개하지 않고, 재개는 별도 Owner 결정이 필요하다.
- 줄인 부분:
  - "(AMD Ryzen 5 7530U 6C/12T, RAM ~13.9GB, 통합 GPU만, 디스크 여유 351GB)" → "(Ryzen 5 7530U, RAM ~13.9GB, 통합 GPU만)"
  - "work-order: prompts/task-0033-local-llm-team-manager-work-order.md." → 삭제

### task-0034 (`task-0034-local-team-manager-approval-boundary.md`)

- 현재(410자): master-plan.md §6의 잠긴 기능 중 background worker/unattended execution과 자동 prompt rendering·실행이 로컬 Team Manager에도 적용됨을 확인했다(외부 API/LLM/credential은 로컬 경로에 문자 그대로는 미적용). Owner 승인 식별은 기존 adapters/discord의 /approve 계약 재사용을 제안한다. 최소 Phase B로는 상시 봇 대신 Owner가 수동 호출하는 1회성 로컬 CLI 조언 도구를 제안했고 어떤 lock도 건드리지 않는다. 설치·다운로드·코드 구현 없음. NEEDS_APPROVAL 사유는 최소 Phase B 범위와 승인 식별 방식의 Owner 확정이 필요하기 때문이다. 전체 원문은 아래 요약(원문) 절에 그대로 보존했다.
- 제안(498자): master-plan.md §6의 잠긴 기능 중 background worker/unattended execution과 자동 prompt rendering·실행이 로컬 Team Manager에도 적용됨을 확인했다(외부 API/LLM/credential은 로컬 경로에 문자 그대로는 미적용). Owner 승인 식별은 기존 adapters/discord의 /approve 계약 재사용을 제안한다. 최소 Phase B로는 상시 봇 대신 Owner가 수동 호출하는 1회성 로컬 CLI 조언 도구를 제안했고 어떤 lock도 건드리지 않는다. 설치·다운로드·코드 구현 없음. NEEDS_APPROVAL 사유는 최소 Phase B 범위와 승인 식별 방식의 Owner 확정이 필요하기 때문이다. 전체 원문은 아래 요약(원문) 절에 그대로 보존했다. 보류: Owner 결정(task-0156). 외부 API·credential·비용·상시 실행 작업은 재개하지 않고, 재개는 별도 Owner 결정이 필요하다.

### task-0036 (`task-0036-cloud-llm-candidates.md`)

- 현재(447자): 9개 축(한국어/장문컨텍스트/계획수립/지시준수/안전성/비용/속도/OpenAI API 호환성/Discord 적합성)으로 OpenAI, Google Gemini, Anthropic Claude, OpenRouter 경유 Qwen 계열, 기타(DeepSeek/Mistral)를 비교했다. 1순위: OpenRouter 경유 대형 다국어 모델(기존 research-council-live-augmentation-v0.1 승인 전례 재사용 가능). 2순위: Google Gemini(OpenAI 호환 모드+최장 컨텍스트). API 키 발급/결제/외부연결/코드 변경 없음. work-order: prompts/task-0036-cloud-llm-candidates-work-order.md. NEEDS_APPROVAL 사유: 최종 벤더/모델 선택과 Phase B 진행 여부는 Owner/ChatGPT 결정 사항.
- 제안(469자): 9개 축(한국어/장문컨텍스트/계획수립/지시준수/안전성/비용/속도/OpenAI API 호환성/Discord 적합성)으로 OpenAI, Google Gemini, Anthropic Claude, OpenRouter 경유 Qwen 계열, 기타(DeepSeek/Mistral)를 비교했다. 1순위: OpenRouter 경유 대형 다국어 모델(기존 research-council-live-augmentation-v0.1 승인 전례 재사용 가능). 2순위: Google Gemini(OpenAI 호환 모드+최장 컨텍스트). API 키 발급/결제/외부연결/코드 변경 없음. NEEDS_APPROVAL 사유: 최종 벤더/모델 선택과 Phase B 진행 여부는 Owner/ChatGPT 결정 사항. 보류: Owner 결정(task-0156). 외부 API·credential·비용·상시 실행 작업은 재개하지 않고, 재개는 별도 Owner 결정이 필요하다.
- 줄인 부분:
  - "work-order: prompts/task-0036-cloud-llm-candidates-work-order.md." → 삭제

### 0033·0036의 축약과 의미 보존

- 두 건만 500자를 넘어 기존 문구를 줄인다. 줄이는 것은 work-order 파일 경로(두 건)와 0033의 하드웨어 세부값("AMD", "6C/12T", "디스크 여유 351GB")이다. 결론, 권고, 하지 않은 일("모델 다운로드/credential 발급/외부 연결/코드 구현 없음"), NEEDS_APPROVAL 사유는 그대로다.
- 줄인 정보를 잃지 않도록, task-0031·0034의 선례("전체 원문은 아래 요약(원문) 절에 그대로 보존했다")처럼 두 기록의 본문 끝에 `## 요약 (원문, task-0175 수정 전)` 절을 더해 현재 summary 전문을 그대로 옮긴다. work-order 파일은 `prompts/`에 그대로 있다.
- 0030·0032·0034는 기존 summary를 한 글자도 바꾸지 않고 문장만 덧붙인다.
- (D2에서 채택하지 않은 대안) 0033·0036도 본문 절 없이 summary 축약만 하기. 이 경우 위 세부값과 경로는 Git 이력에만 남는다.

## 범위 (Start 승인으로 확정)

| 구분 | 경로 |
| --- | --- |
| owned | `memory/tasks/task-0030-codex-chatgpt-team-manager-discord.md`, `memory/tasks/task-0032-chatgpt-team-manager-integration-research.md`, `memory/tasks/task-0033-local-llm-team-manager.md`, `memory/tasks/task-0034-local-team-manager-approval-boundary.md`, `memory/tasks/task-0036-cloud-llm-candidates.md`, `memory/tasks/task-0175-team-manager-holds-to-on-hold.md` |
| deny | `jarvis.bat`, `memory/tasks/task-0031-chatgpt-discord-claude-auto-collab-plan.md`, `memory/tasks/task-0035-local-team-manager-model-benchmark.md`, task-0156과 그 밖의 task 기록, 모든 코드·문서·SOP·master-plan(DONE 뒤 별도 기록 커밋 제외), 보존 worktree |

다섯 기록에서 바꾸는 것은 summary 한 줄, `updated_at`(task-model §7), 0033·0036의 본문 끝 원문 보존 절뿐이다. status는 기록 편집으로 바꾸지 않고 Console Hold로만 바꾼다.

## 검토와 실행 계획

SOP §4.5에 따라 tracked file인 다섯 기록의 수정은 candidate를 만들고 fresh Reviewer → QA를 통과해야 한다. Hold는 Console의 공식 쓰기(status·updated_at·`hold_from`)이고, task-0174의 교훈대로 QA 뒤에는 본문을 고치지 않는다.

1. Owner의 Start 승인 원문을 기록하고 Console Start(`START TASK`)로 이 task를 `TODO→DOING`.
2. 다섯 기록 수정(위 확정안), 이 기록에 구현·Manager 요약.
3. 사전 점검(`check_task_record.py`) → self-review 1회 → 사전 점검 재통과 → candidate commit.
4. Reviewer(exact hash, 승인 원문 동봉) → 유효한 PASS일 때만 같은 candidate로 QA. budget retry 1, repair 1. 무효 검토·유효한 지적이 예산을 넘으면 escalation.
5. QA 항목: 다섯 summary가 제안과 같고 500자 이하·백틱 없음, writer·Console parser 통과, 다섯 기록의 diff가 summary·updated_at·(0033·0036) 원문 보존 절뿐, 원문 보존 절이 baseline summary와 바이트 단위로 같음, 0031·0035·0156 blob 무변경, `/report` total = 상태별 합계, Console smoke, Discord self-check suite, SOP validator, `git diff --check`, `jarvis.bat` untracked.
6. QA PASS 뒤 HEAD = 검토된 candidate인 상태에서, 각 대상에 공식 Console Hold Preview를 열어 current NEEDS_APPROVAL → ON_HOLD, summary에 Owner·task-0156·사유·재개 조건이 보이는지, 승인 안내(Resume하면 NEEDS_APPROVAL로 돌아감)가 나오는지 확인한 뒤에만 `HOLD TASK`로 Confirm. 한 건이라도 Preview가 다르면 그 건은 Confirm하지 않고 보고한다.
7. Hold 뒤 검증: 다섯 건 `ON_HOLD`·`hold_from: NEEDS_APPROVAL`, 변경이 status·updated_at·`hold_from` 줄뿐, 0031 DOING 그대로, Task View에서 On hold 그룹, `/report`에서 ON_HOLD 5와 total = 합계, Console smoke·Discord self-check suite·`git diff --check`.
8. 이 task의 검증 근거를 Console Record Completion Evidence로 남기고, Owner 결정에 따라 Console Complete. Console 쓰기 결과(다섯 Hold와 이 task의 DONE)를 checkpoint commit으로 남기고, master-plan 최근 완료를 별도 기록 커밋으로 갱신. push는 별도 승인.

## Owner 결정 필요 (Start 전)

| # | 결정 | 권고 |
| --- | --- | --- |
| D1 | 공통 추가 문장(87자) 확정 | 위 문구 |
| D2 | 0033·0036 축약 방식 | 본문에 원문 보존 절을 더하고 summary는 위처럼 축약 |
| D3 | 8단계 Console Complete를 Manager에게 맡길지 | Owner가 정한다(SOP §8) |

## Owner 결정: D1~D3와 Start 승인 (원문)

```text
task-0175 계획의 D1~D3에 대해 다음과 같이 결정합니다.

1. D1 승인: 공통 추가 문구를 승인합니다.
`보류: Owner 결정(task-0156). 외부 API·credential·비용·상시 실행 작업은 재개하지 않고, 재개는 별도 Owner 결정이 필요하다.`
2. D2 승인: task-0033과 task-0036은 제안한 대로 summary를 500자 이내로 축약하고, 기존 summary 전문을 `요약 (원문, task-0175 수정 전)` 절로 본문에 보존합니다.
   * 기존 결론, 권고, NEEDS_APPROVAL 사유와 정책상 의미는 바꾸지 마세요.
   * 원문 보존 절이 수정 전 summary와 정확히 일치하는지 검증하세요.
   * 다른 세 건은 기존 summary를 축약하지 않고 승인된 문구만 덧붙입니다.
3. D3 승인: task-0175는 공식 SOP에 따라 Start부터 Reviewer·QA·Hold·완료 절차까지 진행하도록 승인합니다. 다만 각 단계의 필수 Preview와 Confirm 조건을 지키고, 검토 실패나 예산 소진, 예상 밖 변경이 발생하면 즉시 멈춰 보고하세요.

실행 조건

* 공식 Console Start를 먼저 진행합니다.
* task 기록 수정은 승인된 다섯 건으로 한정하고, self-review → candidate → Reviewer → QA를 완료합니다.
* Reviewer와 QA가 모두 유효하게 통과한 동일 candidate에 대해서만 Hold를 진행합니다.
* 다섯 건 각각의 Console Hold Preview에서 상태 전이와 summary 조건을 확인한 뒤 Confirm합니다.
* Hold 후 상태, `hold_from`, `/report` 합계, Task View, smoke 및 self-check를 검증합니다.
* Record Completion Evidence → Complete Preview → 공식 Confirm → DONE checkpoint → master-plan 갱신 순으로 진행합니다.
* task-0031은 DOING 그대로 유지하고, task-0035와 task-0156의 기록, `jarvis.bat`, 보존 worktree는 변경하지 마세요.
* push는 하지 마세요.

실행 전후의 task별 변경 내용과 검증 결과를 보고하세요.
```

Start 전 확인(2026-10-20 15:31 UTC): fetch 뒤 branch `main`, HEAD `7cf5c850256c63945026f8d086fc9cb88f5694f5`(기준선과 같음, origin/main과 같음), tracked 변경 없음, untracked `jarvis.bat`과 이 기록. worktree 5개. D3에 따라 Console Complete까지 Manager가 진행하되, 단계마다 Preview·Confirm 조건을 지키고 검토 실패·예산 소진·예상 밖 변경이면 멈춘다.

## 구현 착수

2026-10-20 15:31 UTC에 Jarvis Console Start(Preview + Confirm, `START TASK`)로 `TODO→DOING`을 적용했다. Preview는 TODO → DOING, 저장 위치 이 기록, `no_execution: true`였고 Confirm 결과 `result_type: updated`. 서버는 `--no-browser`로 띄운 뒤 그 프로세스만 종료했다.

## 구현

다섯 기록에 승인된 D1·D2를 적용했다(편집 시각 2026-10-20 15:31 UTC). 바꾼 것은 각 기록의 summary 한 줄과 `updated_at`(task-model §7)이고, 0033·0036은 본문 끝에 `## 요약 (원문, task-0175 수정 전)` 절을 더해 이전 summary 전문을 그대로 옮겼다. status는 바꾸지 않았다(Hold는 Console로만).

| task | summary 길이 | 기존 문구 | 원문 보존 절 |
| --- | --- | --- | --- |
| 0030 | 404 → 492 | 그대로, 승인 문구만 덧붙임 | 없음 |
| 0032 | 326 → 414 | 그대로, 승인 문구만 덧붙임 | 없음 |
| 0033 | 496 → 491 | 하드웨어 괄호를 "(Ryzen 5 7530U, RAM ~13.9GB, 통합 GPU만)"으로 줄이고 work-order 경로 삭제. 결론·권고·"모델 다운로드/credential 발급/외부 연결/코드 구현 없음"·master-plan §6 잠긴 기능 해석 질문·NEEDS_APPROVAL 사유는 그대로라 정책상 의미가 같다 | 있음 |
| 0034 | 410 → 498 | 그대로, 승인 문구만 덧붙임 | 없음 |
| 0036 | 447 → 469 | work-order 경로만 삭제. "API 키 발급/결제/외부연결/코드 변경 없음"과 NEEDS_APPROVAL 사유를 포함한 나머지는 그대로라 정책상 의미가 같다 | 있음 |

## Implementer 검증 (작업 트리 기준, candidate 전)

| # | 검사 | 결과 |
| --- | --- | --- |
| I1 | 다섯 기록 Console parser·writer 검증 | 모두 valid, status NEEDS_APPROVAL 그대로 |
| I2 | summary 조건 | 다섯 건 모두 500자 이하·백틱 없음, 승인 문구로 끝남. 0030·0032·0034는 baseline summary + 공백 + 승인 문구와 정확히 같음 |
| I3 | 원문 보존 절 | 0033·0036의 보존 절 본문이 baseline(`7cf5c85`) summary와 정확히 같음 |
| I4 | diff 범위 | 0030·0032·0034는 2줄(summary, updated_at), 0033·0036은 2줄 + 보존 절 6줄 |
| I5 | Console smoke, Discord self-check suite, SOP validator, `git diff --check` | 모두 통과(self-check 116개) |
| I6 | `/report` | total 127 = 상태별 합계 127(DOING 2: 0031·0175, NEEDS_APPROVAL 5, DONE 120) |
| I7 | 보호 대상 | 0031·0035·0156 기록과 `jarvis.bat` 무변경(`git status`에 없음), 보존 worktree 5줄, listener 없음 |

이 검증 뒤의 단계는 아래 절에 차례로 적는다.

## Manager 요약

원문 인용은 위 두 원문 블록의 문장을 그대로 옮겼다. 해석은 오른쪽 칸에만 적는다.

| # | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- |
| T1 | "패키지 B의 다음 단계로 A안을 승인합니다." / "새 task-0175를 등록하되, 우선 등록과 계획 수립까지만 진행하고 실제 기존 task 기록 수정이나 Hold 전환은 별도 단계로 진행하세요." / "목표: `task-0175 — 보류 중인 Team Manager task 5건의 ON_HOLD 전환`" | 이 목표 그대로 task-0175로 등록했다. 등록 단계에서는 기록 수정·Hold를 하지 않았다 |
| T2 | "task 등록" / "현재 SOP와 task 등록 절차를 확인하고 공식 경로로 task-0175를 등록해." / "범위는 task-0030, 0032, 0033, 0034, 0036의 보류 사유·재개 조건 기록 및 공식 Hold 전환으로 한정해." / "task-0031은 DOING 상태로 유지하며 전환 대상에서 제외해." / "기존 task-0156의 실제 기록을 읽어 보류 결정과 근거를 정확히 확인해." / "근거를 추측하거나 새로 만들지 마." | task-0172~0174 관례대로 작업 트리에 `TODO` 기록으로 등록했다(공식 경로, Start 뒤 candidate 포함). 범위는 다섯 건의 기록과 Hold로 한정했고 0031은 제외했다. task-0156의 "결정" 절을 그대로 인용해 "근거" 절에 적었다 |
| T3 | "기록 문구 계획" / "각 대상 summary에 다음 정보를 명확하게 남기는 방안을 작성해." / "결정 주체: Owner" / "보류 결정 근거: task-0156" / "보류 사유: 외부 API, credential, 비용 및 상시 실행 관련 작업을 별도 Owner 결정 전까지 진행하지 않음" / "재개 조건: 별도 Owner 결정" / "위 문구는 task-0156 원문과 대조한 뒤 확정해." / "기존 summary의 의미 있는 내용을 삭제하거나 왜곡하지 마." | 승인 문구 한 문장에 결정 주체(Owner)·근거(task-0156)·사유(외부 API·credential·비용·상시 실행 작업 재개 안 함)·재개 조건(별도 Owner 결정)을 담았고, task-0156 원문("재개하지 않는다", "재개하려면 별도 Owner 결정이 필요하다")과 대조했다. 기존 summary의 내용은 지우지 않았다(0033·0036은 본문에 원문 보존) |
| T4 | "task-0033은 summary가 496/500자이므로 특별히 주의해." / "500자 제한을 넘기지 않도록 기존 문구에서 중복·불필요한 표현을 최소한으로 줄이는 후보를 제시하고, 원래 의미가 보존되는지 설명해." / "다른 네 건도 수정 전후 summary와 글자 수를 제시해." | 0033은 하드웨어 세부값과 work-order 경로만 줄여 491자로 맞췄고 결론·권고·NEEDS_APPROVAL 사유는 그대로다. 다섯 건의 전후 summary와 글자 수는 "제안 summary"와 "구현" 절에 있다 |
| T5 | "검토 및 실행 계획" / "기록 수정이 SOP §4에 따라 Reviewer와 QA를 거쳐야 하는지 확인하고, 필요한 검토 단계를 task 계획에 포함해." / "기록 수정 검토가 완료되기 전에는 기존 task를 Hold하지 마." / "기록 수정 후에는 각 task의 공식 Console Hold Preview를 열고, Owner·사유·재개 조건·`hold_from: NEEDS_APPROVAL`을 확인한 뒤에만 Confirm하도록 계획해." / "Hold 후 상태와 `hold_from`, `/report` 집계, smoke test를 검증하고 checkpoint를 남기는 절차를 포함해." | SOP §4.5에 따라 다섯 기록 수정은 candidate → Reviewer → QA를 거친다. Hold는 같은 candidate의 Reviewer·QA PASS 뒤에만, 건별 Hold Preview에서 Owner·사유·재개 조건·`hold_from` 대상(NEEDS_APPROVAL)을 확인한 뒤 Confirm한다. Hold 뒤 상태·`hold_from`·`/report`·smoke를 검증하고 checkpoint를 남긴다 |
| T6 | "이번 단계의 제한" / "지금은 task-0175 등록과 계획까지만 진행해." / "기존 5건의 summary나 상태를 수정하지 마." / "task-0031, task-0035, `jarvis.bat`, 보존 worktree는 건드리지 마." / "Reviewer/QA 완료 전 Hold하지 마." / "커밋과 push는 별도 승인 전까지 하지 마." / "등록 결과, task ID, 제안된 summary 문구와 글자 수, 검토·전환 계획을 보고하고 멈춰." | 등록 단계의 제한이며 그 단계에서 지켰다(다섯 건·0031·0035·`jarvis.bat`·worktree 무변경, Hold·커밋·push 없음). 등록 결과와 계획을 보고하고 멈췄다 |
| T7 | "task-0175 계획의 D1~D3에 대해 다음과 같이 결정합니다." / "D1 승인: 공통 추가 문구를 승인합니다." / "`보류: Owner 결정(task-0156)." / "외부 API·credential·비용·상시 실행 작업은 재개하지 않고, 재개는 별도 Owner 결정이 필요하다.`" | 승인 문구를 다섯 summary 끝에 글자 그대로 붙였다(I2) |
| T8 | "D2 승인: task-0033과 task-0036은 제안한 대로 summary를 500자 이내로 축약하고, 기존 summary 전문을 `요약 (원문, task-0175 수정 전)` 절로 본문에 보존합니다." / "기존 결론, 권고, NEEDS_APPROVAL 사유와 정책상 의미는 바꾸지 마세요." / "원문 보존 절이 수정 전 summary와 정확히 일치하는지 검증하세요." / "다른 세 건은 기존 summary를 축약하지 않고 승인된 문구만 덧붙입니다." | 0033·0036은 summary를 축약하고 이전 summary 전문을 `## 요약 (원문, task-0175 수정 전)` 절로 보존했다. 보존 절 본문이 baseline summary와 정확히 같음을 확인했다(I3). 줄인 것은 work-order 경로와 0033의 하드웨어 세부값뿐이고, 결론·권고·master-plan §6 잠긴 기능 해석 질문(0033)·"모델 다운로드/credential 발급/외부 연결/코드 구현 없음"(0033)과 "API 키 발급/결제/외부연결/코드 변경 없음"(0036) 진술·NEEDS_APPROVAL 사유는 쓰인 그대로라 정책상 의미가 바뀌지 않는다. 0030·0032·0034는 축약 없이 문구만 덧붙였다(I2) |
| T9 | "D3 승인: task-0175는 공식 SOP에 따라 Start부터 Reviewer·QA·Hold·완료 절차까지 진행하도록 승인합니다." / "다만 각 단계의 필수 Preview와 Confirm 조건을 지키고, 검토 실패나 예산 소진, 예상 밖 변경이 발생하면 즉시 멈춰 보고하세요." | D3에 따라 Manager가 Start부터 Complete까지 진행한다. 단계마다 공식 Preview를 확인한 뒤에만 Confirm하고, 검토 실패·예산 소진·예상 밖 변경이면 멈추고 보고한다 |
| T10 | "공식 Console Start를 먼저 진행합니다." / "task 기록 수정은 승인된 다섯 건으로 한정하고, self-review → candidate → Reviewer → QA를 완료합니다." / "Reviewer와 QA가 모두 유효하게 통과한 동일 candidate에 대해서만 Hold를 진행합니다." / "다섯 건 각각의 Console Hold Preview에서 상태 전이와 summary 조건을 확인한 뒤 Confirm합니다." | Console Start를 먼저 했다("구현 착수"). 바꾼 기존 task 기록은 승인된 다섯 건뿐이고, 이 task 자신의 기록은 SOP가 요구하는 기록으로 함께 바뀐다. self-review → candidate → Reviewer → QA를 거쳐, 유효한 PASS를 받은 같은 candidate에서만 다섯 건 각각의 Hold Preview를 확인하고 Confirm한다 |
| T11 | "Hold 후 상태, `hold_from`, `/report` 합계, Task View, smoke 및 self-check를 검증합니다." / "Record Completion Evidence → Complete Preview → 공식 Confirm → DONE checkpoint → master-plan 갱신 순으로 진행합니다." | Hold 뒤 status·`hold_from`·`/report` 합계·Task View On hold 그룹·Console smoke·Discord self-check를 검증한 다음, Record Completion Evidence → Complete Preview → `COMPLETE TASK` → DONE checkpoint → master-plan 기록 커밋 순으로 진행한다 |
| T12 | "task-0031은 DOING 그대로 유지하고, task-0035와 task-0156의 기록, `jarvis.bat`, 보존 worktree는 변경하지 마세요." / "push는 하지 마세요." / "실행 전후의 task별 변경 내용과 검증 결과를 보고하세요." | 0031은 DOING 그대로, 0035·0156 기록·`jarvis.bat`·보존 worktree는 바꾸지 않는다. push하지 않는다. 실행 전후의 task별 변경과 검증 결과를 보고한다 |
| T13 | "Owner 결정: A 승인 — task-0175 기록만 수정" / "Repair 1회(예산 1/1)를 승인합니다." / "task-0175 기록의 T8과 Manager 요약에서 실제 task summary에 없는 인용 문구를 수정하세요." / "task-0036의 실제 문구: `API 키 발급/결제/외부연결/코드 변경 없음`" / "task-0033의 실제 문구: `모델 다운로드/credential 발급/외부 연결/코드 구현 없음`" / "두 문자열을 실제 기록과 정확히 일치시키세요." / "다른 task 기록 5건은 수정하지 마세요." / "수정 후 새 candidate를 만들고, 새 candidate에 대해 Reviewer → QA를 처음부터 다시 진행하세요." / "Reviewer와 QA가 동일한 candidate를 검증해야 합니다." | repair 1(예산 1/1)로 T8 해석 칸의 인용을 0036 "API 키 발급/결제/외부연결/코드 변경 없음", 0033 "모델 다운로드/credential 발급/외부 연결/코드 구현 없음"으로 바꿨고, 두 문자열이 각 summary 줄에 그대로 있는지 편집 전에 확인했다. 다섯 task 기록은 바꾸지 않았다. 새 candidate에 Reviewer → QA를 처음부터 실행하고 둘이 같은 candidate를 검증한다 |
| T14 | "검증 및 후속 절차" / "Reviewer와 QA가 유효한 PASS를 내기 전에는 Hold를 진행하지 마세요." / "둘 다 PASS하면 기존 승인 계획대로 Hold → 상태 검증 → Record Completion Evidence → Console Complete Preview/Confirm → DONE checkpoint → master-plan sync를 진행하세요." / "예산 소진, 검토 실패, 예상하지 못한 변경 또는 절차상 문제가 발생하면 즉시 멈추고 보고하세요." / "`git push`는 하지 마세요." | Reviewer와 QA가 같은 새 candidate에 유효한 PASS를 낸 뒤에만 Hold → 상태 검증 → Record Completion Evidence → Console Complete Preview/Confirm → DONE checkpoint → master-plan 기록 커밋을 진행한다. 예산 소진·검토 실패·예상 밖 변경·절차 문제면 멈추고 보고한다. push하지 않는다 |
| T15 | "향후 같은 종류의 minor 지적에 대한 원칙" / "이번 task-0175에 한해, Reviewer의 유효한 minor FINDINGS가 실제 사실 오류 또는 인용 불일치를 지적하고 repair 예산이 남아 있다면, 즉시 멈추지 말고 승인된 예산 내에서 수정한 뒤 새 candidate로 Reviewer와 QA를 다시 진행해도 됩니다." / "단, 의미 변경, 작업 범위 확대, 상태 전이 정책 변경, 예산 초과, 또는 기존 승인과 충돌하는 문제는 자동으로 수정하지 말고 Owner에게 보고하세요." / "이 원칙은 이번 task-0175에만 적용하며, SOP나 다른 task의 기본 정책은 변경하지 마세요." | 이 원칙은 task-0175에만 적용하고 SOP·다른 task는 바꾸지 않는다. repair 예산이 1/1로 소진돼 다음 repair에는 이 원칙을 쓸 수 없으므로, 다음 지적은 고치지 않고 Owner에게 보고한다. 의미 변경·범위 확대·전이 정책 변경·예산 초과·승인 충돌은 언제나 보고 대상이다 |

## 사전 점검 (첫 실행)

`check_task_record.py … --baseline 7cf5c85…`: `staged_files=6`, `violations=0`, `quote_check_unquoted=0`, `status=PASS`.

## Self-review (첫 candidate 전 1회)

`jarvis-self-review` 절차대로 1회 실행했다. 요청 파일 2026-10-20 15:33:57 UTC 작성, 결과 파일 15:34:45 UTC(`duration_ms` 46581, scratchpad 파일 시각). 사전 점검 PASS, 작업 트리 = index, 이 절 없음을 확인했고, 저장소 루트에서 `claude -p --agent self-reviewer --tools Read,Grep,Glob --output-format json`으로 실행했다(`is_error: false`). 실행 전후 `git status --short`가 같았다. self-review는 Reviewer 판정이 아니며, 여기서 고친 것은 repair가 아니다(SOP §5).

| # | 지적(요지) | 처리 |
| --- | --- | --- |
| S1 | D1·D2 승인 뒤에도 "제안 summary"·"범위" 제목이 초안으로 표시되고, D2에서 채택하지 않은 대안이 열린 선택지로 남아 있다 | 수정. 제목을 "D1·D2로 확정", "Start 승인으로 확정"으로 바꾸고 대안 줄에 "D2에서 채택하지 않은 대안"이라고 표시했다 |
| S2 | Manager 요약 T8이 "정책상 의미는 바꾸지 마세요" 조건을 해석 칸에서 다루지 않는다 | 수정. T8과 구현 표 0033·0036 행에 줄인 범위(경로·하드웨어 세부값)와 그대로 둔 정책 진술(잠긴 기능 해석 질문, 발급·결제·외부 연결 없음, NEEDS_APPROVAL 사유)을 적었다 |
| S3 | 인용부호 안 문구 "다운로드/credential/외부 연결/코드 구현 없음"이 실제 summary("모델 다운로드/credential 발급/외부 연결/코드 구현 없음")와 다르다 | 수정. 두 곳을 실제 문구로 고쳤다 |

이 기록만 고쳤고 다섯 task 기록은 바꾸지 않았다. updated_at은 이 수정 시각 2026-10-20 15:35 UTC(편집 스크립트가 UTC 시계를 읽어 넣음)다. 수정 뒤 사전 점검: `staged_files=6`, `violations=0`, `quote_check_unquoted=0`, `status=PASS`.

## Candidate 1

`86a5d98be4b9d4c1de5b08329cc82b681ccce31b`(parent = baseline `7cf5c85`, 커밋 2026-10-20 15:35:25 UTC). 변경 6개 파일 = owned.

## Reviewer 1 (`86a5d98`, FINDINGS minor 1, 유효)

`self_deviations: []`. findings: Manager 요약 T8이 인용부호 안에 "발급/결제/외부 연결 없음"을 "쓰인 그대로"라고 적었지만 그 문자열은 두 축약 summary 어디에도 없다(0036 "API 키 발급/결제/외부연결/코드 변경 없음", 0033 "모델 다운로드/credential 발급/외부 연결/코드 구현 없음"). self-review S3 수정 때 새로 넣은 문구였다.

Manager 판정: 지적이 맞다. D3의 "검토 실패 … 즉시 멈춰 보고"에 따라 고치지 않고 Owner에게 보고했다.

## Owner 결정: Repair 1 (원문)

```text
Owner 결정: A 승인 — task-0175 기록만 수정

1. Repair 1회(예산 1/1)를 승인합니다.
   * task-0175 기록의 T8과 Manager 요약에서 실제 task summary에 없는 인용 문구를 수정하세요.
   * task-0036의 실제 문구: `API 키 발급/결제/외부연결/코드 변경 없음`
   * task-0033의 실제 문구: `모델 다운로드/credential 발급/외부 연결/코드 구현 없음`
   * 두 문자열을 실제 기록과 정확히 일치시키세요. 다른 task 기록 5건은 수정하지 마세요.
   * 수정 후 새 candidate를 만들고, 새 candidate에 대해 Reviewer → QA를 처음부터 다시 진행하세요. Reviewer와 QA가 동일한 candidate를 검증해야 합니다.
2. 검증 및 후속 절차
   * Reviewer와 QA가 유효한 PASS를 내기 전에는 Hold를 진행하지 마세요.
   * 둘 다 PASS하면 기존 승인 계획대로 Hold → 상태 검증 → Record Completion Evidence → Console Complete Preview/Confirm → DONE checkpoint → master-plan sync를 진행하세요.
   * 예산 소진, 검토 실패, 예상하지 못한 변경 또는 절차상 문제가 발생하면 즉시 멈추고 보고하세요.
   * `git push`는 하지 마세요.
3. 향후 같은 종류의 minor 지적에 대한 원칙
   * 이번 task-0175에 한해, Reviewer의 유효한 minor FINDINGS가 실제 사실 오류 또는 인용 불일치를 지적하고 repair 예산이 남아 있다면, 즉시 멈추지 말고 승인된 예산 내에서 수정한 뒤 새 candidate로 Reviewer와 QA를 다시 진행해도 됩니다.
   * 단, 의미 변경, 작업 범위 확대, 상태 전이 정책 변경, 예산 초과, 또는 기존 승인과 충돌하는 문제는 자동으로 수정하지 말고 Owner에게 보고하세요.
   * 이 원칙은 이번 task-0175에만 적용하며, SOP나 다른 task의 기본 정책은 변경하지 마세요.
```

## Repair 1

- T8 해석 칸의 인용을 두 기록의 실제 문자열로 바꿨다: "모델 다운로드/credential 발급/외부 연결/코드 구현 없음"(0033), "API 키 발급/결제/외부연결/코드 변경 없음"(0036). 두 문자열이 현재 0033·0036 summary 줄에 그대로 있는지 편집 스크립트가 먼저 확인했다.
- SOP가 요구하는 기록도 더했다: 기준선 budget 행(`repair_count=1`), summary, 위 Candidate 1·Reviewer 1·Owner 결정 원문·이 절, Manager 요약의 T13~T15 행(위 원문의 인용과 해석), updated_at(2026-10-20 16:07 UTC, 편집 스크립트가 UTC 시계를 읽어 넣음).
- 다섯 task 기록은 바꾸지 않았다. 이 repair로 candidate가 바뀌므로 Reviewer 1 결과는 쓰지 않고 새 candidate에 Reviewer → QA를 처음부터 실행한다. 결정 3의 원칙(이 task에 한해 예산 안의 사실·인용 오류 minor는 고친 뒤 재검토)은 repair 예산이 소진돼(1/1) 다음 repair에는 적용할 수 없으므로, 다음 지적은 Owner에게 보고한다.
