from datetime import datetime
from pathlib import Path
import re

import pandas as pd

from utils import write_csv
from models import (
    AssessmentReport,
    DataSource,
    EmissionsTotalCO2e,
    EmissionsTotalSector,
    AggregationType,
)

from utils import get_country_codes, get_iso_3166_2_codes

def get_gwps():
    file = (
        Path().cwd().parent.parent
        / "data"
        / "gwp"
        / "processed"
        / "gwp.csv"
    )

    return pd.read_csv(file)


def get_crt_sector():
    file = (
            Path().cwd().parent.parent
            / "data"
            / "crt-on-nir"
            / "processed"
            / "sector.csv"
        )

    return pd.read_csv(file)

def main():
    # ------------------------------------------
    # DataSource table
    # ------------------------------------------
    datasource_name = "state-ghg-emissions-and-removals"
    publisher = "EPA"

    datasource = DataSource(
        id=f"{publisher}:{datasource_name}",
        name="State GHG Emissions and Removals",
        publisher=publisher,
        published_date=datetime.strptime("2025-04-21", "%Y-%m-%d"),
        version="v04212025",
        url="https://www.edf.org/freedom-information-act-documents-epas-greenhouse-gas-inventory",
    )

    # load data and define output directory
    data_dir = (
        Path(__file__).resolve().parent.parent.parent / "data" / "epa-state-emissions"
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
    # Actors
    # ------------------------------------------
    df_actors = (get_iso_3166_2_codes()
        .query("country_iso2=='US'")
        .loc[:, ["actor_id"]]
        .reset_index(drop=True)
    )

    # ------------------------------------------
    # GWPS
    # ------------------------------------------
    df_gwp = get_gwps()


    # ------------------------------------------
    # Sectors
    # ------------------------------------------
    df_sector_all = (
        get_crt_sector()        
        .assign(
            name_sanitized=lambda x: x.apply(
                lambda row: row["name"].replace("-", " ").replace(",", "").lower(),
                axis=1,
            )
        )
        .rename(columns={"id": "sector_id"})
    )

    df_sector = df_sector_all.query("code.isin(['0','1','2','3','4','5','6'])")

    df_sector_all_plus_code = (
        df_sector_all
        .merge(
            df_sector_all.loc[:,["code", "name_sanitized"]].rename(columns={"code":"sector_code", "name_sanitized":"sector_sanitized"}), 
            left_on="parent_code", 
            right_on="sector_code"
        )
    )

    # ------------------------------------------
    # load raw data and process
    # ------------------------------------------
    fl = (
        Path().cwd().parent.parent
        / "data"
        / "epa-state-emissions"
        / "raw"
        / "EPA_GHGI_Methodology_Report_2025" 
        / "DRAFT_AllStateGHGdata_90-23.xlsx" 
    )

    # time frame of the dataset
    YEAR_START = 1990
    YEAR_END = 2023

    id_vars = [
        "sector",
        "subsector",
        "subsector_updated",
        "category",
        "sub_category_1",
        "sub_category_2",
        "sub_category_3",
        "sub_category_4",
        "sub_category_5",
        "carbon_pool",
        "fuel1",
        "fuel2",
        "geo_ref",
        "units",
        "ghg_category",
        "ghg_category_updated",
        "ghg",
        "gwp",
    ]

    value_vars = [str(num) for num in range(YEAR_START, YEAR_END+1)]

    geo_refs_to_drop = [
        "USTERR",    # aggregated emissions from US territories
        "FO",        # emissions occurring offshore within US water
        "National",  # emissions and sinks not disaggregated
    ]

    Tg_to_tonne = 1_000_000

    cofa_states = ["FM", "MH", "PW"]  # micronesia, marshall islands, palau
    us_territories = ["AS", "GU", "MP", "PR", "UM", "VI"]

    sheet_name="Data by Inv Reporting Sectors"

    replace_dict = {
        "subsector": {
            "CO2 transport, injection and geologic storage": "CO2 Transport and storage",
            "Direct and indirect N2O emissions from agricultural soils": "Agricultural soils",
            "Electronics Industry": "Electronic industry",
            "Fossil Fuel Combustion": "Fuel combustion",
            "Fugitives": "Fugitive emissions from fuels",
            "Incineration of Waste": "Fuel combustion", # EPA puts this in Energy sector because of waste to energy recovery
            "Non-Energy Uses of Fossil Fuels": "Non-energy products from fuels and solvent use", # EPA put under energy I changed to  IPPU
            "Production and Use of Fluorinated Gases": "Chemical industry",  # actually a subcategory of this, but for now its fine
        }
    } 

    df = (
        #
        #-- initial processing
        #
        pd.read_excel(fl, sheet_name=sheet_name)
        .query("not geo_ref.isin(@geo_refs_to_drop)")
        .query("not geo_ref.isin(@cofa_states)")
        .query("not geo_ref.isin(@us_territories)")
        .rename(
            columns=lambda x: re.sub(r"^Y(\d{4})", r"\1", x)
        )  # regex to remove leading Y from years
        .assign( # this updates subsector to match NIR
            subsector_updated=lambda x: x.apply(
                lambda row: (
                    "Urea Application" 
                    if (row['subsector'] == "CO2 Emissions from Liming, Urea Application and Other Carbon-Containing Fertilizers" 
                        and row['category'] == "Urea Fertilization")
                    else (
                        row['category']
                        if (row['subsector'] == "CO2 Emissions from Liming, Urea Application and Other Carbon-Containing Fertilizers" 
                            and row['category'] == "Liming")
                        else row['subsector']
                    )
                ),
                axis=1
            )
        )
        .assign(
            ghg_category_updated=lambda x: x.apply(
                lambda row: "F-gases" 
                if row['ghg_category'] in ['HFC', 'PFC', 'NF3', 'SF6']
                else row['ghg_category'],
                axis=1
            )
        )
        .melt(
            id_vars=id_vars,
            value_vars=value_vars,
            value_name="emissions",
            var_name="year",
        )
        .drop(columns=[
            "sub_category_1", 
            "sub_category_2", 
            "sub_category_3", 
            "sub_category_4", 
            "sub_category_5", 
            "carbon_pool", 
            "fuel1", 
            "fuel2", 
            "gwp", 
            "ghg_category", 
            "subsector", 
            "ghg", 
            "category"]
            )
        .rename(columns={"subsector_updated": "subsector", "ghg_category_updated":"gas"})
        .query("emissions > 0")
        #
        # -- processing subsector 
        #
        .query("sector!='Energy-Excluded'") # this drop international bunker fuels
        .assign(
            sector=lambda d: d["sector"].mask(d["subsector"] == "Non-Energy Uses of Fossil Fuels", "Industrial Processes and Product Use"))
        .replace(replace_dict)
        .assign(
            subsector=lambda x: x.apply(
                lambda row: row["subsector"].replace("-", " ").replace(",", "").lower(),
                axis=1,
            ),
            sector=lambda x: x.apply(
                lambda row: row["sector"].replace("-", " ").replace(",", "").lower(),
                axis=1,
            )
        )

    .merge(df_sector_all_plus_code.loc[:, ["sector_id", "code", "parent_code", "name_sanitized", "sector_sanitized"]], 
            left_on=["sector", "subsector"],
            right_on=["sector_sanitized", "name_sanitized"]
    )
        .assign(
            actor_id=lambda x: x.apply(
                lambda row: f"US-{row["geo_ref"]}",
                axis=1,
            ),
            emissions=lambda x: x.apply(
                lambda row: row["emissions"]*1_000_000,
                axis=1,
            ),
            assessment_report="AR5",
            units="CO2 * tonne", 
            gases_included="CH4, CO2, N2O, FGASES",

        )

    )

    # including a groupby().agg() in here because liming is from dolomite and limestone
    # currently we do not have emissions broken down into categories yet
    df_emissions_subsector = (
        df
        .loc[:, ["actor_id", "sector_id", "year", "emissions", "assessment_report", "gases_included", "units"]]
        .groupby(by=["actor_id", "sector_id", "year",  "assessment_report", "gases_included", "units"]).agg("sum")
        .reset_index()
        .astype({
            "actor_id": str,
            "sector_id": str,
            "year": int,
            "emissions": float,
            "assessment_report": str,
            "gases_included": str,
            "units": str
        })
    )

    df_emissions_sector = (
        df
        .drop(columns=["sector_id"])
        .merge(df_sector.loc[:,["sector_id", "code"]], left_on="parent_code", right_on="code")
        .loc[:, ["actor_id", "sector_id", "year", "emissions", "assessment_report", "gases_included", "units"]]
        .groupby(by=["actor_id", "sector_id", "year",  "assessment_report", "gases_included", "units"]).agg("sum")
        .reset_index()
        .astype({
            "actor_id": str,
            "sector_id": str,
            "year": int,
            "emissions": float,
            "assessment_report": str,
            "gases_included": str,
            "units": str
        })
    )

    df_total_sector = pd.concat([df_emissions_sector, df_emissions_subsector])

    # ------------------------------------------
    # emissions total sector
    # ------------------------------------------
    emissions_total_sector_validated = [
        EmissionsTotalSector(
            id=f"{row.actor_id}:{row.year}:{row.sector_id}:{row.assessment_report}",
            actor_id=row.actor_id,
            sector_id=row.sector_id,
            gases_included=row.gases_included,
            assessment_report=AssessmentReport(row.assessment_report),
            year=row.year,
            emissions=row.emissions,
            units=row.units,
            datasource_id=datasource.id,
        ).model_dump()
        for row in df_total_sector.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=EmissionsTotalSector.__tablename__,
        data=emissions_total_sector_validated,
        mode="w",
    )

    # ------------------------------------------
    # emissions aggregation
    # ------------------------------------------

    df_agg_total_ex_lulucf = (
        df_emissions_sector
        .query("sector_id != 'crt:4'")
        .groupby(by=["actor_id", "year", "assessment_report", "gases_included", "units"])
        .agg(emissions=("emissions", "sum"))
        .reset_index()
        .assign(aggregation_type = "total_ex_lulucf")
    )

    df_agg_total = (
        df_emissions_sector
        .groupby(by=["actor_id", "year", "assessment_report", "gases_included", "units"])
        .agg(emissions=("emissions", "sum"))
        .reset_index()
        .assign(aggregation_type = "total")
    )

    df_agg = pd.concat([df_agg_total_ex_lulucf, df_agg_total])


    emissions_total_co2e_validated = [
        EmissionsTotalCO2e(
            id=f"{row.actor_id}:{row.year}:{row.aggregation_type}:{row.assessment_report}",
            actor_id=row.actor_id,
            aggregation_type=AggregationType(row.aggregation_type),
            gases_included=row.gases_included,
            assessment_report=AssessmentReport(row.assessment_report),
            year=row.year,
            emissions=row.emissions,
            units=row.units,
            datasource_id=datasource.id,
        ).model_dump()
        for row in df_agg.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=EmissionsTotalCO2e.__tablename__,
        data=emissions_total_co2e_validated,
        mode="w",
    )

if __name__ == "__main__":
    main()