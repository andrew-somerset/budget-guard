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
