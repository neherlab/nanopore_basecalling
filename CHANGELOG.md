# Changelog

Notable changes to the pipeline. Newest first. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); dates before v1.0 are the loose
notes that preceded it.

## v1.0 — 2026-08-11

The toolchain, the configuration and the layout rewritten. With an existing checkout,
re-create the conda environment and read the breaking changes first.

### Breaking

- **The settings of a run live in the run folder.** `params.tsv` is replaced by `run.yaml`
  (what was sequenced — `kit` and `flow_cell` required, anything else free-form and copied
  into the log) and `samples.tsv` (the barcode → sample table, now a plain table with no
  key/value preamble). `kit` and `flow_cell` are no longer pipeline defaults: an inherited
  kit would quietly basecall a 96-barcode run as a 24-barcode one.
- **`model` is a tier and `modifications` a list.** `model: "sup@v5.2.0"` — the chemistry in
  front of it comes from the flow cell and the kit. `mods_model` is gone, and
  `modifications` now names the modifications to call rather than true/false:
  `modifications: "4mC_5mC,6mA"`. Both old spellings stop the run with a message saying
  what to write instead.
- **The separate methylation workflow is gone.** `snakemake -s methylation.smk …` is the
  `modifications` setting on the one pipeline.
- **Outputs moved** to `final/fastq/` and `final/bam/`, from `final/*.fastq.gz`,
  `final/fastq_files/` and `final/bam_files/`.
- `--config kit=SQK-RBK114-96` replaces `kit96=True`; the barcode count is read off the end
  of the kit name.
- Snakemake 7 → **9**, dorado 0.7.0 → **2.1.1**, default model `sup@v5.0.0` → `sup@v5.2.0`.
  The environment must be re-created: Python ≥ 3.11 and
  `snakemake-executor-plugin-slurm >= 2.7.0`.

### Added

- **Several modifications in one run** — `modifications: "4mC_5mC,6mA"` — called in a single
  pass and written into the same bam.
- **Models and modifications are checked before any job is submitted**, against dorado's own
  catalogue: an unknown modification, one the chosen model does not ship, and a pair dorado
  could not call together (it allows only one per canonical base) all fail in a second
  rather than an hour into a GPU job.
- Settings are read in three layers, each overriding the last: `config/config.yaml` →
  `<run folder>/run.yaml` → `--config key=value`. The run's log file records the merged
  result wholesale, plus the model names it resolved to, so nothing in it can go stale.
- `download_model`: models are fetched on first use, on the login node — the compute nodes
  have no internet.
- Per-step logs in `<run folder>/log/`, kept after the run so a failure can be investigated.
- A CPU and memory efficiency report per cluster run, in `efficiency_reports/`.
- `docs/`: setting up, running a run, and choosing a model and the modifications.

### Changed

- One workflow instead of two. The rules are split into `rules/basecalling.smk` and
  `rules/statistics.smk`, and `snakecommands.py` into one `argparse` script per step under
  `scripts/`. The `click` dependency is gone.
- The cluster profile moved to the SLURM executor plugin (`cluster/config.v8+.yaml`);
  `cluster/cluster_config.json` and `cluster/slurm_submit.sh` are gone.
- Demultiplexing always produces bam, which is then converted to FASTQ. With modifications
  the bam files are kept in `final/bam`, since FASTQ cannot carry the `MM`/`ML` tags.
- The statistics plots are horizontal — barcodes on the y-axis, one colour, and whiskers at
  the 1st and 99th percentiles. A 96-barcode kit now grows taller instead of more crowded,
  and every barcode stays legible.
- **Read quality is reported per base rather than per read.** `quality_mean.png` and
  `quality_std.png` are replaced by `quality_hist.png`, the Q-score distribution of each
  barcode, and `low_quality.png`, the percentage of bases below Q20. The old figures
  averaged Phred scores per read, which overstated accuracy by about 19 Q points — Q43.6
  where the true read accuracy was Q24.8 — and hid a distribution that has half its mass on
  dorado's Q50 cap and so has no meaningful average. `statistics/quality.tsv` and
  `quality_std.tsv` become `statistics/quality_hist.tsv`, counts per Q score, which is also
  a few kB instead of a few MB.
- **Each barcode now reports two Q scores**, marked on its distribution: the mean of the Q
  scores, and `-10 log10(avg error rate)`, which converts each score back to an error
  probability before averaging. The second is the one that says how often the barcode is
  actually wrong; on the test run they read 43.4 and 22.4.
- **The figures leave out barcodes the run did not use**, with a note saying how many. A
  96-barcode kit carrying three samples was 94 blank rows. The threshold is a thousand
  bases, so it also covers cross-talk barcodes that caught a single read. The tables still
  carry every barcode.
- `docs/plots.md`: what each figure shows and what the reported quantities mean.
- `biopython` is no longer a dependency: the stats step reads the fastq directly.
- `basecall` requests 16 CPUs rather than 32, and the conda environment lists only direct
  dependencies.

### Fixed

- **Demultiplexing produced no output with dorado ≥ 1.2**, which writes a nested MinKNOW
  tree rather than flat per-barcode files. The rule collapses that tree, and fails loudly
  rather than silently producing empty barcodes if the layout changes again.
- **Basecalling ran once per GPU.** Plugin versions before 2.7.0 add `--ntasks-per-gpu=1`
  to any job requesting GPUs, so asking for 4 started 4 copies writing to the same file.
- Empty barcodes produced zero-byte `.bam` files, which are not valid bam and broke the
  conversion step. They are now header-only bam.
- QoS is passed as a `qos` resource; newer plugin versions reject it inside `slurm_extra`.
- `clean_all` looked for `basecalling.log` in the wrong place and left it behind.
- The log step aborted the whole run outside a git checkout; it now records `unknown`, and
  notes when the working tree had uncommitted changes.
- The plots are written to the paths the workflow declares, rather than next to their input,
  and their tick labels come from the data instead of being reconstructed.

## 2026-04-27

- Cluster QoS changed from `gpu6hours` to `a100-6hours`.

## 2024-09-27

- Stayed on dorado 7.0: 8.0 did not work well at the time.

## 2024-09-26

- Updated dorado for the basecalling speed improvements in 0.8.
- Added checks for a common mistake in the input path.

## 2024-05-24

- Documented methylation basecalling.
