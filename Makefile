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

.PHONY: help lock build test fetch repro repro-all repro-paper doctor clean shell digest check-numbers outdirs

help:
	@echo "make lock    regenerate requirements.lock.txt (needs uv, runs on host)"
	@echo "make build   build the pinned image"
	@echo "make test    run the full test suite inside the container"
	@echo "make fetch   download the revision-pinned BAGEN subset into ./data"
	@echo "make repro   regenerate the headline figures/ and tables/ inside the container"
	@echo "make repro-paper  regenerate + verify EVERYTHING the paper uses (tables, figures, both checkers)"
	@echo "make repro-all  THE RUN-ALL BUTTON: every figure and table in the repo, then both checkers (slow)"
	@echo "make check-numbers  verify the paper's headline numbers against tables/"
	@echo "make doctor  diagnose why a reproduction run differs (git/data/env/tables)"
	@echo "make clean   delete generated figures/ and tables/ so the next run starts fresh"
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
# Immediately re-checks the regenerated tables against the paper's headline numbers,
# so a run that moves one cannot pass unnoticed.
repro: build outdirs
	docker run --rm --platform=linux/amd64 $(MOUNTS) $(IMAGE) python -m budget_guard.run_final
	$(MAKE) check-numbers

# Everything `repro` covers, plus every remaining reported table (external-budget
# transfer, censored rungs, conditional coverage, per-env economics, diagnostics)
# and all three script-drawn figures, then both checkers. The run-all button.
repro-all: build outdirs
	docker run --rm --platform=linux/amd64 $(MOUNTS) $(IMAGE) sh -c "\
		python -m budget_guard.run_final --full && \
		python scripts/make_pipeline_figure.py && \
		python scripts/make_costofpass_figure.py && \
		python scripts/run_closed_loop.py && \
		python scripts/check_headline_numbers.py && \
		python scripts/check_paper_numbers.py"

# THE PAPER SET: regenerate every table and every figure the submission embeds —
# the headline set, the three remaining paper tables (Warehouse model swap,
# censored calibration, conditional coverage), and the two script-drawn figures
# (pipeline diagram, cost-of-pass frontier) — then verify all 11 headline claims
# and all 35 paper claims. repro-all additionally covers appendix diagnostics.
repro-paper: build outdirs
	docker run --rm --platform=linux/amd64 $(MOUNTS) $(IMAGE) sh -c "\
		python -m budget_guard.run_final && \
		python -m budget_guard.run_transfer_warehouse && \
		python -m budget_guard.run_censored && \
		python -m budget_guard.run_conditional && \
		python scripts/make_pipeline_figure.py && \
		python scripts/make_costofpass_figure.py && \
		python scripts/check_headline_numbers.py && \
		python scripts/check_paper_numbers.py"

# Verifies headline numbers quoted in notes/ against the generated tables. Runs on the
# host (it only reads CSVs) so it works without Docker.
check-numbers:
	@test -n "$(PYTHON)" || { echo "No python found on PATH. Activate your env, or: make check-numbers PYTHON=/path/to/python"; exit 1; }
	$(PYTHON) scripts/check_headline_numbers.py

# Removes generated outputs. Figures are wholly regenerable; tables are tracked in git,
# so this deletes them from the working tree and `git checkout tables/` restores the
# committed copies. Use before a full run to guarantee no output is a stale leftover:
# three drivers write only to figures/final/, so an old top-level copy of those figures
# would otherwise survive a regeneration and sit next to the fresh ones.
clean:
	rm -rf "$(CURDIR)/figures"
	rm -f "$(CURDIR)"/tables/*.csv "$(CURDIR)"/tables/*.fingerprint.json
	@echo "cleaned figures/ and tables/ — 'git checkout tables/' restores committed tables"

# Diagnoses reproduction differences in THIS environment (host or container) —
# run it wherever you ran the experiments that gave unexpected numbers.
doctor:
	@test -n "$(PYTHON)" || { echo "No python found on PATH. Activate your env, or: make doctor PYTHON=/path/to/python"; exit 1; }
	$(PYTHON) scripts/repro_doctor.py

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
