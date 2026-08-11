"""Write the log file of a run: the code version, the dorado version and the settings used."""

import argparse
import pathlib
import subprocess

import utils


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="path of the log file to write")
    parser.add_argument(
        "--dorado-bin",
        required=True,
        type=utils.existing_path,
        help="the dorado binary",
    )
    parser.add_argument("--model", required=True, help="name of the basecalling model")
    parser.add_argument(
        "--mods-model",
        help="name of the modified-base model, if modified bases were called",
    )
    parser.add_argument("--flow-cell", required=True, help="the flow cell used")
    parser.add_argument("--kit", required=True, help="the nanopore kit used")
    parser.add_argument("--time", required=True, help="execution time of the run")
    return parser.parse_args()


def capture(command, default="unknown"):
    """Run a command for the log, without letting a failure abort the whole run."""
    try:
        out = subprocess.check_output(command, shell=True, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, OSError):
        return default
    return out.decode().strip() or default


def main():
    args = parse_args()

    logfile = pathlib.Path(args.output)
    data_dir = logfile.parent
    data_dir.mkdir(parents=True, exist_ok=True)

    reporemote = capture("git remote -v | head -n 1")
    commitID = capture("git rev-parse HEAD")
    # A commit ID only pins the code if the working tree matched it.
    if capture("git status --porcelain", default=""):
        commitID += " (with uncommitted local changes)"
    doradover = capture(f"{args.dorado_bin} -v 2>&1")

    log_text = f"""
Log-file for the basecalling executed by the Snakemake script.
Execution time: {args.time}

The code is stored in the repository: {reporemote}
The current commit is: {commitID}
Dorado version: {doradover}
Dorado model: {args.model}
Modified bases: {args.mods_model or "not called"}
Flow cell: {args.flow_cell}
Nanopore kit: {args.kit}
Input dir: {data_dir / "raw"}
Output dir: {data_dir / "final"}

Parameter file:

"""

    with open(logfile, "w") as file:
        file.write(log_text)


if __name__ == "__main__":
    main()
