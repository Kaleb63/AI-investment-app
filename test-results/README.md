# Test results: October 17, 2026

**140 passed, 0 failed, 2 skipped** (142 collected).

Command, run from the repository root:

```text
python -m pytest -q --junitxml=test-results/pytest.xml
```

Recorded pytest output:

```text
140 passed, 2 skipped in 7.75s
```

Machine-readable details are in [`pytest.xml`](pytest.xml). This record describes
the local run, not a completed GitHub Actions run.

## Environment

- Windows; Python 3.14.4; pytest 9.1.1.
- FastAPI 0.143.3; Pydantic 2.14.1; OpenAI SDK 3.33.0.
- Base repository commit: `71c092b2fde78aad34e7d7b053d506c050c67006`.
- GitHub Actions is configured to run on the repository's Python 3.12 target;
  that hosted run has not been executed here.
- Finnhub, Plaid, and OpenAI calls are mocked or replaced with synthetic data.
  No live model accuracy or availability claim is made by this offline run.

## Coverage

| Test module | Passed | Skipped | Main checks |
| --- | ---: | ---: | --- |
| `test_ai_validation.py` | 58 | 0 | Hand-calculated figures, weights, missing data, signs/units, fabricated claims, malformed/refused/incomplete output |
| `test_stock_endpoints.py` | 23 | 0 | Both stock endpoints, exact scores, ticker validation, provider failures, persisted snapshots |
| `test_portfolio_endpoints.py` | 19 | 0 | Both portfolio routes, auth/ownership, allocation, HHI, ranking, missing data, provider failures |
| `test_explanation_endpoints.py` | 6 | 0 | HTTP responses through actual explanation validation and deterministic rendering |
| `test_scoring_explanations.py` | 6 | 0 | Zero versus negative reasons; unchanged numerical scoring |
| Existing backend tests | 28 | 0 | Scoring, portfolio, screens, authentication, security, Plaid, services |
| `test_live_ai_evaluation.py` | 0 | 2 | Optional paid OpenAI grounding evaluations, disabled by default |
| **Total** | **140** | **2** | **No failures or errors** |

Examples verified against independent expected calculations include a 79.7 score
with 85% coverage, custom-weight score 79.2 with 90% coverage, and a five-position
portfolio with weights 40/25/20/10/5, top-three concentration 85%, HHI 2750, and
effective position count 3.64. Every displayed AI explanation sentence is rendered
from a verified catalog entry; model-written prose and financial values are never
displayed. Mandatory category and missing-data disclosures cannot be omitted.

## Reproducing the live evaluations

Set `OPENAI_API_KEY` and `RUN_LIVE_OPENAI_EVAL=1`, then run:

```text
python -m pytest backend/tests/test_live_ai_evaluation.py -q
```

These calls use the app's existing `OPENAI_MODEL` setting. No live calls were made
for this report. The checks evaluate factual grounding, rather than investment
performance or whether the supplied market data itself is correct.
