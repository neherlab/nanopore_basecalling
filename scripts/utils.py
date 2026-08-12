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

# A barcode with fewer bases than this is left out of the figures rather than drawn. Below
# a thousand bases a bin holding 1% of them holds fewer than ten, so the row is counting
# noise, not a distribution — and normalising it per barcode would make the noise as loud
# as a real result. Cross-talk barcodes that catch a single short read come in around a
# hundred bases, two orders of magnitude under anything genuine.
MIN_BASES_PLOTTED = 1000

# Colours for what is marked on top of a series. The Q-score distribution reports two
# summaries per barcode and needs one each; the length distribution marks N50, and takes
# the same accent as the mean deliberately — no figure draws both.
MEAN_COLOR = "#d1495b"
ACCURACY_COLOR = "#1b7f5f"
N50_COLOR = "#d1495b"

# Read length classes, as (key, label, lower bound, upper bound), the last open-ended.
# generate_stats counts with the bounds and names its rows after the key, and the yield
# figure labels its legend with the label, so the classes are defined once here.
LENGTH_CLASSES = [
    ("under_1kb", "< 1 kb", 0, 1_000),
    ("1_10kb", "1–10 kb", 1_000, 10_000),
    ("10_50kb", "10–50 kb", 10_000, 50_000),
    ("over_50kb", "> 50 kb", 50_000, None),
]

# Length class is an ordered quantity, so the segments of the yield bar are a single-hue
# ramp anchored on SERIES_COLOR rather than four unrelated hues: darker means longer, and
# the order reads without consulting the legend.
LENGTH_CLASS_COLORS = ["#bcd7ee", "#7fb0e0", "#2a78d6", "#12457f"]

# A figure that writes a header line above every row needs more than the quarter inch
# `figsize` gives one. Past two dozen barcodes the header drops to x-small, so the row can
# lose some height with it — otherwise a 96-barcode kit runs to five feet of canvas.
ROW_HEIGHT = 0.62
ROW_HEIGHT_DENSE = 0.42
DENSE_ABOVE = 24

# One box per barcode. A violin was tried first and does not survive the row height — the
# kernel collapses into a sliver — so the distributions are drawn as boxes instead.
BOX_KWS = {
    "widths": 0.65,
    "showfliers": False,
    "patch_artist": True,
    "boxprops": {"facecolor": SERIES_COLOR, "edgecolor": "#33322f", "linewidth": 0.8},
    "whiskerprops": {"color": "#33322f", "linewidth": 0.8},
    "capprops": {"color": "#33322f", "linewidth": 0.8},
    "medianprops": {"color": "#33322f", "linewidth": 1.2},
}

# The five numbers ax.bxp draws a box from, mapped onto the rows of the summary table.
# The whiskers are the 1st and 99th percentiles rather than the usual 1.5*IQR: a barcode
# holds tens of thousands of reads, and that rule marks thousands of them as outliers,
# which draws as a solid smear across the row and buries the box it annotates. Naming the
# rows here keeps generate_stats, which writes them, and make_plots_lengths, which reads
# them, from drifting apart.
BOX_STATISTICS = {
    "whislo": "length_p1",
    "q1": "length_q1",
    "med": "length_median",
    "q3": "length_q3",
    "whishi": "length_p99",
}


def barcode_labels(columns):
    "Short tick labels taken from the column names, e.g. barcode_07 -> 07."
    return [column.replace("barcode_", "") for column in columns]


def figsize(nb_columns, row=0.25):
    """Canvas with a fixed width and one row of height per barcode.

    The floor only has to leave room for the axes and the labels. It used to be six
    inches, from when every figure carried all 96 rows of the kit; now that the unused
    barcodes are dropped, a three-barcode run would have spread three rows over that and
    drawn boxes two inches tall.

    `row` is the height a row gets. The quarter inch default suits a figure that draws one
    mark per barcode and nothing else; a figure writing a header line above every row asks
    for `row_metrics` instead.
    """
    return (9, max(2.5, row * nb_columns + 1.5))


def row_metrics(nb_rows):
    """Per-row height in inches and the text size that fits in it.

    For the two figures that write a line of numbers above every barcode. Past
    DENSE_ABOVE rows the header drops a size, so the row can shrink with it.
    """
    dense = nb_rows > DENSE_ABOVE
    return (ROW_HEIGHT_DENSE if dense else ROW_HEIGHT), (
        "x-small" if dense else "small"
    )


def plotted_columns(totals):
    """The barcodes worth drawing, and a note saying how many were left out.

    `rule all` expands over every barcode the kit offers, so the tables always carry all
    of them and most runs use a fraction. Drawing the rest costs most of the canvas: a
    96-barcode kit with three samples on it is 94 blank rows and three of data. They are
    dropped from the figures — never from the tables, which stay the full record — and the
    note says so, since a figure that quietly omits barcodes is worse than a crowded one.

    Barcodes that caught a read or two are dropped by the same threshold as the ones that
    caught nothing: a hundred bases is not a distribution either.
    """
    kept = [column for column in totals.index if totals[column] >= MIN_BASES_PLOTTED]
    # Nothing reached the threshold — a run that failed outright. Keep every barcode, so
    # the figure shows that rather than coming out empty.
    if not kept:
        return list(totals.index), "no barcode reached 1 kb: showing all"
    dropped = len(totals) - len(kept)
    if not dropped:
        return kept, None
    return (
        kept,
        f"{len(kept)} of {len(totals)} barcodes; {dropped} under 1 kb not shown",
    )


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


def label_and_save(columns, output, xlabel, note=None, legend=None):
    """Label the axes, tidy the frame and write the current figure out.

    The barcodes go on the y-axis and the measured quantity on the x-axis: every barcode
    then gets its own row, the labels read horizontally instead of rotated, and a 96
    barcode kit makes the figure taller rather than more crowded.

    `legend` is an optional (handles, labels) pair, for the figures that draw more than
    one series. It goes in the strip above the axes, opposite the note.

    matplotlib is imported here rather than at the top of the module, so that the scripts
    which only need the helpers above do not pay for the import.
    """
    import matplotlib.pyplot as plt
    import seaborn as sns

    ax = plt.gca()
    ax.set_yticks(range(len(columns)), barcode_labels(columns), fontsize="small")
    ax.set_ylabel("Barcode")
    ax.set_xlabel(xlabel)
    # loc="right", so a figure that already has a centred title keeps it.
    if note:
        ax.set_title(note, fontsize="small", color="#666666", loc="right")
    # A hairline grid along the value axis only, kept behind the marks.
    ax.set_axisbelow(True)
    ax.grid(visible=True, axis="x", color=GRID_COLOR, linewidth=0.6)
    ax.grid(visible=False, axis="y")
    sns.despine(ax=ax)

    # tight_layout does not account for a legend anchored outside the axes, so the strip
    # it sits in is reserved by hand — as a fraction of the height, since that height is
    # set by the number of barcodes.
    if legend:
        handles, labels = legend
        ax.legend(
            handles,
            labels,
            loc="lower left",
            bbox_to_anchor=(0, 1.02),
            ncol=len(labels),
            frameon=False,
            fontsize="small",
            borderaxespad=0,
        )
        height = plt.gcf().get_size_inches()[1]
        plt.tight_layout(rect=(0, 0, 1, 1 - 0.28 / height))
    else:
        plt.tight_layout()
    plt.savefig(output, facecolor="w", dpi=200)
    plt.close()
