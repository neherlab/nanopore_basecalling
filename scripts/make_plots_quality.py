"""Read quality plots: the per-base Q-score distribution, and the low-quality fraction.

Both are drawn from the Q-score histogram rather than from per-read values. A per-read mean
would be misleading here — dorado caps per-base quality at Q50 and puts about half of all
bases there, so the distribution is far from symmetric and no single number stands for it.
"""

import argparse

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import utils
from matplotlib.colors import PowerNorm


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


def main():
    args = parse_args()

    counts = pd.read_csv(args.quality_hist_file, sep="\t", index_col="q")

    # Barcodes with too few bases to have a distribution are dropped rather than drawn as
    # noise. What is left is normalised by its own total, so barcodes with very different
    # yields are still comparable.
    columns, note = utils.plotted_columns(counts.sum())
    counts = counts[columns]
    fractions = counts.div(counts.sum(), axis=1)

    # Q score on the x-axis, barcodes on the y-axis, colour for the density. Cell centres
    # sit at 0..n-1 so that label_and_save can put the barcode names on the rows the same
    # way it does for every other figure.
    q_edges = list(counts.index - 0.5) + [counts.index[-1] + 0.5]
    barcode_edges = [ii - 0.5 for ii in range(len(counts.columns) + 1)]

    plt.figure(figsize=utils.figsize(len(counts.columns)))
    mesh = plt.pcolormesh(
        q_edges,
        barcode_edges,
        fractions.T,
        cmap=utils.density_colormap(),
        norm=PowerNorm(gamma=utils.QSCORE_GAMMA, vmin=0, vmax=utils.QSCORE_VMAX),
    )
    # pcolormesh counts y upwards, seaborn's categorical axis counts it downwards. Invert
    # so this figure lists the barcodes in the same order as all the others.
    plt.gca().invert_yaxis()
    bar = plt.colorbar(mesh, ax=plt.gca(), pad=0.02, fraction=0.04)
    bar.set_label("Fraction of the barcode's bases")
    # The scale stops well below the tallest bin, so the top tick says so rather than
    # claiming the colour means exactly 3%.
    bar.set_ticks([0, 0.005, 0.01, 0.02, utils.QSCORE_VMAX])
    bar.set_ticklabels(["0", "0.5%", "1%", "2%", f"≥{utils.QSCORE_VMAX:.0%}"])
    utils.label_and_save(
        counts.columns, args.quality_hist_plot, "Q score of the base", note=note
    )

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
