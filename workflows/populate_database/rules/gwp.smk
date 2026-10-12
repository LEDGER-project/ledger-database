rule gwp:
    output:
        "logs/gwp.log"
    shell:
        "importer bulk gwp > {output}"