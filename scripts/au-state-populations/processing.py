from datetime import datetime
from functools import reduce
from pathlib import Path

import pandas as pd

from utils import (
    write_csv,
    display_excel_sheets
)
from models import (
    DataSource,
    Population
)

STEM_TO_ACTOR = {
    "queensland": "AU-QLD",
    "tasmania": "AU-TAS",
    "northern-territory": "AU-NT",
    "victoria": "AU-VIC",
    "western-australia": "AU-WA",
    "act" : "AU-ACT",
    "new-south-wales": "AU-NSW",
    "south-australia": "AU-SA",
}

if __name__ == "__main__":

    # define  datasource and publisher at top
    # datasource used to make data directory
    datasource_name = "abs-national-state-and-territory-population"
    publisher = "Australian-Bureau-of-Statistics"

    # output directory
    data_dir = (
        #Path(__file__).resolve().parent.parent.parent 
        Path.cwd().resolve().parent.parent / "data" / f"{datasource_name}"
    )
    output_dir = data_dir / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)


    # ------------------------------------------
    # DataSource table
    # ------------------------------------------
    # https://unfccc.int/topics/mitigation/resources/registry-and-data/ghg-data-from-unfccc
    datasource_name = "abs-national-state-and-territory-population"
    publisher = "Australian-Bureau-of-Statistics"

    datasource = DataSource(
        id=f"{publisher}:{datasource_name}",
        name="National, state and territory population",
        publisher=publisher,
        published_date=datetime.strptime("2025-10-28", "%Y-%m-%d"),
        version="20251028",
        url=f"https://www.abs.gov.au/statistics/people/population/national-state-and-territory-population/latest-release#data-downloads",
    )

    write_csv(
        output_dir=output_dir,
        name=DataSource.__tablename__,
        data=datasource,
        mode="w",
    )


    # ------------------------------------------
    # Population table
    # ------------------------------------------

    files = (Path().cwd().parent.parent / "data" / "au-state-populations" / "raw").glob("*.xlsx")

    list_of_dfs = []

    for fl in files:
        actor_id = STEM_TO_ACTOR.get(fl.stem)
        sheets = [x for x in display_excel_sheets(fl) if 'data' in x.lower()]

        df_tmp = (
            reduce(lambda l, r: pd.merge(l, r, on="Unnamed: 0", how="outer"),
                [pd.read_excel(fl, sheet_name=s) for s in sheets])
            .rename(columns={'Unnamed: 0': 'date'})
            .assign(date=lambda d: pd.to_datetime(d['date'], errors='coerce'))
            .dropna(subset=['date'])
            .pipe(lambda d: d.loc[:, ['date'] + [c for c in d.columns if 'Persons' in c]])
            .pipe(lambda d: d.assign(
                **{c: pd.to_numeric(d[c], errors='coerce') for c in d.columns if 'Persons' in c}
            ))
            .set_index("date")
            .sum(axis=1, numeric_only=True)
            .rename("population")
            .reset_index(name="population") 
            .assign(
                year=lambda d: d['date'].dt.year,
                #datasource_id = datasource.id,
                actor_id = actor_id,
                #id = lambda d: d.apply(lambda x: f"{x['actor_id']}:{x['year']}", axis=1),
                )
            .loc[:, ["id", "actor_id", "year", "population", "datasource_id"]]
        )

        list_of_dfs.append(df_tmp)


    df = pd.concat(list_of_dfs).astype({"actor_id": str, "year": int, "population": int})

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
