# Paper artifacts: how to build Appendices B and C

The submission has three appendices. They are not the same kind of thing, and that
difference decides how you edit them.

| Appendix | Contents | Where it comes from |
|---|---|---|
| A. Method glossary | Twelve plain-English definitions (coverage, q̂, α, width, split conformal, CQR, Mondrian, ACI, DtACI, windowed-CQR, joint coverage, censoring) | Prose. Lives in the document only. Edit it there. |
| B. Per-run dataset composition | Table 3: rollouts and prefix samples for every model x environment run | **Generated** from `tables/allruns.csv` and `tables/transfer_warehouse.csv` |
| C. Supporting figures | Figure 6 (model-swap transfer) and Figure 7 (conditional coverage), with captions | **Generated** captions; images come from `figures/` |

Appendix B originally sat in section 4 (Experimental Setup) as Table 3. Appendix C's
two figures came out of section 5 (Results), where they were Figures 4 and 5 before
the page-limit cut renumbered them.

## Build them

```bash
make appendices        # or: python3 scripts/make_appendices.py
```

This writes `paper/appendices.md`, which is paste-ready: no metadata, no instructions,
nothing to strip. Appendix B arrives as a markdown table. Appendix C arrives as two
captions, each followed by a line like `[insert image: figures/...]` naming the image
file to place at that point.

## Do not retype the numbers

Every value in Appendix B is read from the generated tables, which `make repro-all`
produces and two checkers verify (11 headline claims and 35 paper claims). Hand-copying
numbers into the document is how this paper previously ended up quoting figures that no
longer matched the data. If a number looks wrong, fix the experiment or the table and
rerun `make appendices`; do not edit the document by hand.

The generator is also the guard against silent breakage. It exits non-zero and explains
itself if:

- a source table or figure is missing (run `make repro-all`)
- there are not exactly 19 model x environment runs, which is what a partial BAGEN
  download looks like (run `make doctor` to confirm, then `python scripts/fetch_bagen.py`)
- a figure is older than the table it is drawn from, meaning the image predates the
  numbers it shows (rerun `make repro-all`)

A zero exit with "all sources present and current" means the appendices match the
verified data.

## Keep the cross-references

The body text points into both appendices:

- Section 4, Models: "the per-run counts are in Table 3, Appendix B"
- Section 5.2: "(Figure 6, Appendix C)"
- Section 5.3: "(Figure 7, Appendix C)"

If you rebuild the document from pieces, keep those pointers or the appendices become
orphans. Appendix content does not count against the 9-page limit, which is why this
material lives here.
