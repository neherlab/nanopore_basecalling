"""Read length plots: the distribution per barcode, and the yield split by read length.

Both are drawn from the summary table rather than from per-read lengths — the quantiles a
box needs and the per-class base counts are computed in the stats step, where the whole
barcode is in hand, so nothing here approximates anything.
"""

import argparse

import matplotlib.pyplot as plt
import pandas as pd
import utils

N50_LABEL = "N50"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary_file", help="the combined read summary table")
    parser.add_argument(
        "--len-hist", required=True, help="length distribution plot to write"
    )
    parser.add_argument(
        "--bp-per-barcode", required=True, help="total basepairs plot to write"
    )
    return parser.parse_args()


def plot_distribution(summary, output, note):
    """A box per barcode on a log axis, with N50 marked and the numbers above the row.

    The box is the read-weighted view — half the reads are shorter than the median — and
    N50 is the base-weighted one, the length at which half the bases sit in reads at least
    that long. They are not close: on real data the median is 4 kb where N50 is 16 kb, and
    N50 is the one that says whether the library is any good.

    The numbers go above the row rather than inside it. Inside, the box occupies the
    middle and the whiskers the ends, so there is no reliable free space at either.
    """
    columns = list(summary.index)
    row, text_size = utils.row_metrics(len(columns))

    # A barcode with no reads has no quantiles to draw a box from. That only survives the
    # drop in a run where nothing reached the threshold and every barcode was kept.
    drawn = [column for column in columns if summary.loc[column, "reads"] > 0]
    boxes = [
        {key: summary.loc[column, name] for key, name in utils.BOX_STATISTICS.items()}
        for column in drawn
    ]

    plt.figure(figsize=utils.figsize(len(columns), row=row))
    ax = plt.gca()
    if boxes:
        ax.bxp(
            boxes,
            positions=[columns.index(column) for column in drawn],
            orientation="horizontal",
            manage_ticks=False,
            **utils.BOX_KWS,
        )
    ax.set_xscale("log")
    ax.set_ylim(len(columns) - 0.5, -0.5)

    for position, column in enumerate(columns):
        reads = int(summary.loc[column, "reads"])
        header = [(0.004, f"reads {reads:,}", "#33322f")]
        if reads > 0:
            n50 = int(summary.loc[column, "n50"])
            ax.plot(
                [n50, n50],
                [position - 0.35, position + 0.35],
                color=utils.N50_COLOR,
                linewidth=1.3,
            )
            # Written in the colour of the mark rather than explained in a legend: the
            # figure then needs no strip of its own, which is what the row headers had
            # already taken.
            header.append((0.15, f"{N50_LABEL} {n50:,}", utils.N50_COLOR))
        # x in axes coordinates, y in data coordinates, so the header sits at the left
        # edge of its own row whatever the axis limits come out to.
        for offset, text, color in header:
            ax.text(
                offset,
                position - 0.42,
                text,
                transform=ax.get_yaxis_transform(),
                fontsize=text_size,
                color=color,
                va="bottom",
            )

    utils.label_and_save(columns, output, "Length of reads", note=note)


def plot_yield(summary, output, note):
    "One bar per barcode, total megabases. Says whether the pooling was even."
    columns = list(summary.index)
    values = summary["bases"].astype(float) / 1e6
    plt.figure(figsize=utils.figsize(len(columns)))
    plt.gca().barh(
        range(len(columns)), values, height=0.65, color=utils.SERIES_COLOR, linewidth=0
    )
    plt.gca().set_ylim(len(columns) - 0.5, -0.5)
    utils.label_and_save(columns, output, "MBp", note=note)


def main():
    args = parse_args()

    summary = pd.read_csv(args.summary_file, sep="\t", index_col="barcode")

    # The barcodes the kit offered and the run did not use are left out of the figures.
    columns, note = utils.plotted_columns(summary["bases"])
    summary = summary.loc[columns]

    plot_distribution(summary, args.len_hist, note)
    plot_yield(summary, args.bp_per_barcode, note)


if __name__ == "__main__":
    main()
