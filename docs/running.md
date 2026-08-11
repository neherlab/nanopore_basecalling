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
model: "dna_r10.4.1_e8.2_400bps_hac@v5.2.0"
modifications: true
mods_model: "dna_r10.4.1_e8.2_400bps_hac@v5.2.0_6mA@v1"
```

`mods_model` has to match the version of `model`, so if you override one, override the
other with it — see [choosing a model](#choosing-a-model).

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
model: "dna_r10.4.1_e8.2_400bps_sup@v5.2.0"

modifications: false
mods_model: "dna_r10.4.1_e8.2_400bps_sup@v5.2.0_6mA@v1"
```

To try something once without editing anything, override it on the command line:

```bash
snakemake --profile cluster --config run_dir=my_run model=dna_r10.4.1_e8.2_400bps_hac@v5.2.0
```

`run_dir` has no default and must always be given. Whatever the three layers come out to
is written into the run's log file, so a finished run can always be interrogated for the
settings it actually used.

### Choosing a model

`model` is the other setting worth thinking about. Dorado ships three tiers of basecalling
model for a given chemistry, differing in the size and the architecture of the network:

| Tier | What it is for | Size at `v5.2.0` |
|---|---|---|
| `fast` | quick checks and weak hardware | smallest |
| `hac` | "high accuracy" — the compromise | 8.8 M parameters |
| `sup` | "super accurate" — **the default here** | 78.7 M parameters |

Model names look like `dna_r10.4.1_e8.2_400bps_<tier>@<version>`; the leading part is the
chemistry and has to match the flow cell. The full list is in the
[dorado model list](https://software-docs.nanoporetech.com/dorado/latest/models/list/), or
straight from the binary:

```bash
DORADO=./softwares/dorado-2.1.1-linux-x64/bin/dorado

$DORADO download --list                        # to read on screen
$DORADO download --list-yaml | grep 'sup@'     # to filter
```

Use `--list-yaml` for the second one: `--list` writes to stderr and prints **nothing at all**
when stdout and stderr end up in the same place, so the obvious `--list 2>&1 | grep` comes
back empty.

**The tiers are a real accuracy difference, not a rounding error.** Ryan Wick benchmarked
them on bacterial genomes in
[Dorado v2 basecalling models](https://rrwick.github.io/2026/06/11/dorado-v2.html)
(June 2026):

| Model | Median read accuracy | Median assembly errors | ~132 Gbp on an H100 |
|---|---|---|---|
| `hac@v5.2.0` | Q17.2 (98.09%) | 25.5 | 8h04 |
| `hac@v6.0.0` | Q18.1 (98.46%) | 11 | 7h48 |
| `sup@v5.2.0` | Q20.6 (99.13%) | 4 | 21h33 |

So `sup` costs roughly **2.75× the GPU time** and makes about **43% fewer read errors** than
even the newest `hac`, ending at 4 assembly errors per genome against 11. For de novo
assembly that is worth the wait, which is why the default here is `sup`. Drop to `hac` or
`fast` when you are testing the pipeline itself, when the reads only need to identify
something, or when GPU time is short — see also [running locally](#locally).

Two things from the same post are worth knowing before you reach for `v6.0.0`:

- **There is no `sup@v6.0.0`** — ONT released `hac@v6.0.0` on the argument that a `sup` tier
  is no longer needed. Wick's numbers do not support that: `sup@v5.2.0` beat `hac@v6.0.0` at
  both the read and the assembly level. Until a `sup@v6` exists, `sup@v5.2.0` is still the
  accurate choice.
- **`hac@v6.0.0` was uneven across species** — around 100 assembly errors on *Klebsiella*
  genomes, against its median of 11.

If you change `model`, change `mods_model` with it: the versions have to match, so
`..._hac@v6.0.0` goes with `..._hac@v6.0.0_6mA@v1`. And note that changing the model does
**not** on its own invalidate a finished run — snakemake will report "nothing to be done",
because the intermediates it would compare against were cleaned up at the end of the run. To
re-basecall an existing run with a different model, [start over](#starting-over) first.

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

Modified bases are called by the same pipeline, switched on with one setting. Put it in
the run's `run.yaml`, where it is recorded with the run:

```yaml
modifications: true
```

or, to try it once, on the command line:

```bash
snakemake --profile cluster --config run_dir=my_run modifications=True
```

`mods_model` picks which modification is called — 6mA by default; the available models are
listed in the
[dorado documentation](https://software-docs.nanoporetech.com/dorado/latest/models/list/).
Its version has to match `model`, so change the two together.

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
├── statistics/             lengths.tsv, quality.tsv + four plots
├── log/                    one log per step, kept even if the run fails
└── basecalling.log         when it ran, with which versions and settings
```

The intermediate files are removed automatically at the end. `log/` is deliberately kept.

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
