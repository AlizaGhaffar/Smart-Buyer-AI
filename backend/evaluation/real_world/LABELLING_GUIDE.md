# Labelling guide (real-world evaluation)

You label each company **yourself**, using its website, **before** looking at the system's
answer. The sheet `labelling_sheet.csv` deliberately does not show what the system decided.
Do not open `system_outputs.json` until you have finished.

## For each row

1. Open the `website` (and, if needed, the pages in `pages_the_system_read`).
2. Ask one question: **Would this company plausibly buy the raw material in the `product` column?**
3. Put one of these in the `label` column:

| Label | Use it when |
|---|---|
| `buyer` | The company processes, spins, weaves, knits, fills or manufactures products **from this material**, or trades the raw material. Example: a wool scourer, a duvet maker using duck down, a cashmere spinning mill. |
| `not_buyer` | Retailer or brand that only sells finished goods; farm, herder or producer that **sells** the material; directory, news site, association; unrelated business; uses only synthetic or other fibres. |
| `unsure` | You cannot tell: the site does not load, it is not in a language you can read, or it says too little. |

4. Optionally write a short reason in `notes` (e.g. "makes wool carpets", "only a shop").

## Rules for a fair test

- Judge **the company**, not the product name. A café called "Cashmere" is `not_buyer`.
- Being in a related industry is not enough. A pillow maker that never says what filling it
  uses is `unsure` unless you can find the filling on its site.
- Take about 1-2 minutes per company. Do not search other websites about the company:
  judge only from its own website, like the system does.
- Goose-down-only companies for Duck Down: mark `buyer` if they clearly work with down (they
  could plausibly buy duck down), and write "goose only" in the notes.

When you are done, save the file as CSV (keep the file name), then run:

```
cd backend
python -m evaluation.real_world score
```

The results are written to `evaluation/REAL_WORLD_RESULTS.md`.
