#---------------------------------------------------
# World countries
#---------------------------------------------------
rule wpp:
    input:
        "logs/iso-3166-1.log"
    output:
        "logs/wpp.log"
    shell:
        "importer bulk wpp > {output}"


#---------------------------------------------------
# U.S states
#---------------------------------------------------
rule fred_state_population:
    input:
        "logs/iso-3166-2.log"
    output:
        "logs/fred-state-population.log"
    shell:
        "importer bulk fred-state-population > {output}"


#---------------------------------------------------
# Canadian provinces
#---------------------------------------------------
rule canada_province_population:
    input:
        "logs/iso-3166-2.log"
    output:
        "logs/canada-province-population.log"
    shell:
        "importer bulk canada-province-population > {output}"


#---------------------------------------------------
# Australian state populations
#---------------------------------------------------
rule abs_national_state_and_territory_population:
    input:
        "logs/iso-3166-2.log"
    output:
        "logs/abs-national-state-and-territory-population.log"
    shell:
        "importer bulk abs-national-state-and-territory-population > {output}"


#---------------------------------------------------
# UK state populations
#---------------------------------------------------
rule ons_ukpopulationestimates:
    input:
        "logs/iso-3166-2.log"
    output:
        "logs/ons-ukpopulationestimates.log"
    shell:
        "importer bulk ons-ukpopulationestimates > {output}"