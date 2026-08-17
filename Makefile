# budget-guard — reproducibility entry points.
#
# Everything here runs inside the pinned container, so results do not depend on which
# machine you are sitting at. Requires Docker Desktop (or any Docker daemon) running.

IMAGE := budget-guard

# Package-index cutoff for dependency resolution. Makes `make lock` a pure function of
# requirements-repro.in rather than of "whatever PyPI happens to hold today", so CI can
# verify the committed lockfile without false alarms. Bump deliberately when upgrading.
EXCLUDE_NEWER := 2026-08-01T00:00:00Z

# Paths below use $(CURDIR), the directory of this Makefile — unlike $(PWD) it does not
# depend on where you invoked make from.
#
# Host interpreter for the targets that do NOT run in the container. Neither literal
# works on its own: bare `python` is absent from a clean macOS/Debian PATH, while `python3`
# can resolve to a system interpreter that lacks this project's dependencies even when a
# conda env or venv is active. So prefer `python` when it exists — that IS the active
# environment — and fall back to `python3`. Override explicitly if needed:
#   make check-numbers PYTHON=/path/to/python
PYTHON ?= $(shell command -v python 2>/dev/null || command -v python3 2>/dev/null)

# Mounts are CONDITIONAL on the host path existing. Docker does not error on a missing
# bind-mount source: it silently creates an empty directory and mounts that. For a fresh
# clone with no ../BAGEN, an unconditional mount therefore litters an empty BAGEN/ folder
# in the parent of the user's repo — outside the project entirely — and the only symptom
# is a test quietly skipping. $(wildcard) makes the mount vanish instead.
#
# Inputs are read-only so a run cannot mutate the data it was calibrated on. BAGEN lives
# outside the repo and is mounted at /BAGEN (matching BAGEN_DIR in the Dockerfile), but
# it is an optimization, not a requirement: the smoke fixture is vendored at
# tests/fixtures/, so the suite passes without it. See extract.py::_default_smoke_path.
BAGEN_HOST := $(abspath $(CURDIR)/../BAGEN)
IN     := $(if $(wildcard $(CURDIR)/data),-v "$(CURDIR)/data:/app/data:ro",) \
          $(if $(wildcard $(BAGEN_HOST)),-v "$(BAGEN_HOST):/BAGEN:ro",)
OUT    := -v "$(CURDIR)/figures:/app/figures" -v "$(CURDIR)/tables:/app/tables"
MOUNTS := $(IN) $(OUT)

# fetch must write into data/, so it gets a writable mount instead of the read-only one.
MOUNTS_FETCH := -v "$(CURDIR)/data:/app/data"

# Output dirs are created by us, not by Docker. A daemon-created bind-mount source is
# owned by root on Linux, which then makes the directory unwritable from the host.
outdirs:
	@mkdir -p "$(CURDIR)/figures" "$(CURDIR)/tables"

.PHONY: help lock build test fetch repro repro-all shell digest check-numbers outdirs

help:
	@echo "make lock    regenerate requirements.lock.txt (needs uv, runs on host)"
	@echo "make build   build the pinned image"
	@echo "make test    run the full test suite inside the container"
	@echo "make fetch   download the revision-pinned BAGEN subset into ./data"
	@echo "make repro   regenerate all figures/ and tables/ inside the container"
	@echo "make repro-all  ...plus every remaining reported table (slow)"
	@echo "make check-numbers  verify headline numbers against tables/"
	@echo "make shell   interactive shell inside the container"
	@echo "make digest  print the current upstream digest of the base image tag"

# Regenerates the full transitive dependency tree with hashes, resolved for the
# CONTAINER's platform (linux/amd64), not the host's. Run this only when deliberately
# changing dependencies — then rebuild, re-run the suite, and record any numeric drift.
lock:
	uv pip compile requirements-repro.in \
		--python-version 3.12 \
		--python-platform x86_64-unknown-linux-gnu \
		--exclude-newer $(EXCLUDE_NEWER) \
		--generate-hashes -o requirements.lock.txt

build:
	docker build --platform=linux/amd64 -t $(IMAGE) .

test: build outdirs
	docker run --rm --platform=linux/amd64 $(MOUNTS) $(IMAGE) python -m pytest -q

fetch: build
	@mkdir -p "$(CURDIR)/data"
	docker run --rm --platform=linux/amd64 $(MOUNTS_FETCH) $(IMAGE) python scripts/fetch_bagen.py

# The canonical regeneration path: same container, same seeds, same data revision.
# Immediately re-checks the regenerated tables against the headline numbers, so a
# run that moves a headline number cannot pass unnoticed.
repro: build outdirs
	docker run --rm --platform=linux/amd64 $(MOUNTS) $(IMAGE) python -m budget_guard.run_final
	$(MAKE) check-numbers

# Everything `repro` covers, plus every remaining reported table (external-budget
# transfer, censored rungs, conditional coverage, per-env economics, the loop layer).
# Substantially slower — the loop stress sweep is 4 windows x 10 order seeds.
repro-all: build outdirs
	docker run --rm --platform=linux/amd64 $(MOUNTS) $(IMAGE) python -m budget_guard.run_final --full
	$(MAKE) check-numbers

# Verifies headline numbers against the generated tables. Runs on the
# host (it only reads CSVs) so it works without Docker.
check-numbers:
	@test -n "$(PYTHON)" || { echo "No python found on PATH. Activate your env, or: make check-numbers PYTHON=/path/to/python"; exit 1; }
	$(PYTHON) scripts/check_headline_numbers.py

shell: build outdirs
	docker run --rm -it --platform=linux/amd64 $(MOUNTS) $(IMAGE) bash

# Shows what the mutable tag currently points at, for comparison against the digest
# pinned in the Dockerfile. A difference means upstream republished the tag — expected,
# and precisely why the Dockerfile pins the digest instead.
digest:
	@TOKEN=$$(curl -s "https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/python:pull" \
		| $(PYTHON) -c "import sys,json;print(json.load(sys.stdin)['token'])"); \
	curl -sI -H "Authorization: Bearer $$TOKEN" \
		-H "Accept: application/vnd.oci.image.index.v1+json" \
		https://registry-1.docker.io/v2/library/python/manifests/3.12-slim-bookworm \
		| grep -i docker-content-digest
