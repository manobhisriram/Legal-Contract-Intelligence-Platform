# Evaluation Framework

The repository contains the tooling used to measure review quality. It does **not** include published benchmark scores: results depend on the model versions, prompts and contract set used, and should be generated and recorded for the environment being assessed.

## LLM judge (`backend/agents/llm_judge.py`)

Scores a review result on four dimensions, each 0–1, combined with fixed weights.

| Dimension | Weight | How it is computed |
|---|---|---|
| Correctness | 30% | Share of ground-truth clauses marked `must_find` that appear among extracted clause types (substring match) |
| Severity calibration | 25% | Per expected clause: 1.0 exact level, 0.5 one level away, 0 otherwise or if the clause was not found |
| Completeness | 25% | 70% recall of expected high and critical clauses plus 30% deal-breaker agreement (missed expected deal breaker 0.5, unexpected deal breaker 0.8) |
| Actionability | 20% | LLM-assessed specificity, clause citation, clarity of recommended action and redline quality (Groq); heuristic fallback if the call fails |

Grades map overall score to A (≥0.90), B (≥0.80), C (≥0.70), D (≥0.60), F.

**Ground truth.** `BENCHMARK_GROUND_TRUTH` holds three illustrative annotated contract profiles (SaaS, NDA, vendor) that demonstrate the schema. `run_judge_on_review(review, ground_truth)` and `run_benchmark_evaluation(reviews, ground_truths)` accept real annotations, for example derived from a labelled corpus such as CUAD.

**API behaviour.** `POST /api/evaluation/run` evaluates the 20 most recent completed reviews without ground truth. In that mode correctness, calibration and completeness use simple heuristics (clause counts and the share of high-risk findings) and only actionability is model-assessed. Treat those scores as a trend signal, not as accuracy.

## Red-team suite (`backend/agents/red_team_agent.py`)

Fifty synthetic adversarial contracts, ten in each category:

1. Buried data-rights waivers
2. Disguised liability caps (formula-based)
3. Auto-renewal with unusual terminology
4. Cross-reference exploits (protections negated by a schedule or exhibit)
5. Mixed-language contracts

Each contract declares the hidden risk it contains. A run passes every contract through the review pipeline and checks whether the output surfaces that risk (keyword and risk-level based detection over clauses, top issues and deal breakers). Failure rate is reported overall and per category, stored in `red_team_runs`, and `generate_patch_recommendations` proposes prompt additions for categories with failures.

**Limits.** Detection is keyword-based and can both over- and under-credit; the suite is synthetic and small. It is a regression harness for prompt changes, not a measure of real-world recall.

## Recommended practice

- Record the model versions, prompt revision and contract set alongside each stored run.
- Keep a labelled holdout set and call `run_benchmark_evaluation` with real ground truth for headline numbers.
- Re-run the red-team suite after any prompt or model change and compare per-category failure rates.
- Review stored runs through `/api/evaluation/history` and `/api/redteam/history`, and the Datadog quality-gate widgets.
