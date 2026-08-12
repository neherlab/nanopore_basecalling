# What a run produces

Everything the pipeline writes lands in the run folder, next to the data it started from:

```
my_run/
├── raw/                    the .pod5 files you provided
├── run.yaml                yours, untouched
├── samples.tsv             yours, untouched
├── final/
│   ├── fastq/              barcode_01.fastq.gz … unclassified.fastq.gz
│   └── bam/                only with modifications: barcode_01.bam …
├── statistics/             two tables and four plots
├── log/                    one log per step, kept even if the run fails
└── basecalling.log         when it ran, with which versions and settings
```

The intermediate files are removed automatically at the end. `log/` is deliberately kept.

## The reads

`final/fastq/` holds one gzipped FASTQ per barcode of the kit, plus
`unclassified.fastq.gz` for the reads no barcode could be assigned to. Every barcode gets a
file even if it caught nothing, so a missing file means something went wrong rather than
that the barcode was unused.

`final/bam/` appears **only when modifications were called**, and those bam files are then
the real result of the run: FASTQ cannot carry the `MM`/`ML` tags, so the methylation calls
exist only in the bam. The FASTQ files are still written, without them.

## The statistics

```
statistics/
├── read_summary.tsv     one row per barcode: reads, bases, N50, the read length
│                        quantiles, and how many reads and bases fell in each length class
├── quality_hist.tsv     one row per Q score, one column per barcode: how many bases of
│                        that barcode came out at that score
├── len_hist.png         the read length distribution of each barcode, with N50 marked
├── bp_per_barcode.png   the yield of each barcode, split by read length
├── quality_hist.png     the Q-score distribution of each barcode
└── low_quality.png      the share of each barcode's bases below Q20
```

All four figures put the barcodes down the y-axis, so a 96-barcode kit makes the figure
taller rather than more crowded. **Barcodes holding fewer than 1000 bases are left out of
the figures**, with a note in the corner saying how many — an unused kit position and a
barcode that caught one stray read are noise on a plot. The two tables always carry every
barcode of the kit, so that is where to look for one that is missing from a figure.

Four numbers on the figures are worth defining, two per topic:

| | what it is |
|---|---|
| **median read** | half the reads are shorter than this |
| **N50** | half the **bases** sit in reads at least this long — the usual way to say how long a run's reads were, and typically several times the median |
| **mean Q score** | the average of the Q scores; the number dorado and older tools report |
| **-10 log10(avg error rate)** | each Q converted back to the error rate it stands for, averaged, and converted back — **this is the one that says how often the barcode is wrong** |

Quality is counted **per base**, not per read. Averaging the Q scores within a read averages
logarithms, so the good bases drown out the bad ones: on real data that reads Q43.6 where
the true accuracy is Q24.8. The two Q scores are both marked on `quality_hist.png` and
normally differ by around 20 points; only the second is a number to act on.

A run to be happy with has its yield spread evenly over the barcodes that were loaded, most
of its bases in reads over 10 kb, and a few percent of them below Q20. A fat `< 1 kb`
segment on `bp_per_barcode.png` is what degraded input DNA looks like.

## The log

`basecalling.log` records when the run happened, the dorado and pipeline versions, every
setting the three config layers came out to, and `samples.tsv` copied in below them — so the
run folder answers on its own what was sequenced and how it was called.

`log/` holds one file per step. If a step fails, snakemake prints the path to look at:

```
Error in rule basecall:
    log: my_run/log/basecall.log (check log file(s) for error details)
```
