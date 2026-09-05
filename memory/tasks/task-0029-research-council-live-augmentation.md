# task-0029-research-council-live-augmentation

- id: `task-0029-research-council-live-augmentation`
- title: `Research Council live LLM augmentation via OpenRouter`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-08-25 01:41 UTC`
- updated_at: `2026-08-26 10:28 UTC`
- summary: `Research Council 전용 OpenRouter live LLM augmentation. 2026-08-25 Owner 승인 패키지 research-council-live-augmentation-v0.1 범위로, llm_advisor LIVE 모드에 z-ai/glm-4.6을 deepinfra/fp4로 고정하고 fallback off, zdr on, data_collection deny로 두며 API 키는 환경변수에서만 읽는다. 출력은 additive-only이고 결정론적 결과는 불변이며 golden·benchmark·mutation·demo·Jarvis Console 경로는 건드리지 않는다. commit c7f2b99로 10개 파일을 커밋했고 스모크가 통과했다(exit 0, LIVE 경로 10건 신규). 후속 작업 없음. 전체 원문은 아래 요약(원문) 절에 그대로 보존했다.`
- source_command: `Owner decision`


## 요약 (원문)

이 절은 task-0054에서 옮긴 원본 summary 전문이다. summary 필드가 500자 상한을 넘어 canonical 검증에 실패했기 때문이며, 내용은 한 글자도 줄이지 않고 그대로 보존했다.

OpenRouter live LLM augmentation for Research Council only, approved by Owner on 2026-08-25 under package research-council-live-augmentation-v0.1. Scope is the llm_advisor LIVE mode with z-ai/glm-4.6 pinned to deepinfra/fp4, fallbacks off, zdr on, data_collection deny, OPENROUTER_API_KEY from the environment only, additive-only output, deterministic result unchanged, and no golden, benchmark, mutation, demo or Jarvis Console path. Committed as commit c7f2b99 (10 files: research_council/__init__.py, benchmark_snapshot.py, llm_advisor.py, openrouter_advisor.py (new), run_demo.py, run_golden_cases.py, run_local_app.py, run_smoke_tests.py, .env.example (new), docs/codex-operating-rules.md). Verified with python apps/research-council/run_smoke_tests.py -> "Research Council smoke tests passed" (exit 0), including 10 new LIVE-path tests. No follow-up work identified in scope.

## Escalation record

AGENTS.md treats external API, external LLM, and credential use as an immediate
escalation gate that is independent of budget. This task is that gate being
passed once, for one bounded package. The gate itself stays in force: any
external API, LLM, or credential use outside the boundary recorded here needs a
separate Owner approval.

Owner approved on 2026-08-25:

1. P1. OpenRouter external LLM calls and OPENROUTER_API_KEY use, limited to the
   package research-council-live-augmentation-v0.1.
2. P3. OpenRouter automatic routing and fallback are forbidden. Provider and
   model are pinned explicitly.
3. P4. Request-level zero-retention is enforced. A provider or model that does
   not satisfy it is not used on the LIVE path.
4. P5. The LLMResearchAdvisor protocol is left untouched. A
   LLMAugmentationCandidate generator is injected instead.
5. P6. OPENROUTER_API_KEY is read from the environment only. A missing key or a
   network error degrades augmentation to OFF.

## Boundary

| Boundary | Rule |
|---|---|
| Application | Research Council only. Jarvis Console, Hermes, Daily AI Radar and the Discord adapter are out of scope. |
| Activation | Explicit opt-in. LIVE is never a default anywhere. |
| Source of truth | claims, evidence_ledger, reviewer_critiques, experiments, recommendation, markdown_report, profile and warnings are read-only to the LIVE path. |
| Output | additive-only, written to optional_llm_augments and bounded by ALLOWED_AUGMENTATION_CATEGORIES. |
| Deterministic runners | LIVE is unavailable in golden cases, benchmark snapshots, mutation tests, the demo runner, the demo batch script and the local GUI. |
| Routing | Provider and model pinned. OpenRouter fallback and cost routing disabled. |
| Privacy | Request-level zero-retention data policy required. |
| Credential | os.environ only. No file reads, and no key value in logs, errors or artifacts. |
| Failure | Timeout, rate limit, network error and malformed responses degrade to an OFF-equivalent result and never propagate as a pipeline failure. |

## Contracts that must not change

1. merge_validated_llm_suggestions keeps its single-keyword replace call.
2. ALLOWED_AUGMENTATION_CATEGORIES stays at the same five categories.
3. The six rejection filters in llm_advisor stay in force on every path.
4. to_metadata keeps reporting deterministic_source_of_truth as true.
5. markdown_report keeps being rendered before augmentation runs.
6. Jarvis Console keeps pinning LLMAugmentationMode.OFF at its call site.
7. PROJECT_CONTROL_FORBIDDEN_ACTIONS stays as written.
8. The existing OFF, TEST_SAFE and TEST_NOISY assertions pass unmodified.

## Verified pin

Confirmed once against the official OpenRouter endpoints API and the
authoritative Zero Data Retention list on 2026-08-25, and recorded verbatim in
the adapter constants: model_id z-ai/glm-4.6, tag deepinfra/fp4, context_length
202752, pricing.prompt 0.0000005, pricing.completion 0.000002. DeepInfra carries
training false, retainsPrompts false and requiresUserIDs false.

## Next step

Implementation is committed as commit `c7f2b99` on `main`. The change set is
the adapter module, the LIVE mode and generator injection, the
deterministic-runner exclusions, the benchmark snapshot guard, the new tests,
the env example and the operating-rules exception. No next step is pending
inside this task's approved boundary.
