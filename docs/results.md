# What a run produces

Everything the pipeline writes lands in the run folder, next to the data it started from:

```
my_run/
├── raw/                    input .pod5 files
├── run.yaml                run config
├── samples.tsv             sample information
├── final/
│   ├── fastq/              barcode_01.fastq.gz … unclassified.fastq.gz
│   └── bam/                only with modifications: barcode_01.bam …
├── statistics/             tables and plots with quality statistics
├── log/                    logs of each job
└── basecalling.log         general log of the run, with versions and settings
```

The intermediate files are removed automatically at the end. `log/` is deliberately kept.

## The reads

`final/fastq/` holds one gzipped FASTQ per barcode of the kit, plus
`unclassified.fastq.gz` for the reads no barcode could be assigned to. Every barcode gets a
file even if it caught nothing, so a missing file means something went wrong rather than
that the barcode was unused.

`final/bam/` appears **only when modifications were called**, and contains the methylation information in the `MM` and `ML` tags. The `final/fastq/` output is still produced, but it does not contain any modification information.

## The statistics

```
statistics/
├── read_summary.tsv     per barcode: reads, bases, N50, read lengths...
├── quality_hist.tsv     per barcode: how many bases of each Q score
├── len_hist.png         the read length distribution of each barcode, with N50 marked
├── bp_per_barcode.png   the yield of each barcode, split by read length
├── quality_hist.png     the Q-score distribution of each barcode
└── low_quality.png      the share of each barcode's bases below Q20
```

Barcodes holding fewer than 1000 bases are left out of the figures.

Numbers on the figures worth defining:

|                               | what it is                                                                                                                                                      |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **median read**               | half the reads are shorter than this                                                                                                                            |
| **N50**                       | half the **bases** sit in reads at least this long — the usual way to say how long a run's reads were, and typically several times the median                   |
| **mean Q score**              | the average of the Q scores; the number dorado and older tools report                                                                                           |
| **-10 log10(avg error rate)** | each Q converted back to the error rate it stands for, averaged, and converted back. It measures the effective error rate if no quality filtering is performed. |

## The log

`basecalling.log` records when the run happened, the dorado and pipeline versions, every
setting the three config layers came out to, and `samples.tsv` copied in below them — so the
run folder answers on its own what was sequenced and how it was called.

`log/` holds one file per step. If a step fails, snakemake prints the path to look at:

```
Error in rule basecall:
    log: my_run/log/basecall.log (check log file(s) for error details)
```
