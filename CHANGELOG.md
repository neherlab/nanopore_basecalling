# Changelog

Notable changes to the pipeline. Newest first.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The pipeline
is not versioned or released — "Unreleased" means "on `main`".

## Unreleased

Modernisation of the toolchain and the workflow. Anyone with an existing checkout should
re-create the conda environment, and check the two breaking changes below.

### Breaking

- Final FASTQ moved from `final/*.fastq.gz` to **`final/fastq/*.fastq.gz`**. Scripts
  pointing at the old location need updating.
- Modified-base runs are no longer a separate workflow: `snakemake -s methylation.smk …`
  is replaced by **`--config modifications=True`**, and their outputs move from
  `final/fastq_files/` and `final/bam_files/` to `final/fastq/` and `final/bam/`.
- Choosing the 96-barcode kit is now `--config kit=SQK-RBK114-96` instead of `kit96=True`.
  The barcode count is read from the end of the kit name.
- The conda environment must be re-created: it now pins
  `snakemake-executor-plugin-slurm>=2.7.0` (see below) and needs Python ≥ 3.11.

### Added

- `config/config.yaml` holds every setting — dorado binary, models, kit, flow cell,
  modifications. Override per-run with `--config key=value` or wholesale with
  `--configfile`.
- Per-step log files in `<run folder>/log/`, kept after the run so a failure can be
  investigated. Snakemake reports the relevant path when a step fails.
- `modifications` flag, replacing the separate methylation workflow.
- `download_model` rule: models are fetched automatically on first use. It runs on the
  login node, since the compute nodes have no internet access.
- A CPU and memory efficiency report per cluster run, written to `efficiency_reports/`.
- `docs/`, with a setup guide and a guide to preparing and running a run.
- This changelog.

### Changed

- dorado 0.7.0 → **2.1.1**; basecalling model `sup@v5.0.0` → `sup@v5.2.0`.
- Snakemake 7 → **9**, and the cluster profile from the removed `--cluster`/
  `cluster-config` mechanism to the SLURM executor plugin
  (`cluster/config.v8+.yaml`). `cluster/cluster_config.json` and
  `cluster/slurm_submit.sh` are gone.
- One workflow instead of two near-identical ones. The rules are split by topic into
  `rules/basecalling.smk` and `rules/statistics.smk`, with the Snakefile holding the
  configuration, the log file and the cleanup.
- Demultiplexing always produces bam, which is then converted to FASTQ. With
  `modifications` the bam files are kept in `final/bam`, because FASTQ cannot carry the
  `MM`/`ML` modification tags.
- `basecall` now requests 16 CPUs rather than 32, pending the efficiency report.
- The conda environment lists only direct dependencies instead of a full solve.
- `snakecommands.py` is replaced by `scripts/`, one plain `argparse` script per step plus a
  shared `scripts/utils.py`. The `click` dependency is gone.
- The statistics plots are now horizontal — barcodes on the y-axis, the measured quantity on
  the x-axis — in a single colour. The labels read horizontally instead of rotated, and the
  figure grows taller with the number of barcodes rather than more crowded, which makes the
  96-barcode kit legible.

### Fixed

- **Demultiplexing produced no output with dorado ≥ 1.2**, which writes a nested MinKNOW
  directory tree rather than flat per-barcode files. The rule now collapses that tree, and
  fails loudly rather than silently producing empty barcodes if the layout changes again.
- **Basecalling ran once per GPU.** Versions of the SLURM executor plugin before 2.7.0 add
  `--ntasks-per-gpu=1` to any job requesting GPUs, so asking for 4 GPUs started 4 copies of
  the job, all writing to the same file. The environment now pins `>=2.7.0`.
- QoS is passed as a `qos` resource; newer plugin versions reject it inside `slurm_extra`.
- Empty barcodes in modified-base runs produced zero-byte `.bam` files, which are not
  valid bam and made the conversion step fail. They are now header-only bam files.
- `clean_all` did not delete `basecalling.log`, having looked for it in the wrong place.
- The log file step aborted the whole run when the pipeline was not a git checkout. It now
  records `unknown`, and notes when the working tree had uncommitted changes.
- The plots are written to the paths the workflow declares, rather than next to their
  input, and their x-axis labels are taken from the data instead of being reconstructed.

## 2026-04-27

- Cluster QoS changed from `gpu6hours` to `a100-6hours`.

## 2024-09-27

- Stayed on dorado 7.0: 8.0 did not work well at the time.

## 2024-09-26

- Updated dorado for the basecalling speed improvements in 0.8.
- Added checks for a common mistake in the input path.

## 2024-05-24

- Documented methylation basecalling.
