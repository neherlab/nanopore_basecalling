"""Per-read statistics for one fastq file: length, mean quality and quality std."""

import argparse

import numpy as np
from Bio import SeqIO


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reads", help="the fastq file to summarise")
    parser.add_argument("--output", required=True, help="the .tsv file to write")
    return parser.parse_args()


def main():
    args = parse_args()

    with open(args.reads, "r") as f, open(args.output, "w") as file:
        file.write("length\tmean_quality\tstd_quality\n")
        for record in SeqIO.parse(f, "fastq"):
            length = len(record)
            mean_quality = np.mean(record.letter_annotations["phred_quality"])
            std_quality = np.std(record.letter_annotations["phred_quality"])
            file.write(f"{length}\t{mean_quality}\t{std_quality}\n")


if __name__ == "__main__":
    main()
