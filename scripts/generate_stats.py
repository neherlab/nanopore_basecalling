"""Per-barcode statistics for one fastq file: the read lengths and the Q-score histogram.

The lengths are kept one per read, since the length distribution is drawn from them. The
quality is kept as a **histogram** — one count per Q score — rather than one value per read:
a per-read mean says nothing useful here (half the bases sit on dorado's Q50 cap, so the
mean is pulled to a number that is not the read's accuracy), and keeping every base would
be hundreds of millions of values per barcode. The histogram is 94 integers whatever the
size of the run.
"""

import argparse

import numpy as np
import utils


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reads", help="the fastq file to summarise")
    parser.add_argument(
        "--lengths", required=True, help="the read length .tsv to write"
    )
    parser.add_argument(
        "--quality", required=True, help="the Q-score histogram .tsv to write"
    )
    return parser.parse_args()


def records(handle):
    """Yield (sequence, quality) for each record of a four-line-per-record fastq.

    `samtools bam2fq`, which writes the files this reads, always emits four lines per
    record, so there is no need for a general parser. The '+' check is there so that a
    file which is *not* in that shape fails loudly rather than silently pairing the wrong
    lines together.
    """
    while True:
        header = handle.readline()
        if not header:
            return
        # rstrip() rather than rstrip("\n"): no valid Phred+33 character is whitespace,
        # so this also copes with a file that picked up CRLF line endings.
        sequence = handle.readline().rstrip()
        separator = handle.readline()
        quality = handle.readline().rstrip()
        if not separator.startswith("+"):
            raise ValueError(
                f"{handle.name} is not a four-line-per-record fastq: expected '+' on the "
                f"third line of a record, found {separator[:20]!r}."
            )
        yield sequence, quality


def main():
    args = parse_args()

    # One bin per printable Phred+33 character, so no Q score can fall outside it.
    counts = np.zeros(utils.NB_QSCORES, dtype=np.int64)

    with open(args.reads) as reads, open(args.lengths, "w") as lengths:
        lengths.write("length\n")
        for sequence, quality in records(reads):
            lengths.write(f"{len(sequence)}\n")
            scores = (
                np.frombuffer(quality.encode(), dtype=np.uint8) - utils.PHRED_OFFSET
            )
            counts += np.bincount(scores, minlength=utils.NB_QSCORES)

    with open(args.quality, "w") as quality_file:
        quality_file.write("q\tcount\n")
        for q, count in enumerate(counts):
            quality_file.write(f"{q}\t{count}\n")


if __name__ == "__main__":
    main()
