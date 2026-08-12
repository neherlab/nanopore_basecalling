# The statistics and the figures

Every run writes a `statistics/` folder with two tables and four figures:

```
statistics/
├── lengths.tsv          one row per read, one column per barcode
├── quality_hist.tsv     one row per Q score, one column per barcode
├── len_hist.png         read length distribution
├── bp_per_barcode.png   total yield
├── quality_hist.png     per-base Q score distribution
└── low_quality.png      share of bases below Q20
```

The tables are the record and always carry **every** barcode of the kit, including the
ones the run never used. The figures leave those out — see [what is not
drawn](#what-is-not-drawn).

## What is measured

The `stats` step reads each barcode's fastq once and keeps two things.

**Read lengths**, one number per read. `len_hist.png` and `bp_per_barcode.png` are drawn
from these.

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

## The figures

All four are horizontal — **barcodes down the y-axis, the measured quantity across** — so
the labels read straight and a 96-barcode kit makes the figure taller rather than more
crowded. One quantity per figure means one colour for every mark; the barcode is already
given by the row, so no legend is needed.

### `len_hist.png` — read lengths

A box per barcode on a log axis. Whiskers are the 1st and 99th percentiles rather than the
usual 1.5×IQR: a barcode holds tens of thousands of reads, and the IQR rule then marks
thousands of them as outliers, which draws as a smear across the row.

```
        │
     49 │      ├──────[███████│███████]──────────────┤
     58 │   ├────────[████│████]────────┤
   uncl │        ├───────────[██████│███████]───────────┤
        └──────────────────────────────────────────────────
             10³              10⁴              10⁵
                          Length of reads
```

### `bp_per_barcode.png` — yield

One bar per barcode, total megabases. This is the figure that says whether the pooling was
even.

```
     49 │████████████████████████████████████  213
     58 │█████                                  33
   uncl │▌                                       1
        └──────────────────────────────────────────
          0        50       100       150      200
                            MBp
```

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

Nothing is dropped from `lengths.tsv` or `quality_hist.tsv`. To find out what a missing
barcode did, read the table.

If no barcode reaches 1000 bases, every one is kept and the note says so, rather than the
figures coming out empty.
