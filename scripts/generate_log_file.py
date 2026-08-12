"""Write the log file of a run: the code version, the dorado version and the settings used."""

import argparse
import json
import pathlib
import subprocess

import utils
import yaml


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="path of the log file to write")
    parser.add_argument(
        "--dorado-bin",
        required=True,
        type=utils.existing_path,
        help="the dorado binary",
    )
    parser.add_argument(
        "--settings",
        required=True,
        type=json.loads,
        help="the settings the run was launched with, as json",
    )
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

    # Everything the run was launched with, defaults and run folder and command line
    # already merged, written out as it was received. Nothing is picked out by name, so
    # a setting added to the pipeline lands here without this script being touched.
    settings = yaml.safe_dump(args.settings, sort_keys=False, default_flow_style=False)

    log_text = f"""
Log-file for the basecalling executed by the Snakemake script.
Execution time: {args.time}

The code is stored in the repository: {reporemote}
The current commit is: {commitID}
Dorado version: {doradover}
Input dir: {data_dir / "raw"}
Output dir: {data_dir / "final"}

Settings:

{settings}
Samples:

"""

    with open(logfile, "w") as file:
        file.write(log_text)


if __name__ == "__main__":
    main()
