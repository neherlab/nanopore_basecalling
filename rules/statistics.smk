# Per-barcode read statistics and the summary plots.
#
# Conda paths are relative to this file, hence the "../".


# The two tables go to two directories rather than two files side by side, so that
# combine_stats can keep naming each column after the file it came from.
rule stats:
    message:
        "Generating stats for {input.input_file}."
    input:
        input_file=os.path.join(TMP_DIR, "barcoded/{filename}.fastq"),
    output:
        summary=os.path.join(TMP_DIR, "stats/summary/{filename}.tsv"),
        quality=os.path.join(TMP_DIR, "stats/quality/{filename}.tsv"),
    log:
        os.path.join(LOG_DIR, "stats/{filename}.log"),
    conda:
        "../conda_envs/nanopore_basecalling.yml"
    shell:
        """
        python scripts/generate_stats.py {input.input_file} \
        --summary {output.summary} \
        --quality {output.quality} > {log} 2>&1
        """


rule combine_stats:
    message:
        "Combining the stat files for all the barcodes."
    input:
        stat_files=expand(rules.stats.output, filename=["barcode_" + bc for bc in BARCODES]),
        stat_file_unclassified=expand(rules.stats.output, filename="unclassified"),
    output:
        output_summary=os.path.join(STATISTICS_DIR, "read_summary.tsv"),
        output_quality_hist=os.path.join(STATISTICS_DIR, "quality_hist.tsv"),
    log:
        os.path.join(LOG_DIR, "combine_stats.log"),
    params:
        nb_barcodes=NB_BARCODES,
        summary_dir=os.path.join(TMP_DIR, "stats/summary"),
        quality_dir=os.path.join(TMP_DIR, "stats/quality"),
    conda:
        "../conda_envs/nanopore_basecalling.yml"
    shell:
        """
        python scripts/combine_stats.py {params.summary_dir} {params.quality_dir} \
        --summary {output.output_summary} \
        --quality-hist {output.output_quality_hist} \
        --nb-barcodes {params.nb_barcodes} > {log} 2>&1
        """


rule make_plots_lengths:
    message:
        "Generating lenghts statistics plots."
    input:
        stats_file_summary=rules.combine_stats.output.output_summary,
    output:
        len_hist=os.path.join(STATISTICS_DIR, "len_hist.png"),
        bp_per_barcode=os.path.join(STATISTICS_DIR, "bp_per_barcode.png"),
    log:
        os.path.join(LOG_DIR, "make_plots_lengths.log"),
    conda:
        "../conda_envs/nanopore_basecalling.yml"
    shell:
        """
        python scripts/make_plots_lengths.py {input.stats_file_summary} \
        --len-hist {output.len_hist} \
        --bp-per-barcode {output.bp_per_barcode} > {log} 2>&1
        """


rule make_plots_quality:
    message:
        "Generating quality statistics plots."
    input:
        stats_file_quality_hist=rules.combine_stats.output.output_quality_hist,
    output:
        quality_hist_plot=os.path.join(STATISTICS_DIR, "quality_hist.png"),
        low_quality_plot=os.path.join(STATISTICS_DIR, "low_quality.png"),
    log:
        os.path.join(LOG_DIR, "make_plots_quality.log"),
    conda:
        "../conda_envs/nanopore_basecalling.yml"
    shell:
        """
        python scripts/make_plots_quality.py {input.stats_file_quality_hist} \
        --quality-hist-plot {output.quality_hist_plot} \
        --low-quality-plot {output.low_quality_plot} > {log} 2>&1
        """
