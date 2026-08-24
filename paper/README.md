# paper/ — everything about the write-up, and the rules for editing it

This directory is the single home for paper artifacts. Nothing paper-related lives at
the repo root. If you are about to edit the paper — human or agent — read the three
governance files first; they exist because every past defect in this paper came from
editing prose without them.

## Layout

| Path | What it is |
|---|---|
| [`AUDIT_LOG.md`](AUDIT_LOG.md) | Chronological record of every verification pass, with open items. **Start here to learn the current state.** |
| [`CLAIMS_EVIDENCE.md`](CLAIMS_EVIDENCE.md) | Registry of claims whose evidence lives outside `tables/*.csv` (licences, cited-paper numbers, revision history, load-bearing hedges). **Consult before cutting or rewording any caveat.** |
| `submission/` | The verified NeurIPS 2026 submission: 27-pp PDF, LaTeX source zip, verification report, and the change log the team signed off on. Last fully-verified version. |
| `drafts/` | Dated working drafts. Currently: the 2026-08-23 condensed 18-pp PDF (⚠ source not in repo; three known regressions — see AUDIT_LOG entry 4) and the §3 rewrite experiments of 2026-08-17. |
| `related_work.md` | Related-work research notes feeding §2. |
| `appendices.md` | Generated Appendix B/C content (see "Building the appendices" below). |
| `methodology_draft.md`, `*.docx`, `*.tex`, `*.sty` | Deliberately **git-ignored** (double-blind policy: working documents and templates stay local). The anonymized submission source is preserved in `submission/BudgetGuard_NeurIPS2026_source.zip`. |

## Version lineage

1. **Approved draft** — `Budget Guard - Research Paper (1).docx` (local only, ignored).
2. **Verified submission** (2026-08-19/20) — `submission/budget_guard_neurips2026.pdf`,
   built from `submission/BudgetGuard_NeurIPS2026_source.zip`. Every claim checked
   against `tables/*.csv`; all 27 references verified against primary sources. Deltas
   from the approved draft: `submission/CHANGES_since_approved_draft.md`.
3. **Condensed rewrite** (2026-08-23) — `drafts/2026-08-23_condensed_18pp.pdf`.
   Numerically clean but carries three regressions and **its LaTeX source is not in
   this repo**. Do not submit or further edit until the source is recovered and
   AUDIT_LOG entry-4 open items are closed.

## Editing rules

1. **Numbers**: never hand-edit a number in the paper. Fix the experiment or table,
   run `make repro-all`, and let `scripts/check_headline_numbers.py` +
   `scripts/check_paper_numbers.py` confirm the text matches the regenerated
   `tables/*.csv` (they exit non-zero on any mismatch).
2. **Caveats and disclosures**: check `CLAIMS_EVIDENCE.md` before trimming anything
   that looks like a hedge, a licence note, or an odd self-reference. The 2026-08-23
   pass showed that these are exactly what a low-context edit deletes first — and they
   are the parts previous audits demanded.
3. **New claims**: a claim entering the paper needs either a row in a generated table
   (then extend the checkers) or a row in `CLAIMS_EVIDENCE.md` — in the same change.
4. **New drafts**: date-prefixed, into `drafts/`, with source. A PDF without its
   source is an open item the moment it lands.
5. **Sign-off**: changes in claim *meaning* go through the team, recorded in the style
   of `submission/CHANGES_since_approved_draft.md`.

## Building the appendices

The submission has three appendices; they are not the same kind of thing, and that
difference decides how you edit them.

| Appendix | Contents | Where it comes from |
|---|---|---|
| A. Method glossary | Plain-English definitions (coverage, q̂, α, width, split conformal, CQR, Mondrian, ACI, DtACI, windowed-CQR, joint coverage, censoring) | Prose. Lives in the document only. Edit it there. |
| B. Per-run dataset composition | Rollouts and prefix samples for every model × environment run | **Generated** from `tables/allruns.csv` and `tables/transfer_warehouse.csv` |
| C. Supporting figures | Model-swap transfer and conditional coverage figures, with captions | **Generated** captions; images from `figures/` |

```bash
make appendices        # or: python3 scripts/make_appendices.py
```

This writes `paper/appendices.md`, paste-ready. The generator exits non-zero and
explains itself if a source table or figure is missing (`make repro-all`), if there are
not exactly 19 model × environment runs (a partial BAGEN download — `make doctor`, then
`python scripts/fetch_bagen.py`), or if a figure is older than the table it draws from.

`tests/test_appendices.py` pins the run-label mapping in
`budget_guard/model_names.py`, shared by the generator and the figures, so a model
cannot be named one way in a figure and another in a table; it also checks the
generated table against `tables/allruns.csv`. Run with `make test`.

The body text points into the appendices (per-run counts; transfer and conditional
figures). If you rebuild the document from pieces, keep those pointers or the
appendices become orphans. Appendix content does not count against the 9-page limit.
