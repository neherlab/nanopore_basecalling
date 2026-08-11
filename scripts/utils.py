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

# One box per barcode. A 96-barcode kit gets a quarter inch of height per row, which is
# not enough for a violin to show its shape — the kernel collapses into a sliver — so the
# distributions are drawn as boxes instead.
#
# The whiskers are percentiles rather than seaborn's 1.5*IQR default: a barcode holds tens
# of thousands of reads, and that rule then marks thousands of them as outliers, which
# draws as a solid smear across the row and buries the box it is meant to annotate. The
# 1st and 99th percentiles say the same thing about the tails and stay readable, so the
# outliers themselves are left off.
BOX_KWS = {
    "linewidth": 0.8,
    "width": 0.65,
    "whis": (1, 99),
    "showfliers": False,
    "medianprops": {"color": "#33322f", "linewidth": 1.2},
}


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
