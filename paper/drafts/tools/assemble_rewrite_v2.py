#!/usr/bin/env python3
"""Splice the v2 (restructured) main text into the verbatim Overleaf source.

Kept byte-for-byte from the base: preamble, title block, acknowledgements, bibliography,
appendices, checklist. Appendix B gains the case-study table (the figure is now Figure 1
in the introduction) and a one-sentence pointer.

Usage: python assemble_rewrite_v2.py BASE MAINTEXT OUT
"""
import pathlib, sys
base = pathlib.Path(sys.argv[1]).read_text()
main = pathlib.Path(sys.argv[2]).read_text()
i = base.index("\\begin{abstract}"); j = base.index("\\begin{ack}")
out = base[:i] + main + base[j:]
anchor = "Every number is read from the generated result tables, which one command regenerates and two checkers verify.\n\n\\begin{table}[t]\n\\centering\n\\caption{Breadth across all 19"
assert out.count(anchor) == 1
out = out.replace(anchor, r"""Every number is read from the generated result tables, which one command regenerates and two checkers verify. Table~\ref{tab:case_study} gives the numbers behind Figure~\ref{fig:case_study}.

\begin{table}[t]
\centering
\caption{The first held-out Sokoban rollout in the seed-0 test stream, turn by turn (Claude~Opus~4.7, 2{,}500-token budget); the run plotted in Figure~\ref{fig:case_study}. $\surd$: the interval contains the true remaining spend; $\times$: it misses. ``Spent + upper'' is spend so far plus the guard's upper bound; ``Gate'' is the feasibility score and decision at $\delta{=}0.10$ (abort below 0.02).}
\label{tab:case_study}
\footnotesize
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@{}rrrlllr@{}}
\toprule
Turn & Spent & True rem. & Agent self-report & Guard interval (split-CQR) & Spent + upper & Gate \\
\midrule
1 & 557 & 1{,}090 & [1{,}000, 1{,}800] $\surd$ & [460, 1{,}582] $\surd$ & 2{,}139 $\leq$ 2{,}500 & 0.99 continue \\
2 & 1{,}076 & 571 & [600, 1{,}200] $\times$ & [210, 1{,}102] $\surd$ & 2{,}178 $\leq$ 2{,}500 & 0.95 continue \\
3 & 1{,}380 & 267 & [400, 900] $\times$ & [162, 902] $\surd$ & 2{,}282 $\leq$ 2{,}500 & 0.99 continue \\
\bottomrule
\end{tabular}
\end{table}

\begin{table}[t]
\centering
\caption{Breadth across all 19""")
assert "—" not in out, "em dash in output"
pathlib.Path(sys.argv[3]).write_text(out)
print(f"wrote {sys.argv[3]}")
