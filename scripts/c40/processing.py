from datetime import datetime
from pathlib import Path

import pandas as pd

from utils import write_csv
from utils import display_excel_sheets

from models import (
    AggregationType,
    DataSource,
    EmissionsTotalCO2e,
    EmissionsTotalSector,
    Sector,
)

def main():
    datasource_name = "c40-cities"
    publisher = "C40"

    # load data and define output directory
    data_dir = (
        Path(__file__).resolve().parent.parent.parent / "data" / f"{datasource_name}"
    )
    output_dir = data_dir / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # ------------------------------------------
    # DataSource table
    # ------------------------------------------

    datasource = DataSource(
        id=f"{publisher}:{datasource_name}",
        name="GPC inventory data",
        publisher=publisher,
        published_date=datetime.strptime("2025-01-01", "%Y-%m-%d"),
        version="13.02.2015",
        url="https://www.c40knowledgehub.org/s/article/C40-cities-greenhouse-gas-emissions-interactive-dashboard?language=en_US",    )


    write_csv(
        output_dir=output_dir,
        name=DataSource.__tablename__,
        data=datasource.model_dump(),
        mode="w",
    )

    # ------------------------------------------
    # load data
    # ------------------------------------------
    fl = (
        Path.cwd().resolve().parent.parent/ "data" / f"{datasource_name}" / "raw" / "C40_GPC_Database.xlsx"
    )

    # load data
    df_raw = pd.read_excel(fl, sheet_name='GHG Dashboard Data - Inventory')
    df_gpc = pd.read_excel(fl, sheet_name= 'GPC taxonomy')


    columns = [
    'City',
    'Country',
    'Year_calendar',
    'Population',
    'Area',
    'GDP',
    'I.1.1',
    'I.1.2',
    'I.1.3',
    'I.2.1',
    'I.2.2',
    'I.2.3',
    'I.3.1',
    'I.3.2',
    'I.3.3',
    'I.4.1',
    'I.4.2',
    'I.4.3',
    'I.4.4',
    'I.5.1',
    'I.5.2',
    'I.5.3',
    'I.6.1',
    'I.6.2',
    'I.6.3',
    'I.7.1',
    'I.8.1',
    'II.1.1',
    'II.1.2',
    'II.1.3',
    'II.2.1',
    'II.2.2',
    'II.2.3',
    'II.3.1',
    'II.3.2',
    'II.3.3',
    'II.4.1',
    'II.4.2',
    'II.4.3',
    'II.5.1',
    'II.5.2',
    'II.5.3',
    'III.1.1',
    'III.1.2',
    'III.1.3',
    'III.2.1',
    'III.2.2',
    'III.2.3',
    'III.3.1',
    'III.3.2',
    'III.3.3',
    'III.4.1',
    'III.4.2',
    'III.4.3',
    'IV.1',
    'IV.2',
    'V.1',
    'V.2',
    'V.3',
    'VI.1',
    ]

    id_vars = [ 
        'City',
        'Country',
        'Year_calendar',
        'Population',
        'Area',
        'GDP'
        ]

    subsector_codes = [c for c in columns if c not in id_vars]

    rename_dictionary = {
        "Côte d’Ivoire":"Côte d'Ivoire",
        "The Netherlands":"Netherlands",
        "USA":"United States",
        "Colombia ":"Colombia",
        "Vietnam":"Viet Nam",
        "Turkey":"Türkiye"
    }

    df_emissions = (
        df_raw
        .loc[:, columns]
        .melt(
                id_vars=id_vars, value_vars=subsector_codes, var_name="sector", value_name="emissions"
            )
        #.query("emissions not in ['NE', 'IE', 'NO', 'C', 'IE (I.1.1)', 'IE (I.1.1)']")
        .assign(emissions=lambda x: pd.to_numeric(x["emissions"], errors="coerce"))
        .dropna(subset=["emissions"])
        .assign(Country=lambda d: d["Country"].replace(rename_dictionary))
    )


    # ------------------------------------------
    # get actors
    # ------------------------------------------

    fl_actors = (
        Path().cwd().parent.parent
        #Path(__file__).resolve().parent.parent.parent
        / "data"
        / "iso-3166-1"
        / "raw"
        / "countries.csv"
    )

    fl_locode = (
        Path().cwd().parent.parent
        #Path(__file__).resolve().parent.parent.parent
        / "data"
        / "locode"
        / "processed"
        / "actor.csv"
    )


    df_actors = pd.read_csv(fl_actors, keep_default_na=False)[
        ["#country_code_alpha2", "country_code_alpha3", "name_short"]
    ].rename(
        columns={"#country_code_alpha2": "actor_id", "country_code_alpha3": "iso3", "name_short":"name"}
    )

    df_country = (
        df_raw['Country'].drop_duplicates().to_frame()
        .assign(Country=lambda d: d["Country"].replace(rename_dictionary))
        .rename(columns={"Country":"name"})
        .merge(df_actors, on="name", how="left")
    )

    df_locode = (
        pd.read_csv(fl_locode)
        .loc[:,["id", "is_part_of", "name"]]
        .rename(columns={"id":"locode", "name":"city", "is_part_of":"iso"})
        #.loc[lambda df: df["iso"].str.contains("US-", na=False)]
    )


    df_cities = (
        df_emissions[["City", "Country"]]
        .drop_duplicates()
        .rename(columns={"City":"city", "Country":"name"})
        .merge(df_country, on="name")
        .rename(columns={"actor_id":"iso"})
        )
    
    # 'Dhaka North' and Dhaka South do not have Locodes
    # maybe call them BD DAN and BD DAS?
    # 'Ekurhuleni' has no single locode
    #'Ekurhuleni': "", # no single locodoe for this city
    # Manually set the locode fo New York City, Sao Paulo and Washington DC to avoid misnaming them 

    city_rename = {
    "Athens": "Athinai", 
    "Bengaluru":"Bangalore",
    "Bogotá":"Bogota",
    "Chennai":"Chennai (ex Madras)",
    "Copenhagen": "Kobenhavn",
    'Delhi NCT': "Delhi",
    'Durban (eThekwini)': "Durban",
    'Kolkata': "Kolkata (ex Calcutta)",
    'Lisbon': "Lisboa",
    'Medellín': "Medellin",
    'Ciudad de México': "Ciudad de Mexico",
    'Milan': "Milano",
    'Montréal': "Montreal",
    'Mumbai': "Mumbai (ex Bombay)",
    'Rome': "Rome (Roma)",
    'Tel Aviv': "Tel Aviv-Yafo",
    'Tshwane': "Pretoria",
    'Warsaw': "Warszawa",
    }

        
    df_merged = (
        df_cities.assign(city=lambda d: d["city"].replace(city_rename))
        .merge(df_locode.assign(iso = lambda d: d["iso"].apply(lambda x: x[:2])), on=["city", "iso"], how="left")
        .assign(locode=lambda d: d["locode"].mask(d["city"].eq("Washington, DC"), "USWAS"))
        .assign(locode=lambda d: d["locode"].mask(d["city"].eq("New York City"), "USNYC"))
        .assign(locode=lambda d: d["locode"].mask(d["city"].eq("São Paulo"), "BRSAO"))
        ) #.query("locode.isna()"))


    #this also has Population, Area, and GDP that may want to extract
    df_out = (
        df_emissions
        .rename(columns={"City":"city"})
        .assign(city=lambda d: d["city"].replace(city_rename))
        .merge(df_merged[["city", "locode"]], on="city")
        .rename(columns={"locode":"actor_id", "Year_calendar":"year", "sector":"sector_id"})
        .loc[:,["actor_id", "year", "sector_id", "emissions"]]
    )

    # ------------------------------------------
    # Sector table
    # ------------------------------------------

    sector_dictionary = {
        "Stationary": "I",
        "Transport": "II",
        "Waste": "III",
        "IPUU": "IV",
        "AFOLU": "V"
    }

    sector_list = [
            {
                "code": "I",
                "name": "Stationary",
                "description": "Emissions from stationary energy production and use",
                "taxonomy": "GPC",
            },
            {
                "code": "II",
                "name": "Transport",
                "description": "Emissions from fuel combustion for transportation occurring in the city",
                "taxonomy": "GPC",
            },
            {
                "code":  "III",
                "name": "Waste",
                "description": "Emissions from in-boundary waste treatment",
                "taxonomy":  "GPC",
            },
            {
                "code": "IV",
                "name": "IPPU",
                "description": "Emissions from industrial processes and product use occurring within the city boundary",
                "taxonomy":  "GPC",
            },
            {
                "code": "V",
                "name": "AFOLU",
                "description": "Emissions from agricultural, other land-use and landuse-change",
                "taxonomy":  "GPC",
            },
        ]

    df_sector = pd.DataFrame(sector_list)

    df_subsector = (
        df_gpc
        .query("Scope == 1.0")
        .loc[:,["GPC ref", "Description", "Sub-Sector"]]
        .rename(columns = {"GPC ref": "code", "Sub-Sector":"name", "Description": "description"})
        .assign(
            taxonomy = "GPC",
            parent_code = lambda x: x["code"].apply(lambda row: row.split(".")[0]))
    )
    
    df_sector_data = (
        pd.concat([df_sector, df_subsector])
        .fillna("")
        .astype({"code": str, "parent_code": str, "name": str})
        )

    sector_validated = [
        Sector(
            id=f"crt:{row.code}",
            code=row.code,
            parent_code=row.parent_code,
            name=row.name,
            taxonomy=row.taxonomy,
            datasource_id=datasource.id,
        ).model_dump()
        for row in df_sector_data.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=Sector.__tablename__,
        data=sector_validated,
        mode="w",
    )



    # ------------------------------------------
    # emissions table
    # ------------------------------------------
    gases_included="CO2, CH4, N2O, F-gases"
    units="CO2 * tonne / yr"
    
    emissionstotalsector_validated = [
            EmissionsTotalSector(
                id=f"{row.actor_id}:{row.year}:{row.sector_id}",
                actor_id=row.actor_id,
                year=row.year,
                emissions=row.emissions,
                sector_id=row.sector_id,
                gases_included=gases_included,
                units=units,
                datasource_id=datasource.id,
            ).model_dump()
            for row in df_out.itertuples()
        ]

    write_csv(
        output_dir=output_dir,
        name=EmissionsTotalSector.__tablename__,
        data=emissionstotalsector_validated,
        mode="w",
    )

    # ------------------------------------------
    # this aggregates across each sector
    # not sure if want to store this or not
    # ------------------------------------------

    ''' 
    df_emissions_total = (
        df_out
        .merge(df_sector_data[["code", "parent_code"]], left_on="sector_id", right_on="code")
        .groupby(["year", "actor_id", "parent_code"], as_index=False)
        .agg(emissions=("emissions", "sum"))
    )

    df_emissions_total_ex = (
        df_out
        .query("sector_id != 'V.2'")
        .merge(df_sector_data[["code", "parent_code"]], left_on="sector_id", right_on="code")
        .groupby(["year", "actor_id", "parent_code"], as_index=False)
        .agg(emissions=("emissions", "sum"))
    )
    '''

    # ------------------------------------------
    # emissions total
    # ------------------------------------------
    #total emissions
    # this includes land
    df_total_inc = (
        df_out
        .groupby(["year", "actor_id"], as_index=False)
        .agg(emissions=("emissions", "sum"))
        .assign(aggregration_type = "total")
        .sort_values(by=["actor_id", "year"])
    )

    # this excludes land emissions
    df_total_ex = (
        df_out
        .query("sector_id != 'V.2'")
        #.merge(df_sector_data[["code", "parent_code"]], left_on="sector_id", right_on="code")
        .groupby(["year", "actor_id"], as_index=False)
        .agg(emissions=("emissions", "sum"))
        .assign(aggregation_type = "total_ex_lulucf")
        .sort_values(by=["actor_id", "year"])
    )

    df_emissionstotalco2e = pd.concat([df_total_inc, df_total_ex])

    gases_included="CO2, CH4, N2O, F-gases"
    units="CO2 * tonne / yr"
    
    emissionstotalco2e_validated = [
            EmissionsTotalCO2e(
                id=f"{row.actor_id}:{row.year}:{row.sector_id}",
                actor_id=row.actor_id,
                year=row.year,
                emissions=row.emissions,
                sector_id=row.sector_id,
                aggregation_type=AggregationType(row.aggregation_type),
                gases_included=gases_included,
                units=units,
                datasource_id=datasource.id,
            ).model_dump()
            for row in df_emissionstotalco2e.itertuples()
        ]

    write_csv(
        output_dir=output_dir,
        name=EmissionsTotalCO2e.__tablename__,
        data=emissionstotalco2e_validated,
        mode="w",
    )


if __name__ == "__main__":
    main()
