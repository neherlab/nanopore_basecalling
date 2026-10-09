# Nanopore basecalling with dorado

Basecalls raw nanopore data (`.pod5`) with [dorado](https://github.com/nanoporetech/dorado),
splits the reads by barcode, and produces per-barcode `fastq.gz` plus statistics and plots
for the run. Optionally calls modified bases (methylation) as well. Written for the Scicore
SLURM cluster (but it runs locally too).

## Documentation

- **[Setting up the pipeline](docs/setup.md)** — getting the code and dorado, creating the
  conda environment, checking that it works.
- **[Preparing and running a run](docs/running.md)** — the run folder, `run.yaml` and
  `samples.tsv`, optional methylation settings, and commands to run it on the cluster.
- **[Choosing a model and the modifications](docs/models.md)** — different model tiers, their accuracy and settings for methylation calling.
- **[What a run produces](docs/results.md)** — the output files, and the tables and plots
  describing the run.

## In short

To run on the cluster, after setting up the conda environment and preparing the input directory, do:

```bash
conda activate nanopore_basecalling
snakemake --profile cluster --config run_dir=<your run folder>
```

The run folder contains a `raw/` directory of `.pod5` files, a `run.yaml` saying what
was sequenced, and a `samples.tsv` saying which barcode was which sample. Results land in
`<run folder>/final/fastq/`, with statistics in `statistics/` and per-step logs in `log/`.

## What it does

1. Write a log file recording the versions and settings used.
2. Basecall the reads with dorado, tagging them with their barcode. Optionally call modified bases (methylation) as well.
3. Split them per barcode and trim the barcode off (dorado's default).
4. Convert to FASTQ and compress.
5. Compute per-barcode read length and quality statistics, and plot them.
6. Remove the intermediate files.

Basecalling accuracy for bacterial de novo assemblies using Nanopore only has been tested
[here](https://rrwick.github.io/2026/06/11/dorado-v2.html).

## Layout

| Path                    | What                                                                                  |
| ----------------------- | ------------------------------------------------------------------------------------- |
| `Snakefile`             | settings, run-folder layout, log file, cleanup                                        |
| `rules/basecalling.smk` | model download, basecalling, demultiplexing, compression                              |
| `rules/statistics.smk`  | per-barcode statistics and plots                                                      |
| `scripts/`              | the python steps, one script per rule, plus a shared `utils.py`                       |
| `config/config.yaml`    | the toolchain and the default settings, overridden per run by `<run folder>/run.yaml` |
| `cluster/`              | the SLURM profile                                                                     |
| `cluster-cpu/`          | the same, basecalling on CPUs instead of GPUs (a fallback for a long GPU queue)       |
