# Per-barcode read statistics and the summary plots.
#
# Conda paths are relative to this file, hence the "../".


rule stats:
    message:
        "Generating stats for {input.input_file}."
    input:
        input_file=os.path.join(TMP_DIR, "barcoded/{filename}.fastq"),
    output:
        output_file=os.path.join(TMP_DIR, "stats/{filename}.tsv"),
    log:
        os.path.join(LOG_DIR, "stats/{filename}.log"),
    conda:
        "../conda_envs/nanopore_basecalling.yml"
    shell:
        """
        python snakecommands.py generate-stats {input} {output} > {log} 2>&1
        """


rule combine_stats:
    message:
        "Combining the stat files for all the barcodes."
    input:
        stat_files=expand(os.path.join(TMP_DIR, "stats/barcode_{barcode}.tsv"), barcode=BARCODES),
        stat_file_unclassified=os.path.join(TMP_DIR, "stats/unclassified.tsv"),
    output:
        output_lengths=os.path.join(STATISTICS_DIR, "lengths.tsv"),
        output_quality_mean=os.path.join(STATISTICS_DIR, "quality.tsv"),
        output_quality_std=os.path.join(STATISTICS_DIR, "quality_std.tsv"),
    log:
        os.path.join(LOG_DIR, "combine_stats.log"),
    params:
        nb_barcodes=NB_BARCODES,
        stats_dir=os.path.join(TMP_DIR, "stats"),
    conda:
        "../conda_envs/nanopore_basecalling.yml"
    shell:
        """
        python snakecommands.py combine-stats {params.stats_dir} {output.output_lengths} {output.output_quality_mean} {output.output_quality_std} {params.nb_barcodes} > {log} 2>&1
        """


rule make_plots_lengths:
    message:
        "Generating lenghts statistics plots."
    input:
        stats_file_lengths=rules.combine_stats.output.output_lengths,
    output:
        len_hist=os.path.join(STATISTICS_DIR, "len_hist.png"),
        bp_per_barcode=os.path.join(STATISTICS_DIR, "bp_per_barcode.png"),
    log:
        os.path.join(LOG_DIR, "make_plots_lengths.log"),
    conda:
        "../conda_envs/nanopore_basecalling.yml"
    shell:
        """
        python snakecommands.py make-plots-lengths {input.stats_file_lengths} {output.len_hist} {output.bp_per_barcode} > {log} 2>&1
        """


rule make_plots_quality:
    message:
        "Generating quality statistics plots."
    input:
        stats_file_quality_mean=rules.combine_stats.output.output_quality_mean,
        stats_file_quality_std=rules.combine_stats.output.output_quality_std,
    output:
        quality_mean_plot=os.path.join(STATISTICS_DIR, "quality_mean.png"),
        quality_std_plot=os.path.join(STATISTICS_DIR, "quality_std.png"),
    log:
        os.path.join(LOG_DIR, "make_plots_quality.log"),
    conda:
        "../conda_envs/nanopore_basecalling.yml"
    shell:
        """
        python snakecommands.py make-plots-quality {input.stats_file_quality_mean} {input.stats_file_quality_std} {output.quality_mean_plot} {output.quality_std_plot} > {log} 2>&1
        """
