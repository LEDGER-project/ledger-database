rule net_zero_tracker:
    input:
        "logs/iso-3166-1.log"
    output:
        "logs/net-zero-tracker.log"
    shell:
        "importer bulk net-zero-tracker > {output}"

rule net_zero_regions:
    input:
        "logs/iso-3166-2.log"
    output:
        "logs/net-zero-regions.log"
    shell:
        "importer bulk net-zero-regions > {output}"