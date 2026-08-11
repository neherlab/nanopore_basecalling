# Choosing a model and the modifications

Two settings decide how the reads are called: `model`, the basecalling model, and
`modifications`, the modified bases to call alongside the sequence. Both live in
`config/config.yaml` as defaults and can be overridden per run in `run.yaml` or on the
command line — see [§4 of the run guide](running.md#4-check-the-settings) for the layering.

This page is the long version. The short one: leave `model` at `sup@v5.2.0` unless GPU time
is short, and list the modifications you want as `modifications: "4mC_5mC,6mA"`.

## How a model is named

**Write the model as `<tier>@<version>`**, e.g. `sup@v5.2.0`.

A dorado model name is really `<chemistry>_<tier>@<version>` —
`dna_r10.4.1_e8.2_400bps_sup@v5.2.0`. The chemistry in front is decided by the flow cell and
the kit, both of which `run.yaml` already states, so the pipeline fills it in for you. A full
name is still accepted, and is the escape hatch if you ever need one the pipeline cannot
derive (a kit dorado's catalogue does not list, say).

The full list is in the
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

## The tiers

Dorado ships three tiers of basecalling model for a given chemistry, differing in the size
and the architecture of the network:

| Tier | What it is for | Size at `v5.2.0` |
|---|---|---|
| `fast` | quick checks and weak hardware | smallest |
| `hac` | "high accuracy" — the compromise | 8.8 M parameters |
| `sup` | "super accurate" — **the default here** | 78.7 M parameters |

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
something, or when GPU time is short — see also
[running locally](running.md#locally).

Two things from the same post are worth knowing before you reach for `v6.0.0`:

- **There is no `sup@v6.0.0`** — ONT released `hac@v6.0.0` on the argument that a `sup` tier
  is no longer needed. Wick's numbers do not support that: `sup@v5.2.0` beat `hac@v6.0.0` at
  both the read and the assembly level. Until a `sup@v6` exists, `sup@v5.2.0` is still the
  accurate choice.
- **`hac@v6.0.0` was uneven across species** — around 100 assembly errors on *Klebsiella*
  genomes, against its median of 11.

Note that changing the model does **not** on its own invalidate a finished run — snakemake
will report "nothing to be done", because the intermediates it would compare against were
cleaned up at the end of the run. To re-basecall an existing run with a different model,
[start over](running.md#starting-over) first.

## The modifications

`modifications` is a comma separated list of the modified bases to call alongside the
sequence, and empty for a plain run:

```yaml
modifications: "4mC_5mC,6mA"
```

All of them are called in one pass and written into the same bam. The models that call them
are worked out from `model`, so there is nothing else to keep in step.

Two rules decide what is allowed, and the pipeline checks both **before it submits
anything** — a mistake costs you a second, not a queued GPU job:

- **The modification has to exist for the model you chose.** Not every tier and version
  ships every one: `fast` has none at all, and `4mC_5mC` exists for `hac`/`sup` at `v5.2.0`
  but not at `v4.3.0`. Ask for one that does not and the error lists the ones that do.
- **Only one modification per canonical base.** This is dorado's own rule: two models whose
  motifs overlap on the same base cannot run in one pass. So `4mC_5mC` (on C) and `6mA` (on
  A) go together, while `5mC_5hmC` (C) and `5mCG_5hmCG` (CG) do not.

For DNA at `sup@v5.2.0` or `hac@v6.0.0` that leaves one of `4mC_5mC`, `5mC_5hmC` or
`5mCG_5hmCG` on C, plus `6mA` on A — so at most two at once. To see what any model has:

```bash
$DORADO download --list-structured | grep -A2 'sup@v5.2.0_'
```

Each extra modification is another network running beside the basecaller, so it costs GPU
time and memory; ask for the ones you will actually look at.

By default the current version of each model is used. To pin an older one, append it:
`modifications: "5mC_5hmC@v1"`.

**The bam files are the real output of a modified-base run.** FASTQ cannot carry the `MM`/`ML`
tags, so with any modification the per-barcode bam files are kept in `final/bam` rather than
thrown away with the other intermediates. The FASTQ files are still produced, without the
modification information.
