from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from utils import write_csv
from utils import display_excel_sheets

from models import (
    DataSource,
    Sector,
    GasType,
    Emissions,
)

def parent_from_code(code):
    if isinstance(code, str) and '.' in code:
        return code.rsplit('.', 1)[0]
    return code

if __name__ == "__main__":

    datasource_name = "carbon-monitor-cities"
    publisher = "carbon-monitor"

    # load data and define output directory
    data_dir = (
        Path(__file__).resolve().parent.parent.parent / "data" / f"{datasource_name}" / "processed"
    )
    output_dir = data_dir / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)


    fl = (Path(__file__).resolve().parent.parent.parent 
        / "data" 
        / f"{datasource_name}"
        / "raw" 
        / "carbonmonitor-cities_datas_2025-12-05.csv"
        )


    #fl = "/Users/lukegloege/projects/ghg-tracker-database/data/carbon-monitor-cities/raw/carbon-monitor-CITIES-maingraphdatas.xlsx"
    # carbonmonitor-cities_datas_2025-12-05.csv
    #df = pd.read_excel(fl).dropna()

    # ------------------------------------------
    # Create Locode table
    # Note: this may need to be updated with each release
    # ------------------------------------------
    d = {
        'Qingdao': "CNQIN", 
        'Copenhagen': "DKCPH",  # kobenhavn
        'Paris': "FRPAR", 
        'Berlin': "DEBER", 
        'New Delhi': "INICD", 
        'Tokyo': "JPTYO",
        'Amsterdam': "NLAMS", 
        'Moscow': "RUMOW", 
        'Seoul': "KRSEL",
        'Stockholm': "SESTO",
        'Bangkok': "THBKK",
        'Los Angeles' :"USLAX",
        'Melbourne': "AUMEL",
        'Sydney' : "AUSYD", 
        'Santiago' : "BRSTG",
        'Beijing' : "CNBJS", 
        'Chengdu': "CNCDU",
        'Chongqing' : "CNCQI", 
        'Hangzhou' : "CNHAZ", 
        'Jinan' : "CNJNA", 
        'Nanjing' : "CNNJI", 
        'Shanghai' : "CNSGH",
        'Bogota' : "COBOG", 
        'Helsinki' : "FIHEL", 
        'Lyon': "FRLIO", 
        'Marseille' : "FRMRS", 
        'Nice' : "FRNCE",
        'Munich' : "DEMUC", #Munchen
        'Milan' :"ITMIL", 
        'Rome' :"ITROM", 
        'Osaka':"JPOSA",
        'Mexico City' : "MXMEX", 
        'Oslo' : "NOOSL", 
        'Cape Town' : "ZACPT",
        'Barcelona' : "BRBAQ", 
        'Madrid' : "COMDD", 
        'Istanbul':"TRIST",
        'London' : "GBLON", 
        'Chicago' : "USCHI", 
        'Houston' : "USHOU",
        'Miami' : "USMIA",
        'New York' : "USNYC",
        'San Francisco' : "USSFO", 
        'Seattle' : "USSEA", 
        'Washington': "USWAS"
    }

    df_locodes = pd.DataFrame(list(d.items()), columns=["city", "locode"])

    # ------------------------------------------
    # DataSource table
    # ------------------------------------------
    datasource = DataSource(
        id=f"{publisher}:{datasource_name}",
        name="Carbon Monitor Cities",
        publisher=publisher,
        published_date=datetime.strptime("2015-03-05", "%Y-%m-%d"),
        url="https://cities.carbonmonitor.org/",
    )


    write_csv(
        output_dir=output_dir,
        name=DataSource.__tablename__,
        data=datasource.model_dump(),
        mode="w",
    )


    # ------------------------------------------
    # Sector table
    # ------------------------------------------
    sectors_dict = {
        'Aviation': "1", 
        'Ground Transport': "2", 
        'Industry': "3", 
        'Power': "4", 
        'Residential': "5"
    }

    sector_validated = [
        Sector(
            id=f"carbon-monitor-cities:{code}",
            code=code,
            parent_code=None,
            name=name,
            taxonomy="Carbon Monitor Cities",
            datasource_id=datasource.id,
        ).model_dump()
        for name, code in sectors_dict.items()
    ]


    write_csv(
        output_dir=output_dir,
        name=Sector.__tablename__,
        data=sector_validated,
        mode="w",
    )

    # ------------------------------------------
    # Emissions table
    # Note: file named at top
    # ------------------------------------------

    kt_to_tonne = 1_000 # tonne per Kt
    df = (pd.read_csv(fl)
        .merge(df_locodes, on='city')  
        .assign(
            date=lambda d: pd.to_datetime(d["date"], dayfirst=True),
            year=lambda d: d["date"].dt.year,
            emissions = lambda d: d["value"].apply(lambda row: row * kt_to_tonne),
            units = "tonne*CO2",
            sector_id = lambda d: d['sector'].replace(sectors_dict)
        )
        .loc[:, ["year", "locode", "sector_id", "emissions", "units"]]
        .groupby(["locode", "year","sector_id", "units", ]).sum()
        .reset_index()
        .assign(gas = "CO2")
        .rename(columns={"locode":"actor_id"})
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
        for row in df.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=Emissions.__tablename__,
        data=emissions_validated,
        mode="w",
    )

