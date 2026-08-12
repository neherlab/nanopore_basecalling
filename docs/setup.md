# Setting up the pipeline

One-time setup. If you are going to run on the cluster, do all of this **on the cluster**.

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

> [!IMPORTANT]
> **On the cluster, always launch the pipeline from the login/vscode node from a `tmux` session.**
> Login nodes have access to the internet (important for downloading models), and `tmux` keeps the session alive if you disconnect.

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

This is a dry run: it prints the jobs it *would* run and exits. It needs neither a GPU nor the dorado binary, so it is a good check that the pipeline is installed correctly.

To actually basecall the test data, run it as you would a real run — see
[Preparing and running a run](running.md). On the cluster it takes a few minutes; on a
machine without a GPU it will take hours, so use a dry run instead.

## 5. What comes next

Once this one-time initial setup is done, you can prepare and run a real run — see
[Preparing and running a run](running.md).