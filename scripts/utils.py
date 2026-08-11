"""Helpers shared by the pipeline scripts.

The scripts are run as `python scripts/<name>.py` from the repository root, which puts
this directory on `sys.path`, so a plain `import utils` resolves.
"""

import argparse
import pathlib

# One series per figure, so every mark takes the same colour: the barcode is already
# given by the position on the axis, and a colour per barcode would encode nothing.
SERIES_COLOR = "#2a78d6"
GRID_COLOR = "#e0e0dd"

# The median/IQR box drawn inside each violin. Thinner and lighter than the seaborn
# default, which otherwise reads louder than the distribution it sits in.
INNER_KWS = {"box_width": 2.5, "whis_width": 0.8, "color": "#33322f"}


def barcode_labels(columns):
    "Short tick labels taken from the column names, e.g. barcode_07 -> 07."
    return [column.replace("barcode_", "") for column in columns]


def figsize(nb_columns):
    "Canvas with a fixed width and one row of height per barcode."
    return (9, max(6, 0.25 * nb_columns + 1.5))


def barcode_columns(nb_barcodes):
    "Column order of the stats tables: barcode_01..barcode_NN, then unclassified."
    return [f"barcode_{str(ii).zfill(2)}" for ii in range(1, nb_barcodes + 1)] + [
        "unclassified"
    ]


def existing_path(value):
    "argparse type for a path that must already be there."
    path = pathlib.Path(value)
    if not path.exists():
        raise argparse.ArgumentTypeError(f"no such file or directory: {value}")
    return path


def label_and_save(columns, output, xlabel):
    """Label the axes, tidy the frame and write the current figure out.

    The barcodes go on the y-axis and the measured quantity on the x-axis: every barcode
    then gets its own row, the labels read horizontally instead of rotated, and a 96
    barcode kit makes the figure taller rather than more crowded.

    matplotlib is imported here rather than at the top of the module, so that the scripts
    which only need the helpers above do not pay for the import.
    """
    import matplotlib.pyplot as plt
    import seaborn as sns

    ax = plt.gca()
    ax.set_yticks(range(len(columns)), barcode_labels(columns), fontsize="small")
    ax.set_ylabel("Barcode")
    ax.set_xlabel(xlabel)
    # A hairline grid along the value axis only, kept behind the marks.
    ax.set_axisbelow(True)
    ax.grid(visible=True, axis="x", color=GRID_COLOR, linewidth=0.6)
    ax.grid(visible=False, axis="y")
    sns.despine(ax=ax)
    plt.tight_layout()
    plt.savefig(output, facecolor="w", dpi=200)
    plt.close()
