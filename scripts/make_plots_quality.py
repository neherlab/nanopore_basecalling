"""Read quality plots: the distribution of the mean and of the std, per barcode."""

import argparse

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import utils


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stats_file_mean", help="the combined mean quality table")
    parser.add_argument("stats_file_std", help="the combined quality std table")
    parser.add_argument(
        "--quality-mean-plot", required=True, help="mean quality plot to write"
    )
    parser.add_argument(
        "--quality-std-plot", required=True, help="quality std plot to write"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    df_mean = pd.read_csv(args.stats_file_mean, sep="\t")
    df_std = pd.read_csv(args.stats_file_std, sep="\t")

    plt.figure(figsize=utils.figsize(len(df_mean.columns)))
    sns.violinplot(
        data=df_mean,
        orient="h",
        color=utils.SERIES_COLOR,
        linewidth=0.8,
        inner_kws=utils.INNER_KWS,
    )
    utils.label_and_save(df_mean.columns, args.quality_mean_plot, "Mean quality")

    plt.figure(figsize=utils.figsize(len(df_std.columns)))
    sns.violinplot(
        data=df_std,
        orient="h",
        color=utils.SERIES_COLOR,
        linewidth=0.8,
        inner_kws=utils.INNER_KWS,
    )
    utils.label_and_save(df_std.columns, args.quality_std_plot, "Std of quality")


if __name__ == "__main__":
    main()
