"""Helpers shared by the pipeline scripts.

The scripts are run as `python scripts/<name>.py` from the repository root, which puts
this directory on `sys.path`, so a plain `import utils` resolves.
"""

import argparse
import pathlib

# Shared canvas size for every figure of the pipeline.
FIGSIZE = (12, 8)


def barcode_labels(columns):
    "Short x-tick labels taken from the column names, e.g. barcode_07 -> 07."
    return [column.replace("barcode_", "") for column in columns]


def barcode_columns(nb_barcodes):
    "Column order of the stats tables: barcode_01..barcode_NN, then unclassified."
    return [f"barcode_{str(ii).zfill(2)}" for ii in range(1, nb_barcodes + 1)] + ["unclassified"]


def existing_path(value):
    "argparse type for a path that must already be there."
    path = pathlib.Path(value)
    if not path.exists():
        raise argparse.ArgumentTypeError(f"no such file or directory: {value}")
    return path


def label_and_save(columns, output, xlabel="Barcode"):
    """Label the x-axis with the barcode numbers and write the current figure out.

    matplotlib is imported here rather than at the top of the module, so that the scripts
    which only need the helpers above do not pay for the import.
    """
    import matplotlib.pyplot as plt

    plt.xlabel(xlabel)
    plt.xticks(range(len(columns)), barcode_labels(columns), rotation=80, fontsize="small")
    plt.tight_layout()
    plt.savefig(output, facecolor="w", dpi=200)
    plt.close()
