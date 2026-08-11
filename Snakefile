# Pipeline to basecall the raw data generated from our nanopore, optionally calling
# modified bases as well. See docs/ for how to set it up and how to run it.
#
# This file holds the configuration, the run-folder layout, the log file and the
# cleanup. The rules themselves live in rules/, split by topic.
import json
import shlex
import time
import os
import sys


# Settings come in three layers, each one overriding the one before it:
#
#   config/config.yaml    the toolchain and the defaults, for every run
#   <run_dir>/run.yaml    the facts about this run, next to the data
#   --config key=value    a one-off, for this invocation only
#
# The layering is snakemake's own: a `configfile:` directive merges its file into the
# config and then re-applies whatever came from the command line, so --config always wins.
configfile: "config/config.yaml"


# ---------------------------------------------------------------------------
# Run folder
# ---------------------------------------------------------------------------

if "run_dir" not in config:
    sys.exit(
        "Error: no run folder given. Add --config run_dir=<path to your run folder> to the command."
    )

# pass the path to the folder as an argument when calling snakemake: --config run_dir=PATH
DATA_DIR = os.path.normpath(config["run_dir"])

if not os.path.exists(DATA_DIR):
    sys.exit(
        f"Error: The data directory '{DATA_DIR}' does not exist. Make sure you gave the correct path for your folder."
    )

# The second configuration layer. It lives in the run folder rather than in the
# repository, so that a run carries its own settings and two runs with different kits
# need no command-line juggling.
RUN_CONFIG = os.path.join(DATA_DIR, "run.yaml")
if not os.path.isfile(RUN_CONFIG):
    sys.exit(
        f"Error: The 'run.yaml' file is missing in '{DATA_DIR}'. It records what was "
        "sequenced — copy 'test_data/run.yaml' and see docs/running.md for what goes in it."
    )


configfile: RUN_CONFIG


INPUT_DIR = os.path.join(DATA_DIR, "raw")
TMP_DIR = os.path.join(DATA_DIR, "tmp")
OUTPUT_DIR = os.path.join(DATA_DIR, "final")
STATISTICS_DIR = os.path.join(DATA_DIR, "statistics")
# Per-rule logs. Kept out of TMP_DIR on purpose, so that they survive the clean rule
# and are still there to look at after a failed or a finished run.
LOG_DIR = os.path.join(DATA_DIR, "log")
EXEC_TIME = time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime())
LOGFILE = os.path.join(DATA_DIR, "basecalling.log")


# ---------------------------------------------------------------------------
# Dorado
# ---------------------------------------------------------------------------

DORADO_BIN = config["dorado_bin"]
DORADO_MODELS_DIR = config["models_dir"]
DORADO_MODEL = config["model"]

# Models are referred to by name and downloaded by the download_model local rule, then
# passed to dorado as a path. Passing a path (rather than a name) stops dorado from
# trying to resolve the model over the network, which compute nodes cannot do.
MODEL_PATH = os.path.join(DORADO_MODELS_DIR, DORADO_MODEL)

# Whether to call modified bases alongside the sequence.
MODIFICATIONS = bool(config["modifications"])
DORADO_MODS = config.get("mods_model")
if MODIFICATIONS and not DORADO_MODS:
    sys.exit(
        "Error: 'modifications' is set but 'mods_model' is empty. Give the name of a "
        "modified-base model in config/config.yaml or in the run's run.yaml, e.g. "
        "dna_r10.4.1_e8.2_400bps_sup@v5.2.0_6mA@v1."
    )
MODS_PATH = os.path.join(DORADO_MODELS_DIR, DORADO_MODS) if MODIFICATIONS else None

# Demultiplexing always writes bam, which is then converted to fastq. With modified
# bases the bam is a deliverable in its own right — fastq cannot carry the MM/ML tags —
# so it lives under final/ and survives the clean rule. Without them it is a plain
# intermediate, and goes to tmp/ where clean removes it.
FASTQ_DIR = os.path.join(OUTPUT_DIR, "fastq")
BAM_DIR = os.path.join(OUTPUT_DIR, "bam") if MODIFICATIONS else os.path.join(TMP_DIR, "bam")


# ---------------------------------------------------------------------------
# Sequencing protocol
# ---------------------------------------------------------------------------

# Facts about the physical run, so they have no default: inheriting a kit from the
# repository would quietly basecall a 96-barcode run as a 24-barcode one.
for key in ("kit", "flow_cell"):
    if not config.get(key):
        sys.exit(
            f"Error: '{key}' is missing from '{RUN_CONFIG}'. Both the kit and the flow "
            "cell have to be stated for every run — see docs/running.md."
        )

NANOPORE_KIT = config["kit"]

