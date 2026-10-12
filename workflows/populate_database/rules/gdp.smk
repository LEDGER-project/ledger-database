#---------------------------------------------------
# World countries
#---------------------------------------------------
rule world_bank_gdp:
    input:
        "logs/iso-3166-1.log"
    output:
        "logs/world-bank-gdp.log"
    shell:
        "importer bulk world-bank-gdp > {output}"
