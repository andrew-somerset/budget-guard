#!/usr/bin/env python3
"""Every model-environment run on one figure, no averaging: a dot per run and method.

Reads tables/allruns.csv (the data behind the appendix breadth table: one split per
run, seed 0) and draws, per environment, one row per model with a marker for the agent
self-report and for split-CQR, windowed-CQR and DtACI coverage, against the 0.90
target and the 0.85 line the paper's breadth claim uses. Nothing is aggregated, so the
figure shows exactly what the table shows, including the runs below target.

Writes paper/figures/fig_allruns.png at an aspect ratio that keeps it about 1.6 in tall
at NeurIPS line width.
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

ENV_TITLE = {"sokoban": "Sokoban", "searchr1": "Search-R1", "swebench": "SWE-bench"}
def display(model: str) -> str:
    m = model.lower()
    if "opus-4.7" in m or "opus4.7" in m: return "Claude Opus 4.7"
    if "opus-4-6" in m or "opus-4.6" in m: return "Claude Opus 4.6"
    if "sonnet" in m: return "Claude Sonnet 4.6"
    if "codex" in m: return "GPT-5.2-Codex"
    if "gpt5.2" in m or "gpt-5.2" in m: return "GPT-5.2-instant"
    if "gemini" in m: return "Gemini 3.1 Pro"
    if "qwen" in m: return "Qwen3-235B"
    return model
SERIES = [("agent", "agent self-report", "#8B93A1", "o"), ("split-CQR", "split-CQR", "#1baf7a", "s"),
          ("windowed-CQR", "windowed-CQR", "#4a3aa7", "D"), ("DtACI", "DtACI", "#008300", "^")]
ORDER = ["Claude Opus 4.7", "Claude Opus 4.6", "Claude Sonnet 4.6", "GPT-5.2-instant", "GPT-5.2-Codex", "Gemini 3.1 Pro", "Qwen3-235B"]

def draw(height, out="paper/figures/fig_allruns.png"):
    df = pd.read_csv("tables/allruns.csv"); df["name"] = df["model"].map(display)
    envs = ["sokoban", "searchr1", "swebench"]
    fig, axes = plt.subplots(1, 3, figsize=(13.5, height), constrained_layout=True,
                             gridspec_kw={"width_ratios": [7, 7, 5]})
    for ax, env in zip(axes, envs):
        sub = df[df.env == env].set_index("name").reindex([m for m in ORDER if m in set(df[df.env == env]["name"])])
        y = np.arange(len(sub))[::-1]
        ax.axvline(0.90, color="#4A5361", lw=1.2, ls="--", label="nominal 0.90", zorder=1)
        ax.axvline(0.85, color="#4A5361", lw=0.8, ls=":", label="0.85 (breadth claim)", zorder=1)
        for col, label, color, marker in SERIES:
            vals = sub[col].to_numpy(dtype=float)
            ax.scatter(vals, y, s=34, color=color, marker=marker, label=label, zorder=3, edgecolor="white", linewidth=0.5)
        ax.set_yticks(y, sub.index, fontsize=8)
        ax.set_xlim(0, 1.03); ax.set_xlabel("marginal coverage (one split per run)", fontsize=8)
        ax.set_title(ENV_TITLE[env], fontsize=10); ax.grid(axis="x", alpha=0.25); ax.set_axisbelow(True)
        ax.tick_params(axis="x", labelsize=8)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=8.5, ncol=6, loc="lower center", bbox_to_anchor=(0.5, -0.09))
    fig.savefig(out, dpi=200, bbox_inches="tight"); plt.close(fig)
    w, h = Image.open(out).size; return w / h

if __name__ == "__main__":
    os.makedirs("paper/figures", exist_ok=True)
    target, h = 3.3, 4.2
    for _ in range(6):
        a = draw(h)
        if abs(a - target) < 0.05: break
        h *= a / target
    print(f"wrote paper/figures/fig_allruns.png (aspect {a:.2f}, ~{5.5/a:.2f} in tall at line width)")
    df = pd.read_csv("tables/allruns.csv")
    print("runs:", len(df), "| windowed-CQR >= 0.85:", int((df['windowed-CQR'] >= 0.85).sum()), "| agent self-report available:", int(df['agent'].notna().sum()))
