# Pipeline to basecall the raw data generated from our nanopore, with modified bases.
# Configuration and the rules shared with the Snakefile live in common.smk.


include: "common.smk"


# Modified-base model. Its version is tied to the basecalling model in the config file,
# so the two have to be changed together.
DORADO_MODS = config["mods_model"]
MODS_PATH = os.path.join(DORADO_MODELS_DIR, DORADO_MODS)


rule all:
    input:
        barcodes=expand(OUTPUT_DIR + "/fastq_files/barcode_{barcode}.fastq.gz", barcode=BARCODES),
        unclassified=OUTPUT_DIR + "/fastq_files/unclassified.fastq.gz",
        plot1=STATISTICS_DIR + "/len_hist.png",
        plot2=STATISTICS_DIR + "/bp_per_barcode.png",
        plot3=STATISTICS_DIR + "/quality_mean.png",
        plot4=STATISTICS_DIR + "/quality_std.png",
        clean=DATA_DIR + "/.cleaned_dummy_file.txt",  # comment for debugging
    default_target: True


rule basecall:
    message:
        "Basecalling the reads using Dorado model {params.model} for the kit {params.kit}."
    input:
        input_dir=INPUT_DIR,
        logfile=LOGFILE,
        model=MODEL_PATH,
        mods=MODS_PATH,
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
        {params.dorado} basecaller {input.model} {input.input_dir} --modified-bases-models {input.mods} --kit-name {params.kit} > {output.file}
        """


rule demultiplex:
    message:
        "Splitting the reads based on detected barcodes, and removing the barcodes from the reads."
    input:
        rules.basecall.output.file,
    output:
        directory=directory(OUTPUT_DIR + "/bam_files"),
        barcodes=expand(OUTPUT_DIR + "/bam_files/barcode_{barcode}.bam", barcode=BARCODES),
        unclassified=OUTPUT_DIR + "/bam_files/unclassified.bam",
    conda:
        "conda_envs/nanopore_basecalling.yml"
    params:
        dorado=DORADO_BIN,
        kit=NANOPORE_KIT,
    threads: 4
    shell:
        """
        mkdir -p {output.directory}
        {params.dorado} demux --output-dir {output.directory} --no-classify {input} -t {threads}
        cd {output.directory}
        shopt -s nullglob
        demuxed=({params.kit}_barcode*.bam)
        if [ ${{#demuxed[@]}} -eq 0 ]; then
            echo "ERROR: dorado demux produced no {params.kit}_barcode*.bam files in $(pwd)." >&2
            echo "Its output layout has probably changed; the rename below would silently" >&2
            echo "leave every barcode empty. Found instead:" >&2
            ls -la >&2
            exit 1
        fi
        for file in "${{demuxed[@]}}"; do mv "$file" "${{file/{params.kit}_barcode/barcode_}}"; done
        for bc in {BARCODES}; do
            if ! [[ -e barcode_$bc.bam ]]; then
                touch barcode_$bc.bam
            fi
        done
        """


rule convert:
    message:
        "Converting the file {input.bam} file to .fastq format."
    input:
        bam=OUTPUT_DIR + "/bam_files/{filename}.bam",
    output:
        fastq=TMP_DIR + "/barcoded/{filename}.fastq",
    conda:
        "conda_envs/nanopore_basecalling.yml"
    shell:
        """
        samtools bam2fq {input.bam} > {output.fastq}
        """


rule compress:
    message:
        "Generating the final compressed file {output.output_file}."
    input:
        input_file=TMP_DIR + "/barcoded/{filename}.fastq",
    output:
        output_file=OUTPUT_DIR + "/fastq_files/{filename}.fastq.gz",
    conda:
        "conda_envs/nanopore_basecalling.yml"
    shell:
        """
        gzip -c {input} > {output}
        """
