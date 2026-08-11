# Preparing and running a run

Assumes you have already done the [setup](setup.md), and that you are in the pipeline
directory with the `nanopore_basecalling` environment active.

## 1. Prepare the run folder

A run folder is a directory containing exactly three things to start with:

```
my_run/
├── raw/            all the .pod5 files from the sequencer
├── run.yaml        what this run is, and how to basecall it
└── samples.tsv     which barcode was which sample
```

It can live anywhere — it does not have to be inside the pipeline directory. Everything
the pipeline produces is written into this same folder, and `run.yaml` and `samples.tsv`
stay with the data afterwards. There is a working example of each in `test_data/` to copy.

## 2. Write `run.yaml`

`run.yaml` says what was sequenced. It lives in the run folder rather than in the pipeline
directory, so that a run carries its own settings: two runs with different kits need no
juggling, and nothing has to be kept in sync with the repository.

```yaml
# Required.
kit: "SQK-RBK114-24"
flow_cell: "FLO-MIN114"

# Free-form: any key you add is recorded in the run's log file.
flow_cell_id: "FAX57501"
minknow_run: "06-09-2023_Valentin-Giacomo"
research_group: "neher"
```

`kit` and `flow_cell` are the two required keys, and they have no default — a kit
inherited from the pipeline defaults would quietly basecall a 96-barcode run as a
24-barcode one. **The number of barcodes is read from the end of the kit name**, so
`SQK-RBK114-96` gives 96 barcodes; there is no separate setting.

Everything else is yours. Anything you write here — the operator, the DNA prep, a note
about a flow cell that misbehaved — ends up in the run's log file untouched, so this is
the place for whatever you will want to know in a year's time.

`run.yaml` can also override any of the pipeline defaults from
[§4](#4-check-the-settings) for this one run:

```yaml
model: "hac@v6.0.0"
modifications: "4mC_5mC,6mA"
```

See [choosing a model and the modifications](#choosing-a-model-and-the-modifications), and
[docs/models.md](models.md) for the detail behind it.

## 3. Write `samples.tsv`

`samples.tsv` records which barcode was which sample. It is copied verbatim into the run's
log file. The pipeline checks that it exists but does not parse it, so the exact columns
are up to you — keep the shape below unless you have a reason not to:

```
barcode	requester	strain_id
1	Valentin Druelle	1
2	Valentin Druelle	2
3	Valentin Druelle	3
```

The columns are separated by **tabs**, not spaces.

## 4. Check the settings

Settings are read in three layers, each one overriding the one before it:

| Layer | Holds | When you touch it |
|---|---|---|
| `config/config.yaml` | the toolchain and the defaults | rarely — a lasting change for every run |
| `<run folder>/run.yaml` | the facts about this run | every run |
| `--config key=value` | one-off overrides | a single command |

`config/config.yaml` is the first layer:

```yaml
dorado_bin: "softwares/dorado-2.1.1-linux-x64/bin/dorado"
models_dir: "softwares/dorado_models"
model: "sup@v5.2.0"
modifications: ""
```

To try something once without editing anything, override it on the command line:

```bash
snakemake --profile cluster --config run_dir=my_run model=hac@v5.2.0
```

`run_dir` has no default and must always be given. Whatever the three layers come out to
is written into the run's log file, so a finished run can always be interrogated for the
settings it actually used.

### Choosing a model and the modifications

`model` is the basecalling model, written as `<tier>@<version>` — the chemistry in front of
it (`dna_r10.4.1_e8.2_400bps_...`) is filled in from the run's flow cell and kit. `sup` is
the default and the accurate choice; `hac` and `fast` are for testing the pipeline, for
reads that only need to identify something, and for when GPU time is short.

`modifications` lists the modified bases to call alongside the sequence, empty for a plain
run. They are all called in one pass and written into the same bam, and the models that call
them follow from `model`:

```yaml
model: "sup@v5.2.0"
modifications: "4mC_5mC,6mA"
```

Not every combination is possible — dorado allows only one modification per canonical base,
and not every model ships every one — but the pipeline checks before it submits anything, so
a bad combination costs you a second rather than a queued GPU job.

**[docs/models.md](models.md) has the details**: the accuracy and runtime each tier buys, why
there is no `sup@v6.0.0`, how to list what a model offers, and how to pin a modification to an
older version.

Note that changing the model does **not** on its own invalidate a finished run — snakemake
will report "nothing to be done", because the intermediates it would compare against were
cleaned up at the end of the run. To re-basecall an existing run with a different model,
[start over](#starting-over) first.

## 5. Run it

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

Modified bases are called by the same pipeline, by listing them in one setting. Put it in
the run's `run.yaml`, where it is recorded with the run:

```yaml
modifications: "4mC_5mC,6mA"
```

or, to try it once, on the command line:

```bash
snakemake --profile cluster --config run_dir=my_run modifications=4mC_5mC,6mA
```

All of them are called in the same pass and written into the same bam — see
[docs/models.md](models.md#the-modifications) for which can be combined.

This adds `final/bam` to the output. **Those bam files are the real result of a
modified-base run**: FASTQ has no way to store modification tags, so they exist only in
the bam. The fastq files are still produced, without the modification information.

## 6. What you get

```
my_run/
├── raw/
├── run.yaml
├── samples.tsv
├── final/
│   ├── fastq/              barcode_01.fastq.gz … unclassified.fastq.gz
│   └── bam/                only with modifications: barcode_01.bam …
├── statistics/             lengths.tsv, quality_hist.tsv + four plots
├── log/                    one log per step, kept even if the run fails
└── basecalling.log         when it ran, with which versions and settings
```

The intermediate files are removed automatically at the end. `log/` is deliberately kept.

The four plots are `len_hist.png` and `bp_per_barcode.png` for the read lengths, and
`quality_hist.png` and `low_quality.png` for the quality.

**The quality is reported per base, not per read.** `quality_hist.png` is a heatmap: one
row per barcode, Q score across, colour for the share of that barcode's bases. It is drawn
that way because the distribution has no useful average — dorado caps per-base quality at
Q50 and puts about half of all bases there, so a mean or a median says more about the cap
than about the run. `low_quality.png` reduces the same table to the one number worth
scanning down a 96-barcode column: the percentage of bases below Q20.

A barcode with fewer than a thousand bases is left blank in both, rather than drawn from
counting noise — cross-talk barcodes that catch one stray read would otherwise be the
loudest rows on the figure.

`basecalling.log` holds the dorado and pipeline versions, every setting the three layers
came out to, and `samples.tsv` copied in below them — so the run folder answers on its own
what was sequenced and how it was called.

If a step fails, snakemake prints the path of the log to look at:

```
Error in rule basecall:
    log: my_run/log/basecall.log (check log file(s) for error details)
```

## Starting over

To delete everything a run produced and leave `raw/`, `run.yaml` and `samples.tsv`
untouched:

```bash
snakemake clean_all --config run_dir=my_run --cores 1
```

Re-running the pipeline normally is safe: snakemake only redoes what is missing or out of
date. Note that changing `kit` or `modifications` changes which files are expected, so the
run will pick up from wherever it can.
