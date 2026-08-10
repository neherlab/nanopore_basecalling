# Pipeline to basecall the raw data generated from our nanopore.
# Configuration and the rules shared with methylation.smk live in common.smk.


include: "common.smk"


rule all:
    input:
        barcodes=expand(os.path.join(OUTPUT_DIR, "barcode_{barcode}.fastq.gz"), barcode=BARCODES),
        unclassified=os.path.join(OUTPUT_DIR, "unclassified.fastq.gz"),
        plot1=os.path.join(STATISTICS_DIR, "len_hist.png"),
        plot2=os.path.join(STATISTICS_DIR, "bp_per_barcode.png"),
        plot3=os.path.join(STATISTICS_DIR, "quality_mean.png"),
        plot4=os.path.join(STATISTICS_DIR, "quality_std.png"),
        clean=os.path.join(DATA_DIR, ".cleaned_dummy_file.txt"),  # comment for debugging
    default_target: True


rule basecall:
    message:
        "Basecalling the reads using Dorado model {params.model} for the kit {params.kit}."
    input:
        input_dir=INPUT_DIR,
        logfile=LOGFILE,
        model=MODEL_PATH,
    output:
        file=TMP_DIR + "/dorado_raw/basecalled.bam",
    log:
        LOG_DIR + "/basecall.log",
    conda:
        "conda_envs/nanopore_basecalling.yml"
    params:
        kit=NANOPORE_KIT,
        model=DORADO_MODEL,
        dorado=DORADO_BIN,
    shell:
        """
        {params.dorado} basecaller {input.model} {input.input_dir} --kit-name {params.kit} > {output.file} 2> {log}
        """


rule demultiplex:
    message:
        "Splitting the reads based on detected barcodes, and removing the barcodes from the reads."
    input:
        rules.basecall.output.file,
    output:
        directory=directory(TMP_DIR + "/barcoded"),
        barcodes=expand(TMP_DIR + "/barcoded/barcode_{barcode}.fastq", barcode=BARCODES),
        unclassified=TMP_DIR + "/barcoded/unclassified.fastq",
    log:
        LOG_DIR + "/demultiplex.log",
    conda:
        "conda_envs/nanopore_basecalling.yml"
    params:
        dorado=DORADO_BIN,
    threads: 4
    shell:
        """
        # opened before the cd below, so the path stays relative to the workdir
        exec > {log} 2>&1
        mkdir -p {output.directory}
        {params.dorado} demux --output-dir {output.directory}/minknow --no-classify {input} -t {threads} --emit-fastq
        cd {output.directory}

        # Since v1.2 dorado writes a nested MinKNOW tree rather than flat per-barcode files:
        #   <root>/<position>/<sample>/<run>/fastq_pass/<barcodeNN>/<prefix>_..._<n>.fastq
        # A single barcode can be spread over several files, so collapse each barcode into
        # one flat file, and create an empty one for every barcode that got no reads.
        found=0
        for bc in {BARCODES}; do
            mapfile -t files < <(find minknow -type f -name '*.fastq' -path "*/barcode$bc/*" | sort)
            if [ ${{#files[@]}} -gt 0 ]; then
                cat "${{files[@]}}" > barcode_$bc.fastq
                found=1
            else
                : > barcode_$bc.fastq
            fi
        done

        mapfile -t unclassified < <(find minknow -type f -name '*.fastq' -path '*/unclassified/*' | sort)
        if [ ${{#unclassified[@]}} -gt 0 ]; then
            cat "${{unclassified[@]}}" > unclassified.fastq
        else
            : > unclassified.fastq
        fi

        if [ $found -eq 0 ]; then
            echo "ERROR: dorado demux produced no per-barcode fastq files under $(pwd)/minknow." >&2
            echo "Its output layout has probably changed again. Found instead:" >&2
            find minknow >&2
            exit 1
        fi
        rm -rf minknow
        """


rule compress:
    message:
        "Generating the final compressed file {output.output_file}."
    input:
        input_file=TMP_DIR + "/barcoded/{filename}.fastq",
    output:
        output_file=OUTPUT_DIR + "/{filename}.fastq.gz",
    conda:
        "conda_envs/nanopore_basecalling.yml"
    shell:
        """
        gzip -c {input} > {output}
        """
