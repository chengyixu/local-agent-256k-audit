# Protocol and evidence boundaries

## Hardware and admission

Apple M4 Max, 40-core GPU, 64 GiB unified memory, macOS 27 (26A428). Variable real-workstation load; no quiet-host generalization. One large engine at a time. Text preset: 28 GiB Metal, 8 GiB disk cache, 512-row prefill cap, real combined context 262144. Native watchdog unchanged.

## Workloads

- **A — freeform repository review:** trace a structured request through facade/client/retry/deadline/model-override implementation and tests; 400–650 words; two code-supported risks. Real isolated checkout, read-only, no credentials or external service calls. Source comparison found errors in all compared review configurations; those are not silently counted as strict passes.
- **B — repair (earlier lab evidence):** a deliberately injected retry-cap bug in an isolated real checkout, followed by independent gates/full tests. Do not describe the injected bug as a production discovery or inherit results across variants.
- **D — deep code-execution audit:** source attachment plus three position-separated receipts; read the actual retry implementation; execute three policy cases and status checks; recover receipts without rereading the attachment; report the successful command. Full-tool reference variant has 155 real source sections after explicit removal of 11 complete sections to fit the extension tool schemas. Initial backend input256150. Original controlled reference remains separate.
- **D-V:** same questions/reference, plus explicit character-for-character command copying. Initial backend input256222. Native JSON schema supplies structure only. No expected answer values, receipts or command literals enter the schema; no answer postprocessing.

The private reference corpus and raw source-bearing traces are withheld. Public users must substitute their own authorized corpus and recalibrate actual tokens; that is not byte-identical replication. A context-window metadata label is insufficient evidence.

## Sampling and comparisons

Recorded ordinary Splash/Pi requests used backend defaults: temperature1.0, top_p0.95, top_k20, random seed, unless separately labelled greedy. A separate abliterated greedy trial (temperature0, top_p1, seed42) did not cure formatting. Do not relabel earlier stochastic results as greedy. Reported model comparisons are descriptive, not randomized causal estimates or a global ranking.

## Timing

- Visible stream: final visible text, retokenized by target tokenizer, divided by first nonempty text delta to message_end. Excludes earlier reasoning/prefill.
- Assistant request: message_start to message_end; may omit provider-hook preparation before stream creation.
- Full final cycle: turn_start to message_end; includes exact-token preflight and reasoning/waiting.
- Whole task: process invocation through completion, including all tools, all turns and startup.
- Whole-task completion-token rates may include reasoning and tool syntax; never label them visible output.
- Tool-only parser bursts and sub0.1s windows do not establish decode TPS. Keep failures/timeouts/length cutoffs and unknown metrics.

## Output and execution checks

Strict raw JSON parsing rejects fences/prose. Receipt order and case/status values are checked. Command fidelity requires exact membership in successful tool-call arguments. This surface checker does not prove execution semantics by itself: source/tool results were inspected separately. Extra discovery, echo or redundant execution is recorded as efficiency overhead. Read/bash emitted together must not be represented as read-informed planning.

## Image verification

Requested abenzerps checkpoint at pinned revision; native sd.cpp Metal. Actual registered stdio MCP initialize/list/status/generate path,512x512,20steps,seed42. Validate PNG/size/hash/nonblank, native dimensions/sampler/time, OCR/color heuristics and controller lock. No text-TPS/context claim and no invented visual-quality review. Research/evaluation license restriction retained.

## Failure preservation

Normal full-extension baseline1/3 completed, both variants0/3 strict-quality baseline. Exact-budget-only normal3/3 completed but0/3 strict-quality. Schema alone fixes JSON but not command abbreviation. D-V method reaches bounded3/3 per target. A monitor interruption was infrastructure, not a model pass; foreground abliterated D-V1 reused a partial cache and is not called cold. Freeform review errors remain in the report.
