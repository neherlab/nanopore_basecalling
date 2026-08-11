"""Read length plots: the distribution per barcode and the total yield per barcode."""

import argparse

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import utils


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stats_file", help="the combined read length table")
    parser.add_argument(
        "--len-hist", required=True, help="length distribution plot to write"
    )
    parser.add_argument(
        "--bp-per-barcode", required=True, help="total basepairs plot to write"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    df = pd.read_csv(args.stats_file, sep="\t")

    # log-length distribution by barcode
    plt.figure(figsize=utils.figsize(len(df.columns)))
    sns.boxplot(
        data=df,
        orient="h",
        log_scale=True,
        color=utils.SERIES_COLOR,
        **utils.BOX_KWS,
    )
    utils.label_and_save(df.columns, args.len_hist, "Length of reads")

    # total number of basepairs per barcode
    sum_values = df.sum() / 1e6
    plt.figure(figsize=utils.figsize(len(df.columns)))
    sns.barplot(
        x=sum_values.values, y=sum_values.index, orient="h", color=utils.SERIES_COLOR
    )
    plt.title("Number of basepairs for each barcode")
    utils.label_and_save(df.columns, args.bp_per_barcode, "MBp")


if __name__ == "__main__":
    main()
