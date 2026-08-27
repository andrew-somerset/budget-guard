Reproduce `2026-08-26_overleaf_main.tex` from the verbatim Overleaf source:

    python patch_overleaf_content.py ../2026-08-26_overleaf_main_base.tex ../2026-08-26_overleaf_main.tex \
        --table main --para short --keep-discussion --gate-in-discussion

The script anchors on exact strings and aborts if an anchor does not match exactly once.
No layout or spacing settings are changed. Figures: `scripts/make_paper_figures.py`
regenerates fig_coverage.png / fig_transfer.png at the team's original aspect ratios
(a taller figure pushes an [H] float to the next page and cascades the layout).
Compile check: `tectonic -X compile main.tex` beside the sty and figures; main text
fills page 9 and References start on page 10.

Rewrite (2026-08-26, narrative restructure, all numbers unchanged):

    python assemble_rewrite_v2.py ../2026-08-26_overleaf_main_base.tex ../2026-08-26_rewrite_v2_maintext.tex ../2026-08-26_rewrite_v2_main.tex

`2026-08-26_rewrite_v2_maintext.tex` is the hand-written main text (abstract through
conclusion); the assembler keeps everything else from the base byte-for-byte and adds
the worked-example table to Appendix B. Bundle: `BudgetGuard_Overleaf_REWRITE_2026-08-26.zip`.

Review candidate (2026-08-27, sentence-level corrections and flow edits, no number moved):

    cp ../2026-08-26_rewrite_v2_main.tex ../2026-08-27_rewrite_v3_candidate.tex
    python3 apply_rewrite_v3_edits.py ../2026-08-27_rewrite_v3_candidate.tex

Each edit is one exact-anchor replacement keyed by the IDs in
`../2026-08-27_rewrite_review.md`; delete an entry to reject that edit. Compile check:
24 pages, conclusion on page 9 (F4 pays for F1–F3), zero overfull boxes.

v4 (2026-08-27): `2026-08-27_rewrite_v4_main.tex` = v3 plus the abstract restorations in
audit-log entry 10 and a `\newpage` after the conclusion; diff in `2026-08-27_rewrite_v4.diff`.
