# Basecalling: fetching the dorado models, calling the reads, splitting them by barcode
# and producing the final compressed fastq.
#
# Conda paths are relative to this file, hence the "../".


rule download_model:
    message:
        "Downloading the dorado model {wildcards.model}."
    output:
        model_dir=directory(os.path.join(DORADO_MODELS_DIR, "{model}")),
    log:
        os.path.join(LOG_DIR, "download_model_{model}.log"),
    params:
        dorado=DORADO_BIN,
        models_dir=DORADO_MODELS_DIR,
    shell:
        """
        {params.dorado} download --model {wildcards.model} --models-directory {params.models_dir} > {log} 2>&1
        """


rule basecall:
    message:
        "Basecalling the reads using Dorado model {params.model} for the kit {params.kit}."
    input:
        input_dir=INPUT_DIR,
        logfile=LOGFILE,
        model=MODEL_PATH,
        # One per modification the run asks for, and empty when it asks for none, so
        # download_model is never called for a model the run does not need.
        mods=MODS_PATHS,
    output:
        file=os.path.join(TMP_DIR, "dorado_raw/basecalled.bam"),
    log:
        os.path.join(LOG_DIR, "basecall.log"),
    conda:
        "../conda_envs/nanopore_basecalling.yml"
    params:
        kit=NANOPORE_KIT,
        model=DORADO_MODEL,
        dorado=DORADO_BIN,
        # Dorado takes the modified-base models as one comma separated list, and writes
        # every modification it is given into the same bam.
        mods_flag=("--modified-bases-models " + ",".join(MODS_PATHS)) if MODIFICATIONS else "",
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
        "../conda_envs/nanopore_basecalling.yml"
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
        "../conda_envs/nanopore_basecalling.yml"
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
        "../conda_envs/nanopore_basecalling.yml"
    shell:
        """
        gzip -c {input} > {output} 2> {log}
        """
