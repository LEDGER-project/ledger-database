from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

from utils import write_csv
from utils import display_excel_sheets

from models import (
    AssessmentReport,
    DataSource,
    GasType,
    Emissions,
    EmissionsCO2e,
    EmissionsTotalCO2e,
    EmissionsTotalSector,
    AggregationType,
)


if __name__ == "__main__":

    # load data and define output directory
    data_dir = (
        Path(__file__).resolve().parent.parent.parent / "data" / "unfccc-annex1" / "processed"
    )
    output_dir = data_dir / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)



    # ------------------------------------------
    # DataSource table
    # ------------------------------------------
    datasource_name = "ghg-profiles-annex-1"
    publisher = "UNFCCC"

    # url=f"https://di.unfccc.int/ghg_profiles/annexOne/{iso3}/{iso3}_ghg_profile.xlsx",
    datasource = DataSource(
        id=f"{publisher}:{datasource_name}",
        name="GHG Profiles - Annex I",
        publisher=publisher,
        published_date=datetime.strptime("2025-10-28", "%Y-%m-%d"),
        version="20251028",
        url = "https://di.unfccc.int/ghg_profile_annex1"
    )

    write_csv(
        output_dir=output_dir,
        name=DataSource.__tablename__,
        data=datasource.model_dump(),
        mode="w",
    )

    # ------------------------------------------
    # get actors
    # ------------------------------------------
    fl_actors = (
        #Path(__file__).resolve().parent.parent.parent
        Path.cwd().resolve().parent.parent
        / "data"
        / "iso-3166-1"
        / "raw"
        / "countries.csv"
    )

    df_actors = (
        pd.read_csv(fl_actors, keep_default_na=False)
        .loc[:, ["#country_code_alpha2", "country_code_alpha3"]]
        .rename(columns={"#country_code_alpha2":"alpha2", "country_code_alpha3":"alpha3"})
        )
    

    # ------------------------------------------
    # get sector codes
    # ------------------------------------------
    #Path(__file__).resolve().parent.parent.parent
    fl_codes = Path.cwd().resolve().parent.parent / "data" / "crt-on-nir" / "processed" / "sector.csv"

    df_codes = (
        pd.read_csv(fl_codes)
        .rename(columns={"id":"id_sector"})
        .loc[:, ["id_sector", "code", "name"]]
    )

    # ------------------------------------------
    # get gwps
    # ------------------------------------------
    fl_gwp = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "gwp"
        / "processed"
        / "gwp.csv"
    )

    df_gwp = (
        pd.read_csv(fl_gwp)
        .loc[:, ["id", "gwp", "gas", "assessment_report"]]
        .rename(columns={"id": "gwp_id"})
    )


    # ------------------------------------------
    # EmissionsBySector
    # ------------------------------------------
    
    files = (
        #Path(__file__).resolve().parent.parent.parent
        Path.cwd().resolve().parent.parent
        / "data"
        / "unfccc-annex1" 
        / "raw"
    ).glob("*_ghg_profile.xlsx")

    kt_to_tonne = 1000

    list_of_dfs = []

    for fl in tqdm(files):
        iso3 = Path(fl).stem.split("_")[0]
        actor_id = df_actors.loc[df_actors["alpha3"] == iso3, "alpha2"].iat[0]

        df_tmp = (
            pd.read_excel(fl, sheet_name="Data_by_sector")
            .iloc[
            lambda d: slice(
                d.index[d["GHG emissions, kt CO2 equivalent"].eq('Breakdown by sub-sectors')][0] + 1,
                d.index[d["GHG emissions, kt CO2 equivalent"].eq('Average annual change, in percent')][0]
            )
            ]
            .drop(columns=["Base year"], errors="ignore")
            .drop(columns=["1990.1"], errors="ignore") # this shows in KAZ for some reason
            .melt(id_vars="GHG emissions, kt CO2 equivalent", var_name='year', value_name='emissions_kt_co2_eq')
            .rename(columns={"GHG emissions, kt CO2 equivalent":"sector"})
            .loc[
                lambda d: pd.to_numeric(d["emissions_kt_co2_eq"], errors="coerce").notna()
            ]
            .assign(
                code=lambda d: d["sector"].str.split(" ", n=1).str[0],
                name=lambda d: d["sector"].str.split(" ", n=1).str[1],
                emissions=lambda d: d["emissions_kt_co2_eq"] * kt_to_tonne,
                units = "CO2 * tonne / yr"
            )
            .assign(
                code = lambda d: d['code'].str.rstrip('.'),
                actor_id = actor_id
            )
            .merge(df_codes, on=["code"])
            .loc[:, ["id_sector", "actor_id", "year", "emissions", "units"]]
            .astype({
                "id_sector": str,
                "actor_id": str, 
                "year": int, 
                "emissions": float, 
                "units": str})
        )

        list_of_dfs.append(df_tmp)


    df = pd.concat(list_of_dfs).astype({"actor_id": str, "year": int, "emissions": float, "units": str})