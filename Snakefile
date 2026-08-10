# Pipeline to basecall the raw data generated from our nanopore, optionally calling
# modified bases as well. Set `modifications` in config/config.yaml to choose.
# Configuration and the generic post-processing rules live in common.smk.


include: "common.smk"


rule all:
    input:
        fastq=expand(os.path.join(FASTQ_DIR, "barcode_{barcode}.fastq.gz"), barcode=BARCODES),
        unclassified=os.path.join(FASTQ_DIR, "unclassified.fastq.gz"),
        # With modified bases the bam files are an output, not an intermediate.
        bam=(
            expand(os.path.join(BAM_DIR, "barcode_{barcode}.bam"), barcode=BARCODES)
            if MODIFICATIONS
            else []
        ),
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
        # Only a dependency when modified bases are called, so that download_model is
        # not asked for a model the run does not need.
        mods=MODS_PATH if MODIFICATIONS else [],
    output:
        file=os.path.join(TMP_DIR, "dorado_raw/basecalled.bam"),
    log:
        os.path.join(LOG_DIR, "basecall.log"),
    conda:
        "conda_envs/nanopore_basecalling.yml"
    params:
        kit=NANOPORE_KIT,
        model=DORADO_MODEL,
        dorado=DORADO_BIN,
        mods_flag=("--modified-bases-models " + MODS_PATH) if MODIFICATIONS else "",
    shell:
        """
        {params.dorado} basecaller {input.model} {input.input_dir} {params.mods_flag} --kit-name {params.kit} > {output.file} 2> {log}
        """


rule demultiplex:
    message:
        "Splitting the reads based on detected barcodes, and removing the barcodes from the reads."
    input:
        rules.basecall.output.file,
    output:
        directory=directory(BAM_DIR),
        barcodes=expand(os.path.join(BAM_DIR, "barcode_{barcode}.bam"), barcode=BARCODES),
        unclassified=os.path.join(BAM_DIR, "unclassified.bam"),
    log:
        os.path.join(LOG_DIR, "demultiplex.log"),
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

        # A record-less bam for the barcodes that got no reads. An empty file would not
        # be valid bam, and the convert rule feeds every one of these to samtools.
        # Taken before the cd, while {input} is still resolvable.
        header_bam=$(mktemp)
        trap 'rm -f "$header_bam"' EXIT
        samtools view -b -H {input} > "$header_bam"

        {params.dorado} demux --output-dir {output.directory}/minknow --no-classify {input} -t {threads}
        cd {output.directory}

        # Since v1.2 dorado writes a nested MinKNOW tree rather than flat per-barcode files:
        #   <root>/<position>/<sample>/<run>/bam_pass/<barcodeNN>/<prefix>_..._<n>.bam
        # A single barcode can be spread over several files, so collapse each barcode into
        # one flat file, and write a record-less one for every barcode that got no reads.
        found=0
        for bc in {BARCODES}; do
            mapfile -t files < <(find minknow -type f -name '*.bam' -path "*/barcode$bc/*" | sort)
            if [ ${{#files[@]}} -gt 0 ]; then
                samtools cat -o barcode_$bc.bam "${{files[@]}}"
                found=1
            else
                cp "$header_bam" barcode_$bc.bam
            fi
        done

        mapfile -t unclassified < <(find minknow -type f -name '*.bam' -path '*/unclassified/*' | sort)
        if [ ${{#unclassified[@]}} -gt 0 ]; then
            samtools cat -o unclassified.bam "${{unclassified[@]}}"
        else
            cp "$header_bam" unclassified.bam
        fi

        if [ $found -eq 0 ]; then
            echo "ERROR: dorado demux produced no per-barcode bam files under $(pwd)/minknow." >&2
            echo "Its output layout has probably changed again. Found instead:" >&2
            find minknow >&2
            exit 1
        fi
        rm -rf minknow
        """


rule convert:
    message:
        "Converting the file {input.bam} file to .fastq format."
    input:
        bam=os.path.join(BAM_DIR, "{filename}.bam"),
    output:
        fastq=os.path.join(TMP_DIR, "barcoded/{filename}.fastq"),
    log:
        os.path.join(LOG_DIR, "convert/{filename}.log"),
    conda:
        "conda_envs/nanopore_basecalling.yml"
    shell:
        """
        samtools bam2fq {input.bam} > {output.fastq} 2> {log}
        """


rule compress:
    message:
        "Generating the final compressed file {output.output_file}."
    input:
        input_file=os.path.join(TMP_DIR, "barcoded/{filename}.fastq"),
    output:
        output_file=os.path.join(FASTQ_DIR, "{filename}.fastq.gz"),
    log:
        os.path.join(LOG_DIR, "compress/{filename}.log"),
    conda:
        "conda_envs/nanopore_basecalling.yml"
    shell:
        """
        gzip -c {input} > {output} 2> {log}
        """
