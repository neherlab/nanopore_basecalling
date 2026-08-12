# The statistics and the figures

Every run writes a `statistics/` folder with two tables and four figures:

```
statistics/
├── read_summary.tsv     one row per barcode: counts, N50, quantiles, length classes
├── quality_hist.tsv     one row per Q score, one column per barcode
├── len_hist.png         read length distribution
├── bp_per_barcode.png   yield, split by read length
├── quality_hist.png     per-base Q score distribution
└── low_quality.png      share of bases below Q20
```

The tables are the record and always carry **every** barcode of the kit, including the
ones the run never used. The figures leave those out — see [what is not
drawn](#what-is-not-drawn).

## What is measured

The `stats` step reads each barcode's fastq once and keeps two things. Neither is one value
per read: everything the figures need is a summary or a histogram, and computing it while
the barcode is being read keeps the tables small however big the run gets.

**A length summary**, one row of `read_summary.tsv`:

| column | what it is |
|---|---|
| `reads`, `bases` | how many reads the barcode caught and how many bases they came to |
| `n50` | half the bases sit in reads at least this long |
| `length_min`, `length_max` | the shortest and longest read |
| `length_p1`, `length_q1`, `length_median`, `length_q3`, `length_p99` | the five numbers the box in `len_hist.png` is drawn from |
| `reads_under_1kb` … `reads_over_50kb` | how many reads fell in each length class |
| `bases_under_1kb` … `bases_over_50kb` | how many **bases** those reads came to |

The last two rows are both there because they say different things. On a good barcode about
a fifth of the reads are under 1 kb and they carry about a seventieth of the bases — counting
reads makes a run look short, counting bases makes it look long, and only having both tells
you which.

**A Q-score histogram**, one count per Q score — how many bases in this barcode came out at
Q0, at Q1, and so on. Not a value per read: the quality figures are drawn from this.

### Why per base and not per read

A read has no single quality. The old version of this pipeline averaged the Phred scores
within each read and plotted the mean and standard deviation of that, which was wrong twice
over:

- **The average was not the read's accuracy.** A Q score is a logarithm of an error
  probability, so averaging Q scores averages logarithms, and the good bases drown out the
  bad ones. On real data the figure read **Q43.6** where the true accuracy was **Q24.8** —
  an overstatement of about 19 Q points, which is three orders of magnitude in error rate.
- **A mean and a standard deviation do not describe this distribution.** Dorado caps
  per-base quality at Q50 and puts about half of all bases there, with a second hump around
  Q36–45 and a long thin tail below. Nothing symmetric fits that.

Keeping counts rather than values costs nothing: a barcode's histogram is 94 integers
whatever the size of the run, so `quality_hist.tsv` is a few kB where the per-read table it
replaced was a few MB.

The lengths went the same way for a different reason. A per-read length table is ragged —
one barcode gets ten times the reads of another — and stored as a rectangle it is padded out
to the largest column. On a real run that came to 2.9 MB of which 1.3 % was data. Every
number the figures need is computed in the same pass instead, exactly, so `read_summary.tsv`
is a few kB and nothing is approximated.

## The figures

All four are horizontal — **barcodes down the y-axis, the measured quantity across** — so
the labels read straight and a 96-barcode kit makes the figure taller rather than more
crowded. One quantity per figure means one colour for every mark; the barcode is already
given by the row, so no legend is needed.

### `len_hist.png` — read lengths

A box per barcode on a log axis, with **N50** marked in red and the read count and N50
written above the row. Whiskers are the 1st and 99th percentiles rather than the usual
1.5×IQR: a barcode holds tens of thousands of reads, and the IQR rule then marks thousands
of them as outliers, which draws as a smear across the row.

```
  reads 27,981    N50 16,077
     49 │      ├──────[███████│███████]────┊─────────┤
                                           ┊
  reads 6,558     N50 9,571
     58 │   ├────────[████│████]───┊────────┤
                                  ┊
  reads 135       N50 16,456
   uncl │      ├──────────[██████│███████]──┊─────────┤
        └──────────────────────────────────────────────────
             10³              10⁴              10⁵
                          Length of reads
```

The line inside the box is the **median read** and the red mark is **N50**. They are two
different questions and usually two very different numbers — see [N50 and the
median](#n50-and-the-median).

### `bp_per_barcode.png` — yield, split by read length

One bar per barcode, total megabases, divided into the length classes those bases came from.
The length of the bar says whether the pooling was even; the split says whether a barcode
that got its share got it in reads worth having.

```
        │ ░ < 1 kb   ▒ 1–10 kb   ▓ 10–50 kb   █ > 50 kb
     49 │░▒▒▒▒▒▒▒▒▒▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓██  213
     58 │░▒▒▒▒▒▒▒▓▓▓▓▓▓▓                             33
   uncl │▓                                            1
        └──────────────────────────────────────────────
          0        50       100       150      200
                            MBp
```

Both of those barcodes are usable, and they are not the same library: barcode 49 has 64 % of
its bases in reads over 10 kb against barcode 58's 47 %. A bar carrying only the total said
nothing about that. A fat `< 1 kb` segment is the shape to be suspicious of — it is what
degraded input DNA looks like.

### `quality_hist.png` — the Q-score distribution

One small histogram per barcode: Q score across, share of that barcode's bases as the bar
height, with two summary lines marked and their values written above the row.

```
   mean Q 43.4      -10 log10(avg error rate) 22.4
                            ┊                    ╎   █
     49 ├────────────────────────────────────▁▂▃▃▂▁──█
                            ┊                    ╎   █
   mean Q 38.3      -10 log10(avg error rate) 16.5
                    ┊                     ╎          █
   uncl ├────▁▃▄▃▂▁▁─────────────────────▂▃▄▃▂▁──────█
        └──────────────────────────────────────────────
        0        10        20        30        40    50
                       Q score of the base
                 ╎ mean Q score    ┊ -10 log10(avg error rate)
```

**The y-axis is shared across rows and is not cut.** Roughly half of every barcode's bases
sit on the Q50 cap, and that column is drawn at its real height. It dominates the figure
because it dominates the data; clipping it would make the rest of the shape bigger at the
cost of describing a run that does not exist. The rows being on one scale is what lets you
compare them — a barcode with a shorter cap column and a fatter low tail is a worse barcode,
and you can see that directly.

The consequence is that the low tail is a thin line rather than a shape. The two numbers
above each row are what carry the comparison instead.

### `low_quality.png` — the share below Q20

One bar per barcode: the percentage of its bases under Q20, which is one error in a hundred
and the conventional line between usable and not. This is the figure to scan down a
96-barcode column when looking for the barcode that went wrong.

```
     49 │████▌                    4.5 %
     58 │████▋                    4.7 %
   uncl │███████████████         15.3 %
        └────────────────────────────────
          0     5     10    15    20
              % of bases below Q20
```

## N50 and the median

Both are lengths in bases, and they answer different questions:

| | what it is | what it is good for |
|---|---|---|
| **median read** | half the reads are shorter than this | how long a typical read is |
| **N50** | half the **bases** sit in reads at least this long | how long the reads carrying your data are |

N50 is the one quoted when someone asks how long a nanopore run's reads were, and it is
almost always the larger of the two — long reads carry many more bases each, so they weigh
more when you count by base than when you count by read. On the cluster test run:

| barcode | median read | N50 |
|---|---|---|
| barcode_49 | 3 958 | 16 077 |
| barcode_58 | 3 055 | 9 571 |
| unclassified | 4 862 | 16 456 |

A factor of four between them is normal and not a problem. What is worth looking at is a
barcode whose N50 is much lower than the others on the same run, or one where the two
numbers are close — that means there are no long reads for the base count to be weighted
towards.

## The two numbers on each row

Both come from the same histogram and both are Q scores, so they are directly comparable —
but they say different things and usually differ by about 20 points.

| | what it is | what it is good for |
|---|---|---|
| **mean Q score** | the count-weighted average of the Q scores | comparing against the number dorado and older tools report |
| **-10 log10(avg error rate)** | each Q converted back to the error rate it stands for, averaged, converted back to a Q | how often this barcode is actually wrong |

The second is the one to act on. Converting each score back to an error probability before
averaging is what makes the arithmetic honest: a base at Q10 is wrong once in ten, a base at
Q50 once in a hundred thousand, and averaging the *scores* treats a step from Q10 to Q20 as
the same size as one from Q40 to Q50 when it is a thousand times more consequential.

On the cluster test run the two came out as:

| barcode | mean Q score | -10 log10(avg error rate) |
|---|---|---|
| barcode_49 | 43.4 | 22.4 |
| barcode_58 | 43.5 | 22.0 |
| unclassified | 38.3 | 16.5 |

The mean separates the barcodes by 5 points and the error-rate score by 6, but only the
second is a number you can turn into an expected error count.

## What is not drawn

`rule all` expands over every barcode the kit offers, so a 96-barcode kit run with three
samples on it would otherwise be 94 blank rows and three of data.

**Barcodes holding fewer than 1000 bases are left out of all four figures**, and a note in
the top right corner says how many. The threshold catches two cases at once: barcodes that
caught nothing, and the cross-talk barcodes that caught one stray read — typically around a
hundred bases, which is not a distribution. Normalising a hundred bases per barcode would
make counting noise as loud as a real result, and those rows were the brightest thing on the
figure before the threshold existed.

Nothing is dropped from `read_summary.tsv` or `quality_hist.tsv`. To find out what a missing
barcode did, read the table.

If no barcode reaches 1000 bases, every one is kept and the note says so, rather than the
figures coming out empty.
