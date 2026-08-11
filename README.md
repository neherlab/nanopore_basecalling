# nanopore_basecalling

Basecalls raw nanopore data (`.pod5`) with [dorado](https://github.com/nanoporetech/dorado),
splits the reads by barcode, and produces per-barcode `fastq.gz` plus statistics and plots
for the run. Optionally calls modified bases (methylation) as well. Written for the Scicore
SLURM cluster, but it runs locally too.

## Documentation

- **[Setting up the pipeline](docs/setup.md)** — getting the code and dorado, creating the
  conda environment, checking that it works.
- **[Preparing and running a run](docs/running.md)** — the run folder, `run.yaml` and
  `samples.tsv`, and the commands for the cluster, locally, and with methylation.
- **[Choosing a model and the modifications](docs/models.md)** — what each tier of model
  buys you, and which modified bases can be called together.
- **[Changelog](CHANGELOG.md)** — what changed and when.

## In short

```bash
conda activate nanopore_basecalling
snakemake --profile cluster --config run_dir=<your run folder>
```

where the run folder contains a `raw/` directory of `.pod5` files, a `run.yaml` saying what
was sequenced, and a `samples.tsv` saying which barcode was which sample. Results land in
`<run folder>/final/fastq/`, with statistics in `statistics/` and per-step logs in `log/`.

## What it does

1. Write a log file recording the versions and settings used.
2. Basecall the reads with dorado, tagging them with their barcode.
3. Split them per barcode and trim the barcode off (dorado's default).
4. Convert to FASTQ and compress.
5. Compute per-barcode read length and quality statistics, and plot them.
6. Remove the intermediate files.

The accuracy of de novo assemblies using nanopore only, with the same basecalling as this
pipeline (sup model), has been tested
[here](https://rrwick.github.io/2023/12/18/ont-only-accuracy-update.html).

## Layout

| Path | What |
|---|---|
| `Snakefile` | settings, run-folder layout, log file, cleanup |
| `rules/basecalling.smk` | model download, basecalling, demultiplexing, compression |
| `rules/statistics.smk` | per-barcode statistics and plots |
| `scripts/` | the python steps, one script per rule, plus a shared `utils.py` |
| `config/config.yaml` | the toolchain and the default settings, overridden per run by `<run folder>/run.yaml` |
| `cluster/` | the SLURM profile |
