# nanopore_basecalling

[![built with Codeium](https://codeium.com/badges/main)](https://codeium.com)

## Introduction
This pipeline is used to basecall raw data generated from a nanopore sequencing run (pod5). It performs the following steps:

- Generate a log file with information about the basecalling process.
- Basecall the reads using Dorado. Does this for the 24 barcoding kit by default, can do 96 with additional option.
- Split the reads based on detected barcodes and trim the barcodes from the reads (Dorado default behaviour).
- Convert the barcoded reads to FASTQ format.
- Generate statistics for the barcoded reads.
- Combine the statistics files for all the barcodes.
- Generate plots from the combined statistics file.
- Clean up the temporary files created along the way to avoid unecessary storage use.

The accuracy of de novo assemblies using nanopore only (with the same basecalling as in this pipeline) has been tested here (sup model): https://rrwick.github.io/2023/12/18/ont-only-accuracy-update.html

## How to run

### Prerequisite
Start by cloning this repo (on the cluster, if aiming for cluster execution):
```
git clone https://github.com/vdruelle/nanopore_basecalling.git
```

Once this is done, you need to download dorado (https://github.com/nanoporetech/dorado, linux-x64 in our case), unpack it and move the folder called `dorado-2.1.1-linux-x64` to the directory `softwares/`.

You do not need to download the basecalling model yourself: the pipeline fetches it into `softwares/dorado_models/` on first use and reuses it afterwards. If you do want to pre-fetch it (for instance to work offline), you can run:
```
./softwares/dorado-2.1.1-linux-x64/bin/dorado download --model dna_r10.4.1_e8.2_400bps_sup@v5.2.0 --models-directory softwares/dorado_models
```

Last you need to create the conda environment for the pipeline:
```
conda env create -f conda_envs/nanopore_basecalling.yml
```

### Running the pipeline
#### On the cluster (Scicore / SLURM) - recommended
We suggest running the pipeline from a tmux session. To do so start by launching a tmux session, then move to where you saved the repository and activate the conda environment with:

```
conda activate nanopore_basecalling
```

Your run folder must contain a subfolder named `raw` in which all your `.pod5` are located as well as the `params.tsv` file which you need to update. This is used for logging to keep track of the run. Start the pipeline, giving the path to your run folder as argument.
```
snakemake --profile cluster --config run_dir=<path to your run folder>
```
This command will launch the pipeline by submitting the appropriate jobs for cluster execution to basecall an split the 24 barcodes.
If you want to perform basecalling for 96 barcodes instead do the following instead:
```
snakemake --profile cluster --config run_dir=<path to your run folder> kit=SQK-RBK114-96
```
You can monitor the progress of the pipeline in the console output. For a good nanopore run (20Gbp), the pipeline should take around 1h30 to complete.

At the end of a cluster run a CSV appears in `efficiency_reports/`, listing how much of the requested CPU time and memory each rule actually used. It is worth a look if you are adjusting the resources in `cluster/config.v8+.yaml`.

Note that the pipeline must be launched from the login node. Downloading the dorado model is a local rule, and the compute nodes have no internet access.

#### Local execution
If running locally (which necessitate a strong GPU, unless using faster models), also start by activating the conda environment. Then launch the pipeline with:

```
snakemake --config run_dir=<path to your run folder> --cores <number of cores you want to use>
```

### Settings
The dorado binary path, the basecalling and modified-base models, the sequencing kit and the flow cell are all set in `config/config.yaml`. The number of barcodes is not configured separately: it is read from the end of the kit name, so `SQK-RBK114-96` gives 96 barcodes.

You can change a setting for a single run without editing that file:
```
snakemake --profile cluster --config run_dir=<path to your run folder> kit=SQK-RBK114-96
```
or keep your own copy of the whole file:
```
snakemake --profile cluster --config run_dir=<path to your run folder> --configfile my_config.yaml
```
`run_dir` has no default and must always be given on the command line.

### Output
Once the pipeline completes, should have more files and directories in your run folder. You should have:
- A directory `final/fastq`. It contains separate `.fastq.gz` files for all the barcodes. With `modifications` enabled you also get `final/bam`, holding the same reads as `.bam` — see [Modified basecalling](#modified-basecalling).
- A directory `statistics`. It contains a `.tsv` file for some statistics about the run, as well as two figures that can be used to get an idea of how the run went.
- A log file `basecalling.log`. This file describe when and with which parameter the basecalling happened.
- A directory `log`. It contains one file per step (basecalling, demultiplexing, statistics, plots), holding whatever dorado or the python scripts printed. If a step fails, snakemake reports the path of the file to look at.

The pipeline will also generate many intermediate outputs while it runs. They are automatically removed at the end. The `log` directory is kept, so that a run can still be inspected after it finished or failed; `snakemake clean_all` removes it along with everything else.

## Modified basecalling
The same pipeline can call modified bases (methylation) alongside the sequence. Set `modifications` to `true` in `config/config.yaml`, or for a single run:

```
snakemake --profile cluster --config run_dir=<path to your run folder> modifications=True
```

`mods_model` chooses which modification is called (6mA by default). The models available are listed at https://software-docs.nanoporetech.com/dorado/latest/models/list/. Its version is tied to the `model` setting, so the two need to be kept in step. The pipeline downloads whichever models you name, so there is nothing to fetch by hand.

A modified-base run additionally produces `final/bam`, with one `.bam` per barcode. **These are the real output of such a run**: the modification tags cannot be stored in a FASTQ file, so they only exist in the `.bam`. The `final/fastq` files are produced as usual, without the modification information.