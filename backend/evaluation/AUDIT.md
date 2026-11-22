# Automatic audit of live runs

3 companies from 1 saved live searches, 4 evidence quotes, 2 contacts.

**Result: 4 problem(s)**

| Check | Result |
|---|---|
| Every quote is verbatim text from a fetched company page | FAIL (4) |
| No evidence from snippets / directories / third-party pages | pass |
| Every qualified lead has a rule backed by a material quote | pass |
| No qualified lead with material usage 'none' | pass |
| Every Confirmed Purchaser has a sourcing fact | pass |
| Every Not Relevant lead names its veto rule / reason | pass |
| Every Insufficient lead states why | pass |
| Every contact's source is a checked page | pass |

Facts dropped by the grounding check before reasoning: 0.

## Classes

| Class | Companies |
|---|---|
| strong_potential_buyer | 1 |
| insufficient_evidence | 1 |
| not_relevant | 1 |

## Rules that fired (shows the KRR rules actually run)

| Rule | Times fired |
|---|---|
| DD-P1 | 1 |
| G-R1 | 1 |
| G7 | 1 |

## Problems

- duck_down__japan/northwind.test: quote not found on its page: 'We buy 500 tonnes of duck down every year.'
- duck_down__japan/northwind.test: quote not found on its page: 'We buy 500 tonnes of duck down every year.'
- duck_down__japan/northwind.test: quote not found on its page: 'We buy 500 tonnes of duck down every year.'
- duck_down__japan/northwind.test: quote not found on its page: 'We buy 500 tonnes of duck down every year.'
