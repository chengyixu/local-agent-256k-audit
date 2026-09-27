---
license: other
license_name: local-agent-research-artifact-notice
license_link: LICENSE
pretty_name: Local Agent 256K Audit
language:
- en
tags:
- apple-silicon
- local-inference
- long-context
- agent-evaluation
- reproducibility
---
# Local Agent 256K Audit

**Chengyi Xu and KLIK team — KLIK Research, September 2026**

Two AI-assisted engineering reports, with sanitized measurements and selected method code:

1. [Beyond Decode Speed: Exact Token Admission and Real-Workspace Evaluation at 256K Context](agent-budget/main.pdf) — [LaTeX source](agent-budget/main.tex).
2. [A Local Image Service Is Not a Chat Model: Reproducible Qwen-Image 2.1 Deployment on Apple Silicon](local-image/main.pdf) — [LaTeX source](local-image/main.tex).

**These are public research reports, not peer-reviewed journal acceptances. No DOI is claimed.**

## What the measurements establish

On one Apple M4 Max / 64 GiB workstation, normal and separate abliterated Ornith 1.5 35B-A3B Q4 checkpoints processed **256,222 actual initial tokens** in full-extension Pi sessions inside an isolated real repository checkout. Under the explicitly labelled D-V condition (exact local token admission, native JSON schema, and explicit verbatim-command instruction), each target completed three bounded audit runs with correct executed results, receipts, bare JSON and a literal successful command.

| Target | Visible streaming across those 3 runs | Full final-turn visible rate, including preflight/reasoning/wait | Bounded audit passes |
|---|---:|---:|---:|
| Normal Ornith Q4 | 45.82–96.58 tok/s | 16.72–40.95 tok/s | 3/3 |
| Abliterated Ornith Q4 | 44.34–48.13 tok/s | 16.34–23.70 tok/s | 3/3 |

**Not established:** a universal 20 tok/s end-to-end floor, flawless code reasoning, or globally optimal intelligence. Cold prefill took roughly 23–34 minutes in measured runs. The ordinary full-extension normal baseline completed only 1/3 runs; baseline strict-quality passes were 0/3 for both targets. Freeform repository reviews retain factual errors. An additional Empero 35B distillation was measured and not selected due to major review errors. Failed runs are retained in the evidence tables rather than replaced by later successes.

The requested Qwen-Image 2.1 Uncensored Q6 service generated a valid, nonblank 512×512 PNG through the actual registered MCP → native API path in 373.74 s. Local OCR recovered `LOCAL`. This is integration evidence, **not expert visual-quality assessment**. Image performance is not measured in text tokens/s.

## Method and reproduction boundaries

- [`evidence/agent-results.json`](evidence/agent-results.json): whitelist-only numerical records. `null` means unknown, not zero. Conditions differ and must not be pooled as identical trials.
- [`evidence/image-result.json`](evidence/image-result.json): image request, timing, checksum and functional checks.
- [`evidence/model-provenance.json`](evidence/model-provenance.json): pinned model/runtime metadata and original download verification.
- [`code/`](code): selected measurement, privacy-export and exact-admission code/tests.
- [`protocol.md`](protocol.md): task and measurement definitions without private source.
- [`research-ledger.md`](research-ledger.md): source/technique coverage and evidence boundaries.

The reference corpus contains private software source. **Private source, raw source-bearing transcripts, credentials and private repositories are not published.** Consequently, these artifacts do not enable byte-identical public reproduction of the original tasks. The code and protocol support method replication with an independently authorized repository; such a substitution is a new experiment.

Exact admission uses the local runtime's `/apply-template` and `/tokenize`, leaving a declared 64-token margin inside the real 262,144-token window. It never truncates or compacts the input and never increases the context limit. Failure aborts locally; no cloud fallback exists. JSON schemas constrain structure only, not expected numeric answers, receipts or command strings. Responses were not repaired after generation.

## Running selected tests

Requires Python 3.13+ and Node 24+ (native TypeScript stripping for the extension-handler test):

```sh
cd code
python3 -m unittest test_pi_measure test_deep_evidence test_task_d_quality test_public_evidence
node --test test_exact_budget.mjs
```

These are method tests, not local model inference. Runtime integration also depends on the actual Pi installation and model server. The installation-specific controller/CC Switch tests were run separately on the target host; do not equate the public subset with every deployment gate.

## Building papers

The sources use `klik-paper.sty`. With a conventional TeX environment, build with XeLaTeX/latexmk and shell escape disabled. The recorded host build used the LaTeX skill's `compile.py` driver with the explicit `tools/xelatex` compatibility adapter, which invokes Tectonic `--untrusted`; it is not a claim that a system XeLaTeX distribution was installed. Both compiled PDFs were checked for title/author metadata, text extraction, unresolved references, and overfull boxes. No independent human layout review is claimed.

## Licenses and disclosures

See [LICENSE](LICENSE). No model weights are distributed. **Qwen-Image 2.1 use is research/evaluation-only without separate permission.** Original integration code is MIT; third-party software/model licenses are separate. The synthetic generated image is provided for research inspection subject to applicable model terms.

AI tools materially assisted experiments, implementation, analysis and drafting. No independent human manuscript review, funding declaration, conflict attestation or peer acceptance is asserted. Historical high-speed claims are not substituted for these actual-workspace results.

## Citation

Use [CITATION.cff](CITATION.cff). Cite the specific report and repository revision, not a blanket “champion” speed claim.
