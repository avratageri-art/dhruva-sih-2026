# Synthetic reliability benchmark

> Caveat: this benchmark is synthetic and tests known failure modes. It does not estimate real-world attribution accuracy.

| Model | Precision | Recall | Coverage | False-link rate |
|---|---:|---:|---:|---:|
| Similarity baseline | 21.8% | 70.6% | 91.7% | 100.0% |
| Reliability engine | 100.0% | 70.6% | 20.0% | 0.0% |

## Failure-family breakdown

| Family | Cases | Baseline false links | Engine false links | Engine supported | Dominant abstention |
|---|---:|---:|---:|---:|---|
| common_handle | 7 | 7 | 0 | 0 | INSUFFICIENT |
| conflicting | 7 | 7 | 0 | 0 | CONTESTED |
| copied_posts | 7 | 7 | 0 | 0 | INSUFFICIENT |
| impersonation | 7 | 7 | 0 | 0 | TAINTED |
| same_community_writing | 7 | 7 | 0 | 0 | INSUFFICIENT |
| shared_hosting | 8 | 8 | 0 | 0 | SHARED_INFRA_ONLY |
| true_strong | 12 | 0 | 0 | 12 | — |
| true_weak | 5 | 0 | 0 | 0 | INSUFFICIENT |

The conservative engine intentionally trades coverage for precision on this adversarial dataset. Re-run `python scripts/evaluate.py` after any configuration change; generated results replace this file.
