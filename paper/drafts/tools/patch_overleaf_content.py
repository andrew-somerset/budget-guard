r"""Agreed 2026-08-26 changes, sized to the ~17-line slack at the end of the main text.

The worked example is a \paragraph at the end of 5.4 (Economic impact), after the
Table-4 paragraph and before "Censored calibration"; nothing after it is an [H]
float, so it consumes the reference slack on page 9 rather than cascading figures.

Usage: python patch_overleaf_content.py BASE OUT --table main|appendix --para tight|short
        [--split] [--keep-discussion] [--gate-in-discussion]
Delivered 2026-08-26 version: --table main --para short --keep-discussion --gate-in-discussion
"""
import pathlib, sys

a = sys.argv[3:]
TABLE_AT = a[a.index("--table") + 1]
PARA = a[a.index("--para") + 1]
SPLIT = "--split" in a
KEEP_DISC = "--keep-discussion" in a
GATE_DISC = "--gate-in-discussion" in a
s = pathlib.Path(sys.argv[1]).read_text()

def once(old, new):
    global s
    n = s.count(old); assert n == 1, f"anchor matched {n} times: {old[:80]!r}"
    s = s.replace(old, new)

TABLE = r"""\begin{table}[%s]
\centering
\caption{The first held-out Sokoban rollout in the seed-0 test stream, turn by turn (Claude~Opus~4.7, 2{,}500-token budget). $\surd$: the interval contains the true remaining spend; $\times$: it misses. ``Spent + upper'' is spend so far plus the guard's upper bound; ``Gate'' is the feasibility score and decision at $\delta{=}0.10$ (abort below 0.02).}
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
"""
tabref = r"Table~\ref{tab:case_study} (Appendix~\ref{app:breadth})" if TABLE_AT == "appendix" else r"Table~\ref{tab:case_study}"
figref = r"Figure~\ref{fig:case_study}" if TABLE_AT == "appendix" else r"Figure~\ref{fig:case_study} (Appendix~\ref{app:breadth})"

# The budget and model are stated in the table caption; repeating them here cost the
# line that kept the [H] table on page 8 at \footnotesize.
LEAD = tabref + r""" follows the first held-out Sokoban rollout in the seed-0 test stream turn by turn; the rollout is fixed by that rule, not chosen by hand."""
REST_TIGHT = r""" The agent's self-reported intervals are 500 to 800 tokens wide and cover only at the first prefix: from turn~2 they sit entirely above the truth, and the last one reserves 400 to 900 tokens for a run that needed 267. The guard's split-CQR intervals are wider but contain the truth at every prefix, and spend so far plus their upper bound stays under the budget at every turn, so the run could be certified to fit from its first turn; the feasibility gate of \S\ref{sec:econ} at $\delta{=}0.10$ scores it 0.95 to 0.99 against an abort threshold of 0.02 and says continue throughout, and the run succeeded inside budget. The example is representative rather than selected: across all 30 test rollouts of this split, split-CQR covers a larger fraction of prefixes than the self-report on 22, ties on 6 and trails on 2 (windowed-CQR: 24, 5 and 1), consistent with Figure~\ref{fig:coverage}. """ + figref + r""" plots the rollout."""
REST_SHORT = r""" The agent's self-reported intervals cover only the first prefix: from turn~2 they sit entirely above the truth, and the last one reserves 400 to 900 tokens for a run that needed 267. The guard's split-CQR intervals are wider but contain the truth at every turn, spend so far plus their upper bound stays under the budget throughout, and the $\delta{=}0.10$ gate of \S\ref{sec:econ} scores the run 0.95 to 0.99 against an abort threshold of 0.02, so a deployer could have certified it from turn~1; it succeeded inside budget. The example is representative: over all 30 test rollouts of this split, split-CQR covers more prefixes than the self-report on 22, ties on 6 and trails on 2 (windowed-CQR: 24, 5 and 1). """ + figref + r""" plots the rollout."""
rest = REST_TIGHT if PARA == "tight" else REST_SHORT

if TABLE_AT == "main":
    body = ("\\paragraph{A worked example.}\n" + LEAD + "\n\n" + TABLE % "H" + "\n" + rest.lstrip() + "\n") if SPLIT \
           else ("\\paragraph{A worked example.}\n" + LEAD + rest + "\n\n" + TABLE % "H")
else:
    body = "\\paragraph{A worked example.}\n" + LEAD + rest + "\n"

once("not as proof that the true rate is zero.\n\n\\subsection{Censored calibration}",
     "not as proof that the true rate is zero.\n\n" + body + "\n\\subsection{Censored calibration}")

if KEEP_DISC:
    once("they assume adding the guard would not change agent behaviour and that the sample is representative.\n\n\\paragraph{Broader impact.}",
         "they assume adding the guard would not change agent behaviour and that the sample is representative. The worked example in \\S\\ref{sec:econ} also shows what the guard does not do: its intervals are roughly twice as wide as the agent's, and the price of a calibrated answer is a less precise one. Where a deployer only needs a yes-or-no on whether the run still fits, that width costs nothing; where a tight point estimate matters, the interval is a bound, not a forecast."
         + (" On the split behind that example, the gate aborts none of the 16 feasible test runs and recovers 4.9\\% of doomed-run spend; Table~\\ref{tab:abort} gives the five-seed means." if GATE_DISC else "")
         + "\n\n\\paragraph{Broader impact.}")

FIG = r"""\begin{figure}[t]
\centering
\includegraphics[width=0.72\linewidth]{figures/fig_case_study.png}
\caption{The Sokoban rollout of Table~\ref{tab:case_study}. Grey bars are the agent's self-reported remaining-token interval at each turn, green bars the guard's split-CQR interval, black dots the true remaining spend, and the dashed red line the budget still available. The self-report drifts above the truth after turn~1; the guard's interval tracks it and stays under the remaining budget throughout, and the gate (scores under each turn) says continue at every step.}
\label{fig:case_study}
\end{figure}
"""
lead_sentence = (r"Table~\ref{tab:case_study} and Figure~\ref{fig:case_study} give the worked example of \S\ref{sec:econ}."
                 if TABLE_AT == "appendix" else r"Figure~\ref{fig:case_study} plots the worked example of \S\ref{sec:econ}.")
once("Every number is read from the generated result tables, which one command regenerates and two checkers verify.\n\n\\begin{table}[t]\n\\centering\n\\caption{Breadth across all 19",
     "Every number is read from the generated result tables, which one command regenerates and two checkers verify. " + lead_sentence + "\n\n"
     + ((TABLE % "t") + "\n" if TABLE_AT == "appendix" else "") + FIG + "\n\\begin{table}[t]\n\\centering\n\\caption{Breadth across all 19")

assert "—" not in s
pathlib.Path(sys.argv[2]).write_text(s)
