
#!!
#!!  has duplicates in AR:2010:biofuels
#!! 

rule statistical_review_world_energy:
    input:
        "logs/iso-3166-1.log"
    output:
        "logs/statistical-review-world-energy.log"
    shell:
        "importer bulk statistical-review-world-energy  > {output}"
