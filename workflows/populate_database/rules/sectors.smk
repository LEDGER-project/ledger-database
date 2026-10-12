rule crt_on_nir:
    output:
        "logs/crt-on-nir.log"
    shell:
        "importer bulk crt-on-nir > {output}"