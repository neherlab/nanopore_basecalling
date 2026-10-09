# Changelog

## Unreleased

### Fixed

- **increased `demultiplex` runtime** to 6 hours, to avoid timeout.
- **Re-running a partially completed run no longer re-basecalls it**, which the timestamp in
  `basecalling.log` used to force.

## v1.0 — 2026-08-13

### Overview

Update of the toolchain, configuration and pipeline layout:

- Snakemake 7 → 9, dorado 0.7.0 → 2.1.1
- One workflow instead of two, with methylation as a setting rather than a separate file.
- The settings of a run and its sample table moved next to its data.
- Models and modifications are resolved from dorado's own catalogue and checked before any job is submitted.
- Improvements in the statistics and plots.
- Change in cluster resources requirement (less gpu and shorter default job duration).
- Various bug fixes and improvements.

### Breaking

- **The settings of a run live in the run folder.** `params.tsv` is replaced by `run.yaml`
  (what was sequenced — `kit` and `flow_cell` required, anything else free-form and copied
  into the log) and `samples.tsv` (the barcode → sample table, now a plain table with no
  key/value preamble). `kit` and `flow_cell` are no longer pipeline defaults: an inherited
  kit would quietly basecall a 96-barcode run as a 24-barcode one.
- **`model` is a tier and `modifications` a list.** `model: "sup@v5.2.0"` — the chemistry in
  front of it comes from the flow cell and the kit — and `modifications: "4mC_5mC,6mA"`
  names the modifications to call rather than true/false. `mods_model` is gone. Both old
  spellings stop the run with a message saying what to write instead.
- **The separate methylation workflow is gone.** `snakemake -s methylation.smk …` is the
  `modifications` setting on the one pipeline.
- **Outputs moved** to `final/fastq/` and `final/bam/`, from `final/*.fastq.gz`,
  `final/fastq_files/` and `final/bam_files/`.
- **The statistics tables and plots were renamed.** `lengths.tsv` → `read_summary.tsv`, one
  row per barcode rather than one per read; `quality.tsv` and `quality_std.tsv` →
  `quality_hist.tsv`, counts per Q score; `quality_mean.png` and `quality_std.png` →
  `quality_hist.png` and `low_quality.png`.
- `--config kit=SQK-RBK114-96` replaces `kit96=True`; the barcode count is read off the end
  of the kit name.
- **The conda environment must be re-created**: Python ≥ 3.11 and
  `snakemake-executor-plugin-slurm >= 2.7.0`. The default model also moved from
  `sup@v5.0.0` to `sup@v5.2.0`.

## v0.1 — 2026-08-10

The pipeline as it was before that rewrite: Snakemake 7, dorado 0.7.0, `params.tsv`, and a
separate `methylation.smk`. Tagged so a run made with it can still be reproduced.

What it accumulated, from the loose notes that preceded this changelog:

- 2026-04-27 — cluster QoS `gpu6hours` → `a100-6hours`.
- 2024-09-27 — stayed on dorado 0.7: 0.8 did not work well at the time.
- 2024-09-26 — updated dorado for the basecalling speed improvements in 0.8, and added
  checks for a common mistake in the input path.
- 2024-05-24 — documented methylation basecalling.
