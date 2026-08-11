"""Combine the per-barcode statistics into one table per quantity.

Reads every .tsv file of the stats directory and writes three tables — lengths, mean
quality and quality std — with one column per barcode.
"""

import argparse
import os

import pandas as pd

import utils


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stats_dir", help="directory holding the per-barcode .tsv files")
    parser.add_argument("--lengths", required=True, help="read length table to write")
    parser.add_argument("--quality-mean", required=True, help="mean quality table to write")
    parser.add_argument("--quality-std", required=True, help="quality std table to write")
    parser.add_argument("--nb-barcodes", required=True, type=int, help="number of barcodes of the kit")
    return parser.parse_args()


def main():
    args = parse_args()

    file_list = [file for file in os.listdir(args.stats_dir) if file.endswith(".tsv")]
    df_lengths = pd.DataFrame()
    df_quality_mean = pd.DataFrame()
    df_quality_std = pd.DataFrame()

    # Each file contributes one column to each table, named after the file it came from.
    for file_name in file_list:
        file_path = os.path.join(args.stats_dir, file_name)
        header = os.path.splitext(file_name)[0]

        df = pd.read_table(file_path)

        df_lengths = pd.concat([df_lengths, df["length"]], axis=1)
        df_lengths = df_lengths.rename(columns={"length": header})

        df_quality_mean = pd.concat([df_quality_mean, df["mean_quality"]], axis=1)
        df_quality_mean = df_quality_mean.rename(columns={"mean_quality": header})

        df_quality_std = pd.concat([df_quality_std, df["std_quality"]], axis=1)
        df_quality_std = df_quality_std.rename(columns={"std_quality": header})

    # os.listdir gives no order, so the columns are put back into barcode order here.
    sorted_headers = utils.barcode_columns(args.nb_barcodes)

    df_lengths[sorted_headers].to_csv(args.lengths, index=False, sep="\t")
    df_quality_mean[sorted_headers].to_csv(args.quality_mean, index=False, sep="\t")
    df_quality_std[sorted_headers].to_csv(args.quality_std, index=False, sep="\t")


if __name__ == "__main__":
    main()
