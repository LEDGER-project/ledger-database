rule us_climate_alliance:
    input:
        "logs/iso-3166-2.log"
    output:
        "logs/us-climate-alliance.log"
    shell:
        "importer bulk us-climate-alliance > {output}"
