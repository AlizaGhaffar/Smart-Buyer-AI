# Evaluation results

Dataset: 48 hand-labelled fictional companies (dev 30, held-out test 18).

Positive = Confirmed / Strong / Possible. Baseline = original finder.py `score_lead() > 0` rule on the same text.

## all (n=48)

| Metric | Old keyword baseline | KRR system |
|---|---|---|
| Precision | 33% | 100% |
| Recall | 55% | 100% |
| F1 | 42% | 100% |
| False-positive rate | 79% (22/28) | 0% (0/28) |
| Evidence coverage of positives | n/a (no quotes) | 100% |
| 5-class accuracy | n/a (no classes) | 100% |

## dev (n=30)

| Metric | Old keyword baseline | KRR system |
|---|---|---|
| Precision | 32% | 100% |
| Recall | 50% | 100% |
| F1 | 39% | 100% |
| False-positive rate | 72% (13/18) | 0% (0/18) |
| Evidence coverage of positives | n/a (no quotes) | 100% |
| 5-class accuracy | n/a (no classes) | 100% |

## test (n=18)

| Metric | Old keyword baseline | KRR system |
|---|---|---|
| Precision | 36% | 100% |
| Recall | 62% | 100% |
| F1 | 45% | 100% |
| False-positive rate | 90% (9/10) | 0% (0/10) |
| Evidence coverage of positives | n/a (no quotes) | 100% |
| 5-class accuracy | n/a (no classes) | 100% |

## Per product (KRR system, all cases)

| Product | Precision | Recall | FPR |
|---|---|---|---|
| Duck Down | 100% | 100% | 0% |
| Raw Sheep Wool | 100% | 100% | 0% |
| Cashmere | 100% | 100% | 0% |

## Confusion matrix (rows = manual label, columns = system)

| label \ system | confirmed | strong | possible | insufficient | not |
|---|---|---|---|---|---|
| confirmed_purchaser | 5 | 0 | 0 | 0 | 0 |
| strong_potential_buyer | 0 | 9 | 0 | 0 | 0 |
| possible_potential_buyer | 0 | 0 | 6 | 0 | 0 |
| insufficient_evidence | 0 | 0 | 0 | 10 | 0 |
| not_relevant | 0 | 0 | 0 | 0 | 18 |

## Misclassified cases (0)

| Case | Split | Note | Label | System | Rules fired |
|---|---|---|---|---|---|
