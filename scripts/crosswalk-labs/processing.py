from datetime import datetime
from pathlib import Path

import pandas as pd

from models import (
    DataSource,
    Emissions,
    GasType,
    Sector
)

from utils import write_csv


def main():
    # ------------------------------------------
    # datasource table
    # ------------------------------------------
    datasource_name = "crosswalk-labs"
    publisher = "crosswalk-labs"

    datasource = DataSource(
        id=f"{publisher}:{datasource_name}",
        name=datasource_name,
        publisher=publisher,
        published_date=datetime.strptime("2026-06-08", "%Y-%m-%d"),
        version="2025-q2",
        url="https://explore.crosswalk.io/",
    )

    # load data and define output directory
    data_dir = (
        Path(__file__).resolve().parent.parent.parent / "data" / f"{datasource_name}"
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
    # Sectors
    # ------------------------------------------
    sector_dictionary = {
        "scope1_commercial": "commercial",
        "scope1_electricity_production" : "electricity production",
        "scope1_industrial": "industrial", 
        "scope1_residential" : "residential",
        "scope1_transportation" : "transporation",
        "scope2_total": "scope2 total",
        "scope1_total": "scope1 total",
    }

    sector_validated = [
        Sector(
            id=f"{datasource_name}:{name}",
            code=name,
            name=name,
            taxonomy="crosswalk labs",
            datasource_id=datasource.id,
        ).model_dump()
        for name in sector_dictionary.values()
    ]

    write_csv(
            output_dir=output_dir,
            name=Sector.__tablename__,
            data=sector_validated,
            mode="w",
    )

    # ------------------------------------------
    # get actors
    # ------------------------------------------

    locode_file = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "locode"
        / "processed"
        / "actor.csv"
    )

    df_locode = (
        pd.read_csv(locode_file)
        .loc[:,["id", "is_part_of", "name"]]
        .rename(columns={"id":"locode", "name":"city", "is_part_of":"iso"})
        .loc[lambda df: df["iso"].str.contains("US-", na=False)]
    )


    # ------------------------------------------
    # load raw data and metadata
    # ------------------------------------------
    data_file = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "crosswalk-labs"
        / "raw"
        / "crosswalk_explore_place_top_3000_2025-q2.csv"
    )

    df = pd.read_csv(data_file)

    # get cities from dataframe
    #df_cities = df[["geoid", "name"]].drop_duplicates()

    # read the Data Commons database
    data_commons_database = "https://raw.githubusercontent.com/LEDGER-project/data-commons-database/refs/heads/main/database.csv"
    df_data_commons = pd.read_csv(data_commons_database)

    # maps geoid to name in LOCODE database
    change_these_geoid_names = {
        "639003" : "La Canada-Flintridge",
        "811810": "Canon City",
        "947515": "Milford",
        "1303440": "Athens",
        "1304204": "Augusta",
        "1608830": "Boise", 
        "1836003" : "Indianapolis",
        "2146027": "Lexington",
        "2242030": "La Place",
        "2503690" : "Barnstable",
        "2540710": "Methuen",
        "2573440" : "Watertown",
        "2577890" : "West Springfield",
        "2758000": "Saint Paul",
        "3011397": "Butte"
    }

    # change the names via loop, this could be better
    for geoid, new_name in change_these_geoid_names.items():
        df_data_commons.loc[df_data_commons["geoid"].astype(str) == geoid, "city"] = new_name

    # ------------------------------------------
    # process the dataset
    # ------------------------------------------

    df_out = df_data_commons.merge(df_locode, on=["iso", "city"])

    megatonne_to_tonne = 1_000_000

    df_data = (
        df
        .merge(df_out[["locode", "geoid"]], on="geoid")
        .assign(sector = lambda x:  x["sector"].replace(sector_dictionary))
        .assign(emissions = lambda x: x["co2"] * megatonne_to_tonne )
        .query("sector != 'scope2 total'")
        .assign(units = "tCO2")
        #.rename(columns = {"co2":"emissions"}) 
        .query("emissions > 0")
        .rename(columns = {"locode": "actor_id"})
    )

    # ------------------------------------------
    # emissions dataset for gases in natural units
    # ------------------------------------------
    # sector_id is a little clunky
    df_emissions  = (
        df_data
        .query("sector != 'scope1 total'") 
        .assign(
            sector_id = lambda x: x["sector"].apply(lambda row: f"crosswalk-labs:{row}"),
            gas = "CO2")
        .loc[:,["year", "actor_id", "gas", "emissions", "units", "sector_id"]]
    )

    emissions_validated = [
        Emissions(
            id=f"{row.actor_id}:{row.year}:{row.gas}:{row.sector_id}",
            actor_id=row.actor_id,
            gas=GasType(row.gas),
            sector_id=row.sector_id,
            year=row.year,
            emissions=row.emissions,
            units=row.units,
            datasource_id=datasource.id,
        ).model_dump()
        for row in df_emissions.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=Emissions.__tablename__,
        data=emissions_validated,
        mode="w",
    )
    
if __name__ == "__main__":
    main()
