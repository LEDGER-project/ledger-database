rule primap:
    input:
        "logs/iso-3166-1.log",
        "logs/crt-on-nir.log",
        "logs/gwp.log"
    output:
        "logs/primap.log"
    shell:
        "importer bulk primap > {output}"


rule epa_state_emissions:
    input:
        "logs/iso-3166-2.log",
        "logs/crt-on-nir.log",
        "logs/gwp.log"
    output:
        "logs/epa-state-emissions.log"
    shell:
        "importer bulk epa-state-emissions > {output}"


rule eccc_ghg_inventory:
    input:
        "logs/iso-3166-2.log",
        "logs/crt-on-nir.log",
        "logs/gwp.log"
    output:
        "logs/eccc-ghg-inventory.log"
    shell:
        "importer bulk eccc-ghg-inventory > {output}"


rule naei_gb_subnational_emissions:
    input:
        "logs/iso-3166-2.log",
        "logs/crt-on-nir.log",
        "logs/gwp.log"
    output:
        "logs/naei-gb-subnational-emissions.log"
    shell:
        "importer bulk naei-gb-subnational-emissions > {output}"


rule au_state_emissions:
    input:
        "logs/iso-3166-2.log",
        "logs/crt-on-nir.log",
        "logs/gwp.log"
    output:
        "logs/au-state-emissions.log"
    shell:
        "importer bulk au-state-emissions > {output}"