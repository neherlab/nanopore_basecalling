"""Read quality plots: the per-base Q-score distribution, and the low-quality fraction.

Both are drawn from the Q-score histogram rather than from per-read values. A per-read
mean would be misleading here — dorado caps per-base quality at Q50 and puts about half of
all bases there, so the distribution is far from symmetric and no single number stands for
it. What the figures report instead is the distribution itself, with two summaries marked
on it; see docs/results.md for what they mean.
"""

import argparse

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import utils

MEAN_LABEL = "mean Q score"
ACCURACY_LABEL = "-10 log10(avg error rate)"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "quality_hist_file", help="the combined Q-score histogram table"
    )
    parser.add_argument(
        "--quality-hist-plot", required=True, help="Q-score distribution plot to write"
    )
    parser.add_argument(
        "--low-quality-plot", required=True, help="low-quality fraction plot to write"
    )
    return parser.parse_args()


def summaries(fractions):
    """The two numbers reported next to each row, both from the histogram.

    The **mean** is the count-weighted average of the Q scores. It is what the old
    per-read figures reported, and it flatters the run: a Q score is a logarithm, so
    averaging Q scores averages logarithms, and the good bases drown out the bad ones that
    actually cost you.

    The **error-rate score** turns each Q back into the error rate it stands for, averages
    those, and converts the result back to a Q. That is the score matching how often the
    barcode is wrong, and it is the one to compare barcodes on. On real data the two sit
    about 20 points apart, the mean above.
    """
    scores = fractions.index.values
    mean = fractions.mul(scores, axis=0).sum() / fractions.sum()
    error_rate = fractions.mul(10.0 ** (-scores / 10.0), axis=0).sum()
    return mean, -10 * np.log10(error_rate)


def plot_distribution(fractions, output, note):
    """One small histogram per barcode, stacked, with the two summaries marked.

    The y-axis is shared and **not cut**. Roughly half of every barcode's bases sit on the
    basecaller's cap, and that column is drawn at its real height: it is the largest single
    fact about the distribution, and a figure that clipped it to make the rest of the shape
    bigger would be describing a run that does not exist. What the low tail loses in height
    the two reported numbers give back — they are what separates one barcode from another.
    """
    columns = list(fractions.columns)
    scores = fractions.index.values
    mean, accuracy = summaries(fractions)

    row, text_size = utils.row_metrics(len(columns))
    height = max(3.0, row * len(columns) + 1.4)
    fig, axes = plt.subplots(
        len(columns), 1, sharex=True, figsize=(9, height), squeeze=False
    )
    axes = axes[:, 0]

    # A run where every barcode was dropped leaves nothing to scale to.
    top = np.nanmax(fractions.to_numpy()) if fractions.notna().any().any() else np.nan
    ylim = float(top) * 1.05 if np.isfinite(top) else 1.0

    for ax, column in zip(axes, columns):
        ax.bar(
            scores,
            fractions[column].values,
            width=1.0,
            color=utils.SERIES_COLOR,
            linewidth=0,
        )
        for value, color, style, label in [
            (mean[column], utils.MEAN_COLOR, "--", MEAN_LABEL),
            (accuracy[column], utils.ACCURACY_COLOR, "-.", ACCURACY_LABEL),
        ]:
            if np.isfinite(value):
                ax.axvline(
                    value, color=color, linewidth=1.1, linestyle=style, label=label
                )
        ax.set_ylim(0, ylim)
        ax.set_xlim(scores[0] - 0.5, scores[-1] + 0.5)
        ax.set_yticks([])
        ax.set_ylabel(
            utils.barcode_labels([column])[0],
            rotation=0,
            ha="right",
            va="center",
            fontsize="small",
        )
        ax.set_axisbelow(True)
        ax.grid(visible=True, axis="x", color=utils.GRID_COLOR, linewidth=0.6)
        sns.despine(ax=ax, left=True)
        # The numbers go above the row rather than inside it. Inside, there is nowhere
        # they do not eventually collide with something: the cap column owns the right
        # end, and on a bad barcode the error-rate mark walks left into the space at the
        # other one.
        ax.set_title(
            f"mean Q {mean[column]:.1f}      "
            f"{ACCURACY_LABEL} {accuracy[column]:.1f}",
            loc="left",
            fontsize=text_size,
            color="#33322f",
            pad=3,
        )

    axes[-1].set_xlabel("Q score of the base")
    fig.supylabel("Barcode")
    if note:
        axes[0].set_title(note, fontsize="small", color="#666666", loc="right")

    # A strip at each end for the title and the legend, reserved by hand: tight_layout
    # does not account for either, and on a figure that is a few feet tall it would leave
    # the title sitting over the second barcode. Inches converted to the fraction of the
    # height they come to, since that height is set by the number of barcodes.
    bottom, top = 0.35 / height, 0.5 / height
    handles, labels = axes[0].get_legend_handles_labels()
    if handles:
        fig.legend(
            handles,
            labels,
            loc="lower center",
            ncol=2,
            frameon=False,
            fontsize="small",
        )
    fig.suptitle("Share of each barcode's bases per Q score", y=1 - 0.14 / height)
    fig.tight_layout(rect=(0, bottom, 1, 1 - top))
    fig.savefig(output, facecolor="w", dpi=200)
    plt.close(fig)


def main():
    args = parse_args()

    counts = pd.read_csv(args.quality_hist_file, sep="\t", index_col="q")

    # Barcodes with too few bases to have a distribution are dropped rather than drawn as
    # noise. What is left is normalised by its own total, so barcodes with very different
    # yields are still comparable.
    columns, note = utils.plotted_columns(counts.sum())
    counts = counts[columns]
    fractions = counts.div(counts.sum(), axis=1)

    plot_distribution(fractions, args.quality_hist_plot, note)

    # The same table read as one number per barcode: how much of it is below the usable
    # line. This is what to scan down when looking for a barcode that went wrong.
    # min_count matters only for a run where nothing reached the threshold and every
    # barcode is kept: without it the sum of nothing would be 0, and an unmeasured barcode
    # would draw as a flawless one.
    low = fractions.loc[: utils.LOW_QUALITY_MAX - 1].sum(min_count=1) * 100
    plt.figure(figsize=utils.figsize(len(counts.columns)))
    sns.barplot(x=low.values, y=low.index, orient="h", color=utils.SERIES_COLOR)
    plt.title(f"Bases below Q{utils.LOW_QUALITY_MAX}")
    utils.label_and_save(
        counts.columns,
        args.low_quality_plot,
        f"% of bases below Q{utils.LOW_QUALITY_MAX}",
        note=note,
    )


if __name__ == "__main__":
    main()
