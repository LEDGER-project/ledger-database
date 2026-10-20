from datetime import datetime
from pathlib import Path
import re

import pandas as pd

from utils import write_csv

from models import DataSource, Population


def extract_single_country(text):
    pattern = r"\b(England|Scotland|Wales|Northern Ireland)\b"
    countries = re.findall(pattern, text)
    if len(countries) == 1:
        return countries[0]
    return None


if __name__ == "__main__":
    # define  datasource and publisher at top
    # datasource used to make data directory
    datasource_name = "ons-ukpopulationestimates"
    publisher = "ons"  # office of national statistics

    # output directory
    data_dir = (
        # Path(__file__).resolve().parent.parent.parent
        Path.cwd().resolve().parent.parent / "data" / f"{datasource_name}"
    )
    output_dir = data_dir / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------
    # DataSource table
    # ------------------------------------------

    datasource = DataSource(
        id=f"{publisher}:{datasource_name}",
        name="Population estimates for the UK and constituent countries by sex and age",
        publisher=publisher,
        published_date=datetime.strptime("2024-07-15", "%Y-%m-%d"),
        version="mid-2023",
        url="https://www.ons.gov.uk/file?uri=/peoplepopulationandcommunity/populationandmigration/populationestimates/datasets/populationestimatesforukenglandandwalesscotlandandnorthernireland/mid2024/mye24tablesuk.xlsx",
    )

    write_csv(
        output_dir=output_dir,
        name=DataSource.__tablename__,
        data=datasource.model_dump(),
        mode="w",
    )

    # get actors
    fl_actors = (
        # Path(__file__).resolve().parent.parent.parent
        Path.cwd().resolve().parent.parent
        / "data"
        / "iso-3166-2"
        / "raw"
        / "subdivisions.csv"
    )

    df_actors = (
        pd.read_csv(fl_actors, keep_default_na=False)
        .loc[
            :,
            ["#country_code_alpha2", "subdivision_code_iso3166-2", "subdivision_name"],
        ]
        .rename(columns={"#country_code_alpha2": "country_code_alpha2"})
        .query("country_code_alpha2 == 'GB'")
        # .rename(columns={"#country_code_alpha2":"alpha2", "country_code_alpha3":"alpha3"})
    )

    # ------------------------------------------
    # Population table
    # ------------------------------------------

    fl = (
        # Path(__file__).resolve().parent.parent.parent
        Path.cwd().resolve().parent.parent
        / "data"
        / f"{datasource_name}"
        / "raw"
        / "ukpopulationestimates183820231.xlsx"
    )

    # display_excel_sheets(fl)

    list_of_data = []

    for table in [10, 12, 14, 17]:
        # table=10
        sheet_name = f"Table {table}"
        header = pd.read_excel(fl, sheet_name=sheet_name, nrows=1).columns[0]
        subnational = extract_single_country(header)

        actor_id = (
            df_actors.query("subdivision_name == @subnational")
            .loc[:, "subdivision_code_iso3166-2"]
            .iat[0]
        )

        # can set id and data_source_is below
        df_pop = (
            pd.read_excel(fl, sheet_name=sheet_name, skiprows=1)
            .assign(
                year=lambda d: d["Year"].apply(lambda x: x.split("-")[1]),
                actor_id=actor_id,
                id=lambda d: d.apply(lambda x: f"{x['actor_id']}:{x['year']}", axis=1),
                datasource_id=datasource.id,
            )
            .rename(columns={"Persons": "population"})
            .query("population != 'missing data'")
            .loc[:, ["actor_id", "year", "population"]]
            .sort_values(by="year")
        )

        list_of_data.append(df_pop)

        df = pd.concat(d for d in list_of_data)

    # set the correct types
    df = df.astype(
        {
            "actor_id": str,
            "year": int,
            "population": int,
        }
    )

    populations_validated = [
        Population(
            id=f"{row.actor_id}:{row.year}",
            year=row.year,
            actor_id=row.actor_id,
            population=row.population,
            datasource_id=datasource.id,
        ).model_dump()
        for row in df.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=Population.__tablename__,
        data=populations_validated,
        mode="w",
    )
