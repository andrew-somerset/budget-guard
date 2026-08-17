# syntax=docker/dockerfile:1
# check=skip=FromPlatformFlagConstDisallowed
#
# (The lint above objects to hardcoding --platform in FROM, because it normally defeats
# multi-arch builds. Here that is the point: this image must be one fixed architecture
# forever, even if someone forgets the --platform flag on the command line.)
#
# Reproducibility image for budget-guard.
#
# Purpose: freeze the *environment* (OS, CPU architecture, compiled binaries, package
# versions) so that a reported number can be regenerated identically on any machine.
# Fixed seeds already freeze the program's random choices; this freezes everything else.
#
# Build:  make build
# Test:   make test
# Repro:  make repro          (regenerates figures/ and tables/ from mounted data/)
#
# ---------------------------------------------------------------------------------
# Base image is pinned BY DIGEST, not by tag. The tag `python:3.12-slim-bookworm`
# is mutable — upstream republishes it with security patches, so building from the
# tag in six months would give a different OS. The digest below can only ever refer
# to one exact image. (Same discipline as the pinned BAGEN REVISION in
# scripts/fetch_bagen.py.) Resolved 2026-08-01.
#
# To deliberately update it:
#   TOKEN=$(curl -s "https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/python:pull" | python -c "import sys,json;print(json.load(sys.stdin)['token'])")
#   curl -sI -H "Authorization: Bearer $TOKEN" \
#     -H "Accept: application/vnd.oci.image.index.v1+json" \
#     https://registry-1.docker.io/v2/library/python/manifests/3.12-slim-bookworm \
#     | grep -i docker-content-digest
# ...then re-run the full suite and record any numeric drift in notes/robustness_progress.md.
#
# --platform=linux/amd64 makes x86-64 Linux the single reference architecture. Without
# it, an Apple Silicon machine builds an arm64 image and gets different compiled numpy /
# LightGBM binaries than a CI runner — the exact drift this image exists to eliminate.
# On Apple Silicon this runs under emulation (slower, but identical).
FROM --platform=linux/amd64 python:3.12-slim-bookworm@sha256:d50fb7611f86d04a3b0471b46d7557818d88983fc3136726336b2a4c657aa30b

# libgomp1 = the OpenMP runtime LightGBM links against. Absent from -slim images; without
# it `import lightgbm` fails. (This is the Linux counterpart of the libomp install needed
# on macOS.)
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Determinism controls.
#   OMP_NUM_THREADS=1 et al. force single-threaded numeric kernels. Floating-point
#   addition is not associative, so a parallel reduction combines partial sums in an
#   order that depends on the thread count: an 8-core laptop and a 4-core CI runner can
#   produce slightly different models from identical code, data, and seeds. Pinning to
#   one thread fixes the summation order. It costs wall-clock time; that is the intended
#   trade for a reproducibility image.
#   PYTHONHASHSEED=0 fixes string hash randomization, so any set/dict iteration order
#   that leaks into results is stable across runs.
#   BAGEN_DIR points at the mount for the BAGEN repo, which lives outside this repo (see
#   the Makefile). Setting it explicitly beats relying on the /app/../BAGEN relative path.
ENV BAGEN_DIR=/BAGEN \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1

WORKDIR /app

# Dependencies first, as their own layer: Docker caches each step, so editing research
# code below does not trigger a full reinstall on rebuild.
#
# --require-hashes makes pip refuse to install any package whose bytes do not match the
# recorded hash, and refuse to install anything not listed at all. That is what turns
# requirements.lock.txt from documentation into an enforced guarantee.
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements.lock.txt

COPY pyproject.toml README.md ./
COPY budget_guard ./budget_guard
COPY scripts ./scripts
COPY examples ./examples
COPY tests ./tests

# --no-deps: install the package itself only. Its pyproject dependencies are floors
#   (numpy>=1.24), so resolving them here could pull versions outside the lockfile and
#   silently unpin the environment.
# --no-build-isolation: use the setuptools/wheel already installed from the lockfile
#   rather than letting pip download an unpinned build backend at build time.
RUN pip install --no-cache-dir --no-deps --no-build-isolation -e .

# data/, figures/ and tables/ are deliberately NOT baked into the image. BAGEN carries its
# own licence terms (redistributing it inside a published image would be republishing
# someone else's dataset), it is ~105 MB, and scripts/fetch_bagen.py already pins its
# revision — freezing it twice adds nothing. They are bind-mounted at run time instead;
# see the Makefile.
VOLUME ["/app/data", "/app/figures", "/app/tables"]

# Default: prove the environment works. Override with any command, e.g.
#   docker run --rm budget-guard python -m budget_guard.run_coverage
CMD ["python", "-m", "pytest", "-q"]
