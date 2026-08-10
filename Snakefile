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
        directory=directory(TMP_DIR + "/dorado_raw"),
        file=TMP_DIR + "/dorado_raw/basecalled.bam",
    conda:
        "conda_envs/nanopore_basecalling.yml"
    params:
        kit=NANOPORE_KIT,
        model=DORADO_MODEL,
        dorado=DORADO_BIN,
    shell:
        """
        {params.dorado} basecaller {input.model} {input.input_dir} --kit-name {params.kit} > {output.file}
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
    conda:
        "conda_envs/nanopore_basecalling.yml"
    params:
        dorado=DORADO_BIN,
        kit=NANOPORE_KIT,
    threads: 4
    shell:
        """
        mkdir -p {output.directory}
        {params.dorado} demux --output-dir {output.directory} --no-classify {input} -t {threads} --emit-fastq
        cd {output.directory}
        shopt -s nullglob
        demuxed=({params.kit}_barcode*.fastq)
        if [ ${{#demuxed[@]}} -eq 0 ]; then
            echo "ERROR: dorado demux produced no {params.kit}_barcode*.fastq files in $(pwd)." >&2
            echo "Its output layout has probably changed; the rename below would silently" >&2
            echo "leave every barcode empty. Found instead:" >&2
            ls -la >&2
            exit 1
        fi
        for file in "${{demuxed[@]}}"; do mv "$file" "${{file/{params.kit}_barcode/barcode_}}"; done
        for bc in {BARCODES}; do
            if ! [[ -e barcode_$bc.fastq ]]; then
                touch barcode_$bc.fastq
            fi
        done
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
