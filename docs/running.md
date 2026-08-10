# Preparing and running a run

Assumes you have already done the [setup](setup.md), and that you are in the pipeline
directory with the `nanopore_basecalling` environment active.

## 1. Prepare the run folder

A run folder is a directory containing exactly two things to start with:

```
my_run/
├── raw/            all the .pod5 files from the sequencer
└── params.tsv      what was on the flow cell
```

It can live anywhere — it does not have to be inside the pipeline directory. Everything
the pipeline produces is written into this same folder.

## 2. Write `params.tsv`

`params.tsv` is a tab-separated file recording what was sequenced. It is copied verbatim
into the run's log file, so it is what you will consult in a year's time to work out which
barcode was which sample. The pipeline checks that it exists but does not parse it, so the
exact columns are up to you — keep the shape below unless you have a reason not to:

```
Minknow run:	06-09-2023_Valentin-Giacomo
research_group:	neher
flow_cell_ID:	FAX57501

barcode	requester	strain_id
1	Valentin Druelle	1
2	Valentin Druelle	2
3	Valentin Druelle	3
```

The columns are separated by **tabs**, not spaces. There is a working example in
`test_data/params.tsv` to copy.

## 3. Check the settings

Everything the pipeline needs is in `config/config.yaml`:

```yaml
dorado_bin: "softwares/dorado-2.1.1-linux-x64/bin/dorado"
models_dir: "softwares/dorado_models"
model: "dna_r10.4.1_e8.2_400bps_sup@v5.2.0"

modifications: false
mods_model: "dna_r10.4.1_e8.2_400bps_sup@v5.2.0_6mA@v1"

kit: "SQK-RBK114-24"
flow_cell: "FLO-MIN114"
```

The one you are most likely to change is `kit`. **The number of barcodes is read from the
end of the kit name**, so `SQK-RBK114-96` gives 96 barcodes; there is no separate setting.

You can either edit the file, or override a setting for a single run on the command line
without touching it:

```bash
snakemake --profile cluster --config run_dir=my_run kit=SQK-RBK114-96
```

`run_dir` has no default and must always be given.

## 4. Run it

### On the cluster (recommended)

Basecalling takes hours, so start a `tmux` session first — that way the pipeline survives
losing your connection.

```bash
tmux new -s basecalling
conda activate nanopore_basecalling
snakemake --profile cluster --config run_dir=my_run
```

Detach with `Ctrl-b d`, and come back later with `tmux attach -t basecalling`.

Snakemake submits the jobs for you; you do not write any `sbatch` yourself. Launch it from
the **login node** — the model download needs internet, which the compute nodes do not
have. For a good run (20 Gbp) expect roughly 1h30.

### Locally

Only worth it with a strong GPU, or with a small/fast model:

```bash
snakemake --config run_dir=my_run --cores 8
```

### With methylation

Modified bases are called by the same pipeline, switched on with one setting:

```bash
snakemake --profile cluster --config run_dir=my_run modifications=True
```

or by setting `modifications: true` in `config/config.yaml`. `mods_model` picks which
modification is called — 6mA by default; the available models are listed in the
[dorado documentation](https://software-docs.nanoporetech.com/dorado/latest/models/list/).
Its version has to match `model`, so change the two together.

This adds `final/bam` to the output. **Those bam files are the real result of a
modified-base run**: FASTQ has no way to store modification tags, so they exist only in
the bam. The fastq files are still produced, without the modification information.

## 5. What you get

```
my_run/
├── raw/
├── params.tsv
├── final/
│   ├── fastq/              barcode_01.fastq.gz … unclassified.fastq.gz
│   └── bam/                only with modifications: barcode_01.bam …
├── statistics/             lengths.tsv, quality.tsv + four plots
├── log/                    one log per step, kept even if the run fails
└── basecalling.log         when it ran, with which versions and settings
```

The intermediate files are removed automatically at the end. `log/` is deliberately kept.

If a step fails, snakemake prints the path of the log to look at:

```
Error in rule basecall:
    log: my_run/log/basecall.log (check log file(s) for error details)
```

## Starting over

To delete everything a run produced and leave `raw/` and `params.tsv` untouched:

```bash
snakemake clean_all --config run_dir=my_run --cores 1
```

Re-running the pipeline normally is safe: snakemake only redoes what is missing or out of
date. Note that changing `kit` or `modifications` changes which files are expected, so the
run will pick up from wherever it can.
