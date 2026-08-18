"""Diagnose why a reproduction run differs from the reported numbers.

Run it, paste the output. Every known way to get "different results" is checked
explicitly, in the order they usually happen:

  1. wrong commit (a branch without the reproducibility line)
  2. dirty working tree (locally edited code or tables)
  3. incomplete or wrong-size BAGEN data (partial fetch; run_final then silently
     skips the model-swap and breadth experiments)
  4. running on the host instead of the container (unpinned package versions;
     numbers are only guaranteed inside `make repro`)
  5. stale generated tables (regenerate, then re-check)

Read-only: this script never writes or downloads anything.

Usage: python scripts/repro_doctor.py        (host or container)
"""
from __future__ import annotations

import ast
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OK, BAD, WARN = "ok  ", "FAIL", "warn"
findings: list[tuple[str, str, str]] = []


def note(status: str, what: str, detail: str = "") -> None:
    findings.append((status, what, detail))
    print(f"[{status}] {what}" + (f" — {detail}" if detail else ""))


def run(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT).stdout.strip()
    except OSError:
        return ""


print("=== repro doctor ===\n")

in_container = os.path.exists("/.dockerenv")

# 1. git state ------------------------------------------------------------
commit = run(["git", "rev-parse", "--short", "HEAD"]) or "unknown"
branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"
print(f"commit {commit} on branch {branch}")
# The image excludes Dockerfile/Makefile via .dockerignore, so inside the
# container the image's own existence is the evidence for those two.
sentinels = ["scripts/check_headline_numbers.py", "tables/coverage.csv"] + (
    [] if in_container else ["Dockerfile", "Makefile", "requirements.lock.txt"])
missing_sentinels = [s for s in sentinels if not (ROOT / s).exists()]
if missing_sentinels:
    note(BAD, "this checkout predates the reproducibility line",
         f"missing {', '.join(missing_sentinels)}; check out a recent main commit "
         "(old commits WILL give different numbers)")
else:
    note(OK, "reproducibility files present at this commit")

dirty = [l for l in run(["git", "status", "--porcelain"]).splitlines()
         if l and not l.startswith("??")]
if dirty:
    note(WARN, f"working tree has {len(dirty)} locally modified tracked file(s)",
         "; ".join(l.split()[-1] for l in dirty[:5]))
else:
    note(OK, "working tree clean")

# 2. environment ----------------------------------------------------------
print(f"\nplatform: {platform.platform()} / {platform.machine()}, "
      f"python {platform.python_version()}, "
      f"{'inside container' if in_container else 'HOST (not the container)'}")
if not in_container:
    note(WARN, "running on the host, not the pinned container",
         "reported numbers are only guaranteed by `make repro` (Docker); host runs "
         "use unpinned package versions and multi-threaded kernels")

lock = {}
lock_path = ROOT / "requirements.lock.txt"
if lock_path.exists():
    for line in lock_path.read_text().splitlines():
        if "==" in line and not line.startswith(("#", " ")):
            name, _, ver = line.partition("==")
            lock[name.strip().lower()] = ver.split()[0].strip(" \\")
from importlib import metadata
for pkg in ("numpy", "pandas", "lightgbm", "scikit-learn"):
    try:
        have = metadata.version(pkg)
    except metadata.PackageNotFoundError:
        note(BAD, f"{pkg} not installed in this environment")
        continue
    want = lock.get(pkg)
    if want and have != want:
        note(WARN if not in_container else BAD,
             f"{pkg} {have} != locked {want}",
             "model fits can genuinely differ across versions")
    else:
        note(OK, f"{pkg} {have}" + (f" (matches lock)" if want else ""))

# 3. data completeness ----------------------------------------------------
print()
fetch_src = (ROOT / "scripts" / "fetch_bagen.py").read_text()
tree = ast.parse(fetch_src)
files: list[str] = []
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if getattr(t, "id", None) == "FILES":
                files = ast.literal_eval(node.value)
sizes = {}
manifest = ROOT / "data" / "bagen_hf" / "manifest.jsonl"
if manifest.exists():
    for line in manifest.read_text().splitlines():
        try:
            rec = json.loads(line)
            sizes[rec["path"]] = rec["size_bytes"]
        except (json.JSONDecodeError, KeyError):
            pass

data_root = ROOT / "data" / "bagen_hf"
missing = [f for f in files if not (data_root / f).exists()]
wrong_size = [f for f in files
              if f not in missing and f in sizes
              and (data_root / f).stat().st_size != sizes[f]]
if not files:
    note(WARN, "could not parse FILES from fetch_bagen.py")
elif missing:
    note(BAD, f"BAGEN data incomplete: {len(missing)}/{len(files)} pinned files missing",
         f"e.g. {missing[0]}; run `python scripts/fetch_bagen.py` — run_final SKIPS "
         "the model-swap and 19-run experiments on partial data, so tables will "
         "be missing rows rather than wrong")
elif wrong_size:
    note(BAD, f"{len(wrong_size)} data file(s) have unexpected sizes",
         f"e.g. {wrong_size[0]}; likely a truncated or different-revision download — "
         "re-run `python scripts/fetch_bagen.py`")
else:
    note(OK, f"all {len(files)} pinned BAGEN files present"
         + (" with expected sizes" if sizes else " (no manifest to size-check)"))

# 4. generated tables sanity ---------------------------------------------
print()
expect_rows = {"allruns.csv": 19, "transfer_swebench.csv": 16,
               "transfer_env.csv": 8, "multiresource.csv": 4}
for name, want in expect_rows.items():
    p = ROOT / "tables" / name
    if not p.exists():
        note(BAD, f"tables/{name} missing", "run `make repro`")
        continue
    have = sum(1 for _ in p.open()) - 1
    if have != want:
        note(BAD, f"tables/{name} has {have} rows, expected {want}",
         "regenerated on partial data? re-fetch data, then `make repro`")
    else:
        note(OK, f"tables/{name}: {want} rows")

# 5. the number checks ----------------------------------------------------
print()
for script in ("check_headline_numbers.py", "check_paper_numbers.py"):
    path = ROOT / "scripts" / script
    if not path.exists():
        note(WARN, f"scripts/{script} not present at this commit")
        continue
    r = subprocess.run([sys.executable, str(path)], capture_output=True, text=True)
    tail = (r.stdout.strip().splitlines() or ["(no output)"])[-1]
    note(OK if r.returncode == 0 else BAD, script, tail)

# verdict -----------------------------------------------------------------
fails = [f for f in findings if f[0] == BAD]
warns = [f for f in findings if f[0] == WARN]
print(f"\n=== verdict: {len(fails)} failure(s), {len(warns)} warning(s) ===")
if fails:
    print("Fix the FAIL lines top to bottom; each names its remedy.")
elif warns:
    print("No hard failures. If your numbers still differ, the warnings above "
          "(host run / dirty tree) are the remaining explanations — "
          "run inside the container: make build && make repro && make check-numbers")
else:
    print("This environment should reproduce the reported numbers exactly. "
          "If it does not, capture the command you ran and its output, and diff "
          "your tables/ against git — `git diff tables/` shows exactly which "
          "numbers moved.")
sys.exit(1 if fails else 0)
