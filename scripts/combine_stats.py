"""Combine the per-barcode statistics into one table per quantity.

Reads the two directories the stats step fills — one .tsv per barcode in each — and writes
the read length summary and the Q-score histogram.
"""

import argparse
import os

import pandas as pd
import utils


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "summary_dir", help="directory holding the per-barcode length summaries"
    )
    parser.add_argument(
        "quality_dir", help="directory holding the per-barcode Q-score histograms"
    )
    parser.add_argument("--summary", required=True, help="read summary table to write")
    parser.add_argument(
        "--quality-hist", required=True, help="Q-score histogram table to write"
    )
    parser.add_argument(
        "--nb-barcodes", required=True, type=int, help="number of barcodes of the kit"
    )
    return parser.parse_args()


def read_columns(directory, column, index=None):
    """One column per .tsv file of a directory, named after the file it came from.

    `index` names the column to index the rows by, so that the tables are lined up on the
    Q score rather than on the order the rows happen to be in.
    """
    columns = {}
    for file_name in os.listdir(directory):
        if not file_name.endswith(".tsv"):
            continue
        header = os.path.splitext(file_name)[0]
        table = pd.read_table(os.path.join(directory, file_name), index_col=index)
        columns[header] = table[column]
    return pd.DataFrame(columns)


def main():
    args = parse_args()

    # os.listdir gives no order, so the columns are put back into barcode order here.
    sorted_headers = utils.barcode_columns(args.nb_barcodes)

    # Transposed relative to the histogram below: one row per barcode and one column per
    # statistic. That is the shape you scan looking for the barcode that went wrong, and
    # the shape samples.tsv already has.
    # Every statistic is a count or a length, so the table is integer throughout. The cast
    # is to pandas' nullable integer: a barcode with no reads leaves its quantiles blank,
    # and plain numpy would turn the whole column to float and write "27981.0".
    summary = read_columns(args.summary_dir, "value", index="statistic")
    summary = summary[sorted_headers].astype("Int64")
    summary.T.to_csv(args.summary, sep="\t", index_label="barcode")

    # Every histogram covers the same Q scores, so the counts line up on the score. Scores
    # no barcode reached are dropped off the end, which leaves the table ending at the
    # basecaller's cap rather than at the last character fastq can encode. A run with no
    # reads at all has nothing to trim to, and keeps the full range.
    quality = read_columns(args.quality_dir, "count", index="q")[sorted_headers]
    reached = quality.index[quality.sum(axis=1) > 0]
    if len(reached):
        quality = quality.loc[: reached.max()]
    quality.to_csv(args.quality_hist, sep="\t")


if __name__ == "__main__":
    main()
