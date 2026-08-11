# Setting up the pipeline

One-time setup. If you are going to run on the cluster, do all of this **on the cluster**,
in a directory you can get back to (basecalling a full run takes a couple of hours).

## 1. Get the pipeline

```bash
git clone https://github.com/neherlab/nanopore_basecalling.git
cd nanopore_basecalling
```

Everything below, and every later run, is done **from this directory**. The pipeline uses
relative paths, so it will not work from anywhere else.

## 2. Get dorado

Dorado is not distributed with the pipeline and is not in conda. Download the
`linux-x64` build from [the dorado releases page](https://github.com/nanoporetech/dorado),
unpack it, and put the resulting folder in `softwares/`:

```bash
mkdir -p softwares
cd softwares
wget https://cdn.oxfordnanoportal.com/software/analysis/dorado-2.1.1-linux-x64.tar.gz
tar -xzf dorado-2.1.1-linux-x64.tar.gz
cd ..
```

You should end up with `softwares/dorado-2.1.1-linux-x64/bin/dorado`. Check it runs:

```bash
./softwares/dorado-2.1.1-linux-x64/bin/dorado --version
```

If you use a different version, update `dorado_bin` in `config/config.yaml` to match —
the version number is part of the path.

**The basecalling models are downloaded for you** the first time you run the pipeline,
into `softwares/dorado_models/`, and reused afterwards. A run that calls modified bases
fetches one extra model per modification, the same way. You only need to fetch them by
hand if you want to work fully offline:

```bash
mkdir -p softwares/dorado_models
./softwares/dorado-2.1.1-linux-x64/bin/dorado download \
    --model dna_r10.4.1_e8.2_400bps_sup@v5.2.0 \
    --models-directory softwares/dorado_models
```

Here the model has to be given by its full name, chemistry and all — `dorado download` has
no flow cell to work it out from. The directory has to exist first: dorado refuses to
create it, and says so only on stderr.

> **On the cluster, always launch the pipeline from the login node.** Downloading a model
> is a local rule, and the compute nodes have no internet access.

## 3. Create the conda environment

```bash
conda env create -f conda_envs/nanopore_basecalling.yml
conda activate nanopore_basecalling
```

Activate this environment every time you use the pipeline.

## 4. Test that it works

A small dataset ships with the repository in `test_data/`. First check that the workflow
is wired up correctly, without running anything:

```bash
snakemake -n --config run_dir=test_data
```

This is a dry run: it prints the jobs it *would* run and exits. You should see a summary
ending in `total 84`, and no errors. It needs neither a GPU nor the dorado binary, so it
is a good check that the pipeline is installed correctly.

To actually basecall the test data, run it as you would a real run — see
[Preparing and running a run](running.md). On the cluster it takes a few minutes; on a
machine without a GPU it will take hours, so use a dry run instead.

## Where things end up

| Path | What |
|---|---|
| `softwares/` | dorado and its models. Not in git; you populate it. |
| `config/config.yaml` | the toolchain and the default settings |
| `rules/` | the workflow rules, split by topic |
| `efficiency_reports/` | per-run CPU and memory usage, written after each cluster run |
