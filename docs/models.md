# Choosing a model and the modifications

Two settings decide how the reads are called: `model`, the basecalling model, and
`modifications`, the modified bases to call alongside the sequence. Both should be specified per run in `run.yaml` (see [§4 of the run guide](running.md#4-check-the-settings)).

In general:
- leave `model` at `sup@v5.2.0`, the most accurate model for bacterial DNA, unless you are testing the pipeline or have a reason to use a different tier or version.
- leave `modifications` empty for a plain run, or set it to the modifications you want to call (e.g. `modifications: "6mA"`).

Here are more details on what each setting does, and how to choose them.

## How a model is named

In the pipeline it is sufficient to specify the model as `<tier>@<version>`, e.g. `sup@v5.2.0`. Alternatively, it is also possible to specify *the full model name*.

A full dorado model name is `<chemistry>_<tier>@<version>` (e.g. `dna_r10.4.1_e8.2_400bps_sup@v5.2.0`).
The chemistry in front is decided by the flow cell and the kit, both of which `run.yaml` already states, so when not specified the pipeline fills it in for you.

The full list of models is in the
[dorado model list](https://software-docs.nanoporetech.com/dorado/latest/models/list/), or
straight from the binary:

```bash
DORADO=./softwares/dorado-2.1.1-linux-x64/bin/dorado

$DORADO download --list                        # to read on screen
$DORADO download --list-yaml | grep 'sup@'     # to filter
```

## The tiers

Dorado ships three tiers of basecalling model for a given chemistry, differing in the size
and the architecture of the network:

| Tier   | What it is for                      | Size at `v5.2.0`  |
| ------ | ----------------------------------- | ----------------- |
| `fast` | quick checks and weak hardware      | smallest          |
| `hac`  | "high accuracy" — the compromise    | 8.8 M parameters  |
| `sup`  | "super accurate" — the default here | 78.7 M parameters |

There is an excellent comparative benchmark of these models by Ryan Wick: [Dorado v2 basecalling models](https://rrwick.github.io/2026/06/11/dorado-v2.html) (June 2026):

| Model        | Median read accuracy | Median assembly errors | ~132 Gbp on an H100 |
| ------------ | -------------------- | ---------------------- | ------------------- |
| `hac@v6.0.0` | Q18.1 (98.46%)       | 11                     | 7h48                |
| `sup@v5.2.0` | Q20.6 (99.13%)       | 4                      | 21h33               |

The benchmark revealed that `sup` costs roughly **2.75× the GPU time** but makes about **43% fewer read errors** than `hac`. For this reason we set `sup` as the default model in the pipeline.

> [!NOTE]
> To re-basecall an existing run with a different model, clear all the results first, see [starting over](running.md#starting-over).

## The modifications

`modifications` is a comma separated list of the modified bases to call alongside the
sequence, and empty for a plain run:

```yaml
modifications: "4mC_5mC,6mA"
```

All of them are called in one pass and written into the same bam.

Not all combinations of model and modification are valid. There are two rules:

- **The modification has to exist for the model you chose.** Not every tier and version
  ships every one (e.g. `fast` has none at all). You can check [the list of dorado models](https://software-docs.nanoporetech.com/dorado/latest/models/list/).
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

A follow-up [methylation benchmark](https://rrwick.github.io/2026/07/08/dorado-v2-methylation.html) by Ryan Wick indicated that `sup@v5.2.0` seems to be a good default model for methylation calls as well.

> [!NOTE]
> Remember that modifications are stored in the output `bam` files, as FASTQ cannot carry them.
