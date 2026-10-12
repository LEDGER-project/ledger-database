rule earth:
    output:
        "logs/earth.log"
    shell:
        "importer bulk earth > {output}"


rule iso_3166_1:
    input:
        "logs/earth.log"
    output:
        "logs/iso-3166-1.log"
    shell:
        "importer bulk iso-3166-1 > {output}"


rule iso_3166_2:
    input:
        "logs/iso-3166-1.log"
    output:
        "logs/iso-3166-2.log"
    shell:
        "importer bulk iso-3166-2 > {output}"


rule locode:
    input:
        "logs/iso-3166-1.log",
        "logs/iso-3166-2.log"
    output:
        "logs/locode.log"
    shell:
        "importer bulk locode > {output}"



