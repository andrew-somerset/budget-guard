# budget-guard — reproducibility entry points.
#
# Everything here runs inside the pinned container, so results do not depend on which
# machine you are sitting at. Requires Docker Desktop (or any Docker daemon) running.

IMAGE := budget-guard

# Package-index cutoff for dependency resolution. Makes `make lock` a pure function of
# requirements-repro.in rather than of "whatever PyPI happens to hold today", so CI can
# verify the committed lockfile without false alarms. Bump deliberately when upgrading.
EXCLUDE_NEWER := 2026-08-01T00:00:00Z

# $(CURDIR) is the directory of this Makefile — unlike $(PWD) it does not depend on
# where you invoked make from. A wrong host path here does not error: Docker silently
# creates an empty directory and mounts that, which shows up as tests skipping rather
# than failing. Worth knowing, because it is a quiet failure mode.
#
# Inputs are mounted read-only so a run cannot mutate the data it was calibrated on.
# BAGEN lives OUTSIDE the repo, so the sibling checkout is mounted at /BAGEN (matching
# BAGEN_DIR in the Dockerfile). This is an optimization, not a requirement: since
# 2026-08-01 the smoke fixture is also vendored at tests/fixtures/, so the suite passes
# without it — see budget_guard/extract.py::_default_smoke_path for the resolution order.
IN     := -v "$(CURDIR)/data:/app/data:ro" -v "$(CURDIR)/../BAGEN:/BAGEN:ro"
OUT    := -v "$(CURDIR)/figures:/app/figures" -v "$(CURDIR)/tables:/app/tables"
MOUNTS := $(IN) $(OUT)

# fetch must write into data/, so it gets a writable mount instead of the read-only one.
MOUNTS_FETCH := -v "$(CURDIR)/data:/app/data"

.PHONY: help lock build test fetch repro repro-all shell digest check-numbers

help:
	@echo "make lock    regenerate requirements.lock.txt (needs uv, runs on host)"
	@echo "make build   build the pinned image"
	@echo "make test    run the full test suite inside the container"
	@echo "make fetch   download the revision-pinned BAGEN subset into ./data"
	@echo "make repro   regenerate all figures/ and tables/ inside the container"
	@echo "make repro-all  ...plus every remaining reported table (slow)"
	@echo "make check-numbers  verify notes/ headline numbers against tables/"
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

test: build
	docker run --rm --platform=linux/amd64 $(MOUNTS) $(IMAGE) python -m pytest -q

fetch: build
	docker run --rm --platform=linux/amd64 $(MOUNTS_FETCH) $(IMAGE) python scripts/fetch_bagen.py

# The canonical regeneration path: same container, same seeds, same data revision.
# Immediately re-checks the regenerated tables against the numbers quoted in notes/, so a
# run that moves a headline number cannot pass unnoticed.
repro: build
	docker run --rm --platform=linux/amd64 $(MOUNTS) $(IMAGE) python -m budget_guard.run_final
	$(MAKE) check-numbers

# Everything `repro` covers, plus every remaining reported table (external-budget
# transfer, censored rungs, conditional coverage, per-env economics, the loop layer).
# Substantially slower — the loop stress sweep is 4 windows x 10 order seeds.
repro-all: build
	docker run --rm --platform=linux/amd64 $(MOUNTS) $(IMAGE) python -m budget_guard.run_final --full
	$(MAKE) check-numbers

# Verifies headline numbers quoted in notes/ against the generated tables. Runs on the
# host (it only reads CSVs) so it works without Docker.
check-numbers:
	python scripts/check_headline_numbers.py

shell: build
	docker run --rm -it --platform=linux/amd64 $(MOUNTS) $(IMAGE) bash

# Shows what the mutable tag currently points at, for comparison against the digest
# pinned in the Dockerfile. A difference means upstream republished the tag — expected,
# and precisely why the Dockerfile pins the digest instead.
digest:
	@TOKEN=$$(curl -s "https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/python:pull" \
		| python -c "import sys,json;print(json.load(sys.stdin)['token'])"); \
	curl -sI -H "Authorization: Bearer $$TOKEN" \
		-H "Accept: application/vnd.oci.image.index.v1+json" \
		https://registry-1.docker.io/v2/library/python/manifests/3.12-slim-bookworm \
		| grep -i docker-content-digest