# The number of barcodes is taken from the kit name suffix, e.g. SQK-RBK114-24.
kit_suffix = NANOPORE_KIT.rsplit("-", 1)[-1]
if not kit_suffix.isdigit():
    sys.exit(
        f"Error: cannot infer the number of barcodes from kit '{NANOPORE_KIT}'. "
        "Expected a kit name ending in the barcode count, e.g. SQK-RBK114-24."
    )

NB_BARCODES = int(kit_suffix)
BARCODES = [str(ii).zfill(2) for ii in range(1, NB_BARCODES + 1)]


# ---------------------------------------------------------------------------
# Input checks
# ---------------------------------------------------------------------------

# Check that 'samples.tsv' file exists in DATA_DIR. It is never parsed, only appended to
# the log file, so its columns are up to whoever writes it.
SAMPLES_FILE = os.path.join(DATA_DIR, "samples.tsv")
if not os.path.isfile(SAMPLES_FILE):
    sys.exit(
        f"Error: The 'samples.tsv' file is missing in '{DATA_DIR}'. Please write down "
        "which barcode was which sample and add it to your run folder."
    )

# Check that 'raw' directory exists in DATA_DIR
if not os.path.isdir(INPUT_DIR):
    sys.exit(
        f"Error: The 'raw' directory is missing in '{DATA_DIR}'. Make sure that your in the right folder and that your raw data folder is correctly named."
    )

# Optionally, check if the 'raw' directory is not empty
if not os.listdir(INPUT_DIR):
    sys.exit(
        f"Error: The 'raw' directory '{INPUT_DIR}' is empty. Please ensure that it contains the raw nanopore files."
    )


localrules:
    all,
    generate_log_file,
    download_model,
    clean,
    clean_all,


wildcard_constraints:
    model=r"dna_r[0-9.]+_e[0-9.]+_[0-9]+bps_[a-z]+@v[0-9.]+(_[A-Za-z0-9]+@v[0-9.]+)?",


include: "rules/basecalling.smk"
include: "rules/statistics.smk"


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


rule all:
    input:
        fastq=expand(os.path.join(FASTQ_DIR, "barcode_{barcode}.fastq.gz"), barcode=BARCODES),
        unclassified=os.path.join(FASTQ_DIR, "unclassified.fastq.gz"),
        # With modified bases the bam files are an output, not an intermediate.
        bam=(
            expand(os.path.join(BAM_DIR, "barcode_{barcode}.bam"), barcode=BARCODES)
            if MODIFICATIONS
            else []
        ),
        plot1=os.path.join(STATISTICS_DIR, "len_hist.png"),
        plot2=os.path.join(STATISTICS_DIR, "bp_per_barcode.png"),
        plot3=os.path.join(STATISTICS_DIR, "quality_mean.png"),
        plot4=os.path.join(STATISTICS_DIR, "quality_std.png"),
        clean=os.path.join(DATA_DIR, ".cleaned_dummy_file.txt"),  # comment for debugging
    default_target: True


# The settings are handed over as a whole rather than one flag at a time, so that the log
# records every one of them — including keys the pipeline does not know about, which is
# what makes run.yaml a place to write free-form notes about the run.
rule generate_log_file:
    input:
        run_config=RUN_CONFIG,
        samples=SAMPLES_FILE,
    output:
        LOGFILE,
    log:
        os.path.join(LOG_DIR, "generate_log_file.log"),
    params:
        dorado=DORADO_BIN,
        ex_time=EXEC_TIME,
        settings=shlex.quote(json.dumps(dict(config), default=str)),
    conda:
        "conda_envs/nanopore_basecalling.yml"
    shell:
        """
        exec > {log} 2>&1
        python scripts/generate_log_file.py --output {output} \
        --dorado-bin {params.dorado} \
        --time {params.ex_time} \
        --settings {params.settings}
        cat {input.samples} >> {output}
        """


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


rule clean:
    message:
        "Cleaning up the output folder."
    input:
        rules.make_plots_lengths.output.len_hist,
        rules.make_plots_quality.output.quality_mean_plot,
        rules.make_plots_quality.output.quality_std_plot,
    output:
        os.path.join(DATA_DIR, ".cleaned_dummy_file.txt"),
    params:
        tmp_dir=TMP_DIR,
    shell:
        """
        rm -rf {params.tmp_dir}
        touch {output}
        """


rule clean_all:
    message:
        "Removing every output of the run, including the final files."
    params:
        output_dir=OUTPUT_DIR,
        statistics_dir=STATISTICS_DIR,
        tmp_dir=TMP_DIR,
        log_dir=LOG_DIR,
        logfile=LOGFILE,
        dummy=rules.clean.output,
    shell:
        """
        rm -rf {params.output_dir}
        rm -rf {params.statistics_dir}
        rm -rf {params.tmp_dir}
        rm -rf {params.log_dir}
        rm -f {params.logfile}
        rm -f {params.dummy}
        """
