#
# this needs work
# can not match all regions
#
from datetime import datetime
from pathlib import Path

import pandas as pd

from utils import (
    climactor_keydict, 
    get_country_codes, 
    get_iso_3166_2_codes, 
    write_csv
)

from models import (
    Population,
    GDP,
    DataSource,
)


def main():
    # ------------------------------------------
    # DataSource table
    # ------------------------------------------
    datasource_name = "dose"
    publisher = "PIK"

    datasource = DataSource(
        id=f"{publisher}:{datasource_name}",
        name="DOSE - Global dataset of reported subnational economic output",
        publisher=publisher,
        published_date=datetime.strptime("2026-05-07", "%Y-%m-%d"),
        version="v7",
        url="https://zenodo.org/records/20035157",
    )

    # load data and define output directory
    data_dir = (
        Path().cwd().resolve().parent.parent / "data" / "dose"
    )
    output_dir = data_dir / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    write_csv(
        output_dir=output_dir,
        name=DataSource.__tablename__,
        data=datasource.model_dump(),
        mode="w",
    )

    # ------------------------------------------
    # process data
    # ------------------------------------------
    fl = (
        Path().cwd().parent.parent
        / "data"
        / "dose"
        / "raw"
        / "DOSE_V2.14.csv" 
    )

    df = pd.read_csv(fl).assign(name = lambda x: x["region"].str.lower())

    df_regions_raw = (
        df
        .loc[:, ["name", "GID_0"]]
        .rename(columns={"GID_0":"iso3"})
        .drop_duplicates()
    )

    # actors
    df_actors = get_country_codes()

    df_subdiv = (
        get_iso_3166_2_codes()
        .merge(df_actors.rename(columns={"actor_id":"country_iso2"}), on=["country_iso2"])
        .assign(name = lambda x: x["name"].str.lower())
    )

    # key dictionary
    df_key = (
        climactor_keydict()
        .assign(
            right = lambda x: x["right"].str.lower(),
            wrong = lambda x: x["wrong"].str.lower(),
            right_simpl = lambda x: x["right_simpl"].str.lower(),
        )
    )

    # 3714
    # ['Region', 'SubRegion', 'City', 'Association']
    df_key_merged = (
        df_key.query("entity_type=='Region'")
        .merge(df_subdiv, left_on=["right_simpl", "iso"], right_on=["name", "iso3"], how="inner") 
    )

    df_simp = (
        df_regions_raw
        .merge(
            df_key_merged.loc[:,["right_simpl", "iso3","actor_id"]], 
            left_on=["name", "iso3"],
            right_on=["right_simpl", "iso3"], 
            how="inner")
        .drop_duplicates()
        .loc[:, ["name", "iso3", "actor_id"]]
    )

    df_wrong = (
        df_regions_raw
        .merge(
            df_key_merged.loc[:,["wrong", "iso3","actor_id"]], 
            left_on=["name", "iso3"], 
            right_on=["wrong", "iso3"], 
            how="inner")
        .drop_duplicates()
        .loc[:, ["name", "iso3", "actor_id"]]
    )

    df_direct = df_regions_raw.merge(df_subdiv, on=["iso3", "name"]).dropna().drop_duplicates().loc[:, ["name", "iso3", "actor_id"]]

    df_concat = pd.concat([df_simp, df_wrong, df_direct]).drop_duplicates()

    
    # these I can't map, there are 605 regions, 36%, that I can't match
    #keys = ["name", "iso3"]

    #df_diff = (
    #    df_regions_raw[keys]
    #    .drop_duplicates()
    #    .merge(df_concat[keys].drop_duplicates(), on=keys, how="left", indicator=True)
    #    .query("_merge == 'left_only'")
    #    .drop(columns="_merge")
    #)

    df_data = (
        df.merge(df_concat, left_on=["name", "GID_0"], right_on=["name", "iso3"])
        .loc[:, ["actor_id", "year", "grp_pc_usd_2015", "pop"]]
        .assign(gdp = lambda x: x["grp_pc_usd_2015"] * x["pop"])
    )

    # ------------------------------------------
    # Population table
    # ------------------------------------------
    df_pop = df_data.loc[:,["actor_id", "year", "pop"]].dropna().astype({"year": int, "actor_id": str, "pop":int, })
    population_validated = [
        Population(
            id=f"{row.actor_id}:{row.year}:{datasource.id}",
            actor_id=row.actor_id,
            year=row.year,
            population=row.pop,
            datasource_id=datasource.id,
        ).model_dump()
        for row in df_pop.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=Population.__tablename__,
        data=population_validated ,
        mode="w",
    )

    # ------------------------------------------
    # GDP table
    # ------------------------------------------
    df_gdp = df_data.loc[:,["actor_id", "year", "gdp"]].dropna().astype({"year": int, "actor_id": str, "gdp":float, })
    gdp_validated = [
        GDP(
            id=f"{row.actor_id}:{row.year}:{datasource.id}",
            actor_id=row.actor_id,
            year=row.year,
            gdp=row.gdp,
            datasource_id=datasource.id,
        ).model_dump()
        for row in df_gdp.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=GDP.__tablename__,
        data=gdp_validated ,
        mode="w",
    )


if __name__ == "__main__":
    main()