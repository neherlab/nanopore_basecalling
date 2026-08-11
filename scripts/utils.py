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

# Fastq quality characters are Phred+33, so ASCII 33 ('!') to 126 ('~') covers every score
# a basecaller can emit: 94 bins, whatever the run.
PHRED_OFFSET = 33
NB_QSCORES = 94

# "Low quality" for the summary bar. Q20 is one error in a hundred bases, the conventional
# line between usable and not.
LOW_QUALITY_MAX = 20

# A barcode with fewer bases than this is left blank in the quality figures rather than
# drawn. Below a thousand bases a bin holding 1% of them holds fewer than ten, so the row
# is counting noise, not a distribution — and normalising it per barcode would make the
# noise as loud as a real result. Cross-talk barcodes that catch a single short read come
# in around a hundred bases, two orders of magnitude under anything genuine.
MIN_BASES_PLOTTED = 1000

# The Q-score heatmap saturates here. Dorado caps per-base quality at Q50 and puts about
# half of all bases there, so a scale running to the true maximum would show one bright
# column and nothing else; stopping at 3% keeps the Q36-45 hump and the low tail readable.
# The square root on top of that spreads the low tail, which is where barcodes differ —
# a log scale spreads it too far and makes a bad barcode look like a good one.
QSCORE_VMAX = 0.03
QSCORE_GAMMA = 0.5

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


def density_colormap():
    """White-to-SERIES_COLOR ramp, for the one figure that encodes a value as colour.

    Every other figure draws one series in one flat colour, since the barcode is already
    given by the row. The Q-score heatmap is a 2D density and has nothing else to encode
    the count with, so it gets a scale — built from the same blue, so the two kinds of
    figure still look like one set.
    """
    from matplotlib.colors import LinearSegmentedColormap

    return LinearSegmentedColormap.from_list("density", ["#ffffff", SERIES_COLOR])


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
