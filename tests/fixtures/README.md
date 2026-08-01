# Test fixtures

## `bagen_smoke_sokoban_dialogues.json`

A 2.3 KB verbatim copy of `_smoke/sokoban_dialogues.json` from the BAGEN repository
(one sokoban rollout, three turns). Vendored here so a fresh clone can run the full test
suite without a separate BAGEN checkout — previously `tests/test_extract.py` resolved
`<repo>/../BAGEN/_smoke/`, so the extractor invariant tests silently skipped anywhere
BAGEN was not a sibling directory, including inside the reproducibility container.

**Source:** BAGEN (RAGEN Team), arXiv:2606.00198.
**Licence:** MIT, Copyright 2025 RAGEN Team — redistribution is permitted provided the
copyright and permission notice travel with the copy, which is the purpose of this note.

Resolution order is defined in `budget_guard/extract.py::_default_smoke_path`:

1. `$BAGEN_DIR/_smoke/sokoban_dialogues.json` if `BAGEN_DIR` is set
2. `<repo>/../BAGEN/_smoke/sokoban_dialogues.json` (sibling checkout)
3. this vendored copy

So a real BAGEN checkout always wins; this is the fallback that makes the repo
self-contained. If BAGEN's smoke sample ever changes upstream, refresh this file rather
than letting the two drift.
