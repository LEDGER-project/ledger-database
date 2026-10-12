rule net_zero_tracker:
    input:
        "logs/iso-3166-1.log"
    output:
        "logs/net-zero-tracker.log"
    shell:
        "importer bulk net-zero-tracker > {output}"