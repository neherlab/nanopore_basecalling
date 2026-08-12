"""Per-barcode statistics for one fastq file: a length summary and the Q-score histogram.

Neither is kept per read. The lengths are reduced to the scalars the figures and the table
need — counts, N50, the quantiles a box plot is drawn from, and the split by length class —
computed **here**, where the whole barcode is in hand, so nothing downstream has to
approximate them. A per-read table was what this used to write, and since it is ragged
across barcodes it was stored as a rectangle padded to the largest one: on a real run that
came to 2.9 MB of which 1.3 % was data.

The quality is kept as a **histogram** — one count per Q score — for a different reason: a
per-read mean says nothing useful here (half the bases sit on dorado's Q50 cap, so the mean
is pulled to a number that is not the read's accuracy), and keeping every base would be
hundreds of millions of values per barcode. The histogram is 94 integers whatever the size
of the run.
"""

import argparse

import numpy as np
import utils


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reads", help="the fastq file to summarise")
    parser.add_argument(
        "--summary", required=True, help="the read length summary .tsv to write"
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


def n50(sorted_desc, total):
    """The length at which half the bases sit in reads at least that long.

    The standard nanopore length statistic, and a different number from the median read:
    it weights by base rather than by read, so a barcode whose reads are mostly short but
    whose bases are mostly long — which is the usual shape — scores far above its median.
    """
    half = np.searchsorted(np.cumsum(sorted_desc), total / 2)
    return int(sorted_desc[half])


def summarise(lengths):
    """The rows of the summary table for one barcode, in the order they are written.

    A barcode with no reads gets zeros for everything counted and **blank** quantiles: a
    zero-length read that does not exist is a worse answer than no answer, and the box
    plot has to leave the row out either way.
    """
    total = int(lengths.sum())
    rows = [("reads", len(lengths)), ("bases", total)]

    names = ["n50", "length_min", "length_p1", "length_q1"]
    names += ["length_median", "length_q3", "length_p99", "length_max"]
    if len(lengths):
        quantiles = np.percentile(lengths, [1, 25, 50, 75, 99])
        values = [n50(np.sort(lengths)[::-1], total), lengths.min()]
        values += list(np.round(quantiles))
        values.append(lengths.max())
        rows += [(name, int(value)) for name, value in zip(names, values)]
    else:
        rows += [(name, "") for name in names]

    # Read counts and base counts per class say opposite things — a fifth of the reads of
    # a good barcode are under 1 kb and carry a seventieth of its bases — so both are
    # reported rather than one standing in for the other.
    per_class = {}
    for key, _, low, high in utils.LENGTH_CLASSES:
        in_class = lengths >= low
        if high is not None:
            in_class &= lengths < high
        per_class[key] = (int(in_class.sum()), int(lengths[in_class].sum()))
    rows += [(f"reads_{key}", counted) for key, (counted, _) in per_class.items()]
    rows += [(f"bases_{key}", summed) for key, (_, summed) in per_class.items()]
    return rows


def main():
    args = parse_args()

    # One bin per printable Phred+33 character, so no Q score can fall outside it.
    counts = np.zeros(utils.NB_QSCORES, dtype=np.int64)
    lengths = []

    with open(args.reads) as reads:
        for sequence, quality in records(reads):
            lengths.append(len(sequence))
            scores = (
                np.frombuffer(quality.encode(), dtype=np.uint8) - utils.PHRED_OFFSET
            )
            counts += np.bincount(scores, minlength=utils.NB_QSCORES)

    # Held in memory rather than streamed, since the quantiles and N50 need every read of
    # the barcode at once. That is 8 bytes a read: a barcode of a real run is tens of
    # thousands, and even ten million would be 80 MB against the 4 GB the rule asks for.
    with open(args.summary, "w") as summary:
        summary.write("statistic\tvalue\n")
        summary.writelines(
            f"{name}\t{value}\n"
            for name, value in summarise(np.array(lengths, dtype=np.int64))
        )

    with open(args.quality, "w") as quality_file:
        quality_file.write("q\tcount\n")
        quality_file.writelines(f"{q}\t{count}\n" for q, count in enumerate(counts))


if __name__ == "__main__":
    main()
