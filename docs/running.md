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

# Optional
model: "sup@v5.2.0" # the basecalling model, overrides the default in config/config.yaml
modifications: ""   # the modified bases to call, overrides the default in config/config.yaml

# Free-form: any key you add is recorded in the run's log file.
flow_cell_id: "FAX57501"
minknow_run: "06-09-2023_Valentin-Giacomo"
research_group: "neher"
```

`kit` and `flow_cell` are the two required keys.
**The number of barcodes is read from the end of the kit name**, so
`SQK-RBK114-96` gives 96 barcodes.

`run.yaml` can also override any of the pipeline defaults from
[config/config.yaml](#4-check-the-settings) for this one run:

```yaml
model: "hac@v6.0.0"
modifications: "4mC_5mC,6mA"
```

See [choosing a model and the modifications](#choosing-a-model-and-the-modifications), and
[docs/models.md](models.md) for the detail behind it.

> [!NOTE]
> Every other entry in the ``run.yaml`` file ends up in the run's log file untouched. This is a good place to record details about the run that are important to log. Feel free to add any additional information you want to keep with the run.


## 3. Write `samples.tsv`

`samples.tsv` records the link between barcodes and samples. It stores important information about the samples (e.g. requester, sample names/ids, etc.). Feel free to add additional columns to the table. It will be copied verbatim in the run's log file.

```
barcode	requester	strain_id
1	Valentin Druelle	1
2	Valentin Druelle	2
3	Valentin Druelle	3
```

## 4. Check the settings

Settings are read in three layers, each one overriding the one before it:

| Layer                   | Holds                          | When you touch it                       |
| ----------------------- | ------------------------------ | --------------------------------------- |
| `config/config.yaml`    | the toolchain and the defaults | rarely — a lasting change for every run |
| `<run folder>/run.yaml` | the facts about this run       | every run                               |
| `--config key=value`    | one-off overrides              | a single command                        |

`config/config.yaml` is the first layer. This config file is mainly responsible for storing the paths to the dorado binary and its models. It also sets the default model and modifications to use for basecalling, but you are supposed to specify them per run in `run.yaml`.

```yaml
dorado_bin: "softwares/dorado-2.1.1-linux-x64/bin/dorado"
models_dir: "softwares/dorado_models"
model: "sup@v5.2.0"
modifications: ""
```

Most of the setting for the run are specfied in the `run.yaml` file, which is the second layer. You're supposed to create it for every run, and it is copied into the run's log file. It overrides any default in `config/config.yaml`.

Finally, to try something once without editing anything, you can override it on the command line:

```bash
snakemake --profile cluster --config run_dir=my_run model=hac@v5.2.0
```

Whatever the three layers come out to is written into the run's log file, so a finished run can always be interrogated for the settings it actually used.

> [!IMPORTANT]
> `run_dir` has no default and must always be specified via command the command line option `--config run_dir=<my_run>`

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

Not every combination is possible (dorado allows only one modification per canonical base,
and not every model ships every one) but the pipeline checks before it submits anything.

You can check [docs/models.md](models.md) for more details on model choice.

## 5. Run it

### On the cluster (recommended)

Basecalling might take hours, so start a `tmux` session first — that way the pipeline survives
losing your connection. Then in the session activate the environment and launch the pipeline:

```bash
conda activate nanopore_basecalling
snakemake --profile cluster --config run_dir=my_run
```

Detach with `Ctrl-b d`, and come back later with `tmux a`.

### Calling methylation

To call DNA modifications, modify the corresponding entry in `run.yaml`:

```yaml
modifications: "6mA"
```

If you want to combine multiple modifications, separate them with commas:

```yaml
modifications: "4mC_5mC,6mA"
```

Note that only some modifications can be called together, and not every model supports every modification. See [docs/models.md](models.md#the-modifications) for more details.

Modifications cannot be stored in fastq files. Therefore this option adds `final/bam` to the output, containing the reads in BAM format with the modifications encoded in the `MM` and `ML` tags. The `final/fastq` output is still produced, but it does not contain any modification information. See [what a run produces](results.md#the-reads) for more details.

## 6. What you get

The reads land in `<run folder>/final/fastq/`, one gzipped FASTQ per barcode, with tables
and plots for the run in `statistics/`, a log per step in `log/`, and a record of what was
run in `basecalling.log`. The intermediates are cleaned up at the end. See [What a run produces](results.md) for more details.

## Starting over

To delete everything a run produced and leave `raw/`, `run.yaml` and `samples.tsv`
untouched:

```bash
snakemake clean_all --config run_dir=my_run --cores 1
```

Re-running the pipeline normally is safe: snakemake only redoes what is missing or out of
date. Note that changing `kit` or `modifications` changes which files are expected, so the
run will pick up from wherever it can.
