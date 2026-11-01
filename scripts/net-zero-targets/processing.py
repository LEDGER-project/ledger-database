from datetime import datetime
from pathlib import Path

import pandas as pd

from models import DataSource, TargetType, Targets
from utils import write_csv

from utils import climactor_keydict
from utils import get_country_codes
from utils import get_iso_3166_2_codes


def main():
    # ------------------------------------------
    # datasource table
    # ------------------------------------------
    datasource_name = "net-zero-tracker"
    publisher = "Net Zero Tracker"

    datasource = DataSource(
        id=f"{publisher}:{datasource_name}",
        name=datasource_name,
        publisher=publisher,
        published_date=datetime.strptime("2025-06-04", "%Y-%m-%d"),
        version="2025-06-04",
        url="https://zerotracker.net/",
    )

    # load data
    # Note: Path(__file__).resolve().parent.parent same as "../"
    data_dir = (
        Path(__file__).resolve().parent.parent.parent / "data" / f"{datasource_name}"
    )
    output_dir = data_dir / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    # input dataset
    fl = data_dir / "raw" / "current_snapshot_2025-06-04_12-07-45.xlsx"

    # get actors information
    # !note: we are grabbing from the raw dataset
    # may be doing this a lot
    # let's make a function that gets iso2 and iso3 names
    fl_actors = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "iso-3166-1"
        / "raw"
        / "countries.csv"
    )

    df_actors = pd.read_csv(fl_actors)[
        ["#country_code_alpha2", "country_code_alpha3"]
    ].rename(
        columns={"#country_code_alpha2": "actor_id", "country_code_alpha3": "iso3"}
    )

    write_csv(
        output_dir=output_dir,
        name=datasource.__tablename__,
        data=datasource.model_dump(),
        mode="w",
    )

    # some notes on different target types in Net Zero Tracker
    # ['Emissions reduction target', <-- definitely track these
    # 'Absolute emissions target',   <--- this one can be recast into an Emission reduction target
    # 'Reduction v. BAU'             <--- this one can be recast into an Emission reduction target
    # 'Emissions intensity target',  <-- no sure we want to track these
    # 'Net zero', 'Net negative',  'GHG neutral(ity)', 'Carbon neutral(ity)',  <--- these are all similar
    # 'Zero emissions', 'Zero carbon', 'Carbon negative', <-- these are all similar
    # 'Climate positive', 'Climate neutral', <-- these are all similar
    # 'Other',  'No target',  nan] <-- not very useful

    columns_end = [
        "Name",
        "Country",
        "Entity_type",  # ['Country', 'Region', 'City', 'Company']
        "End_target",  # target type
        "End_target_percentage_reduction",
        "End_target_baseline_year",
        "End_target_year",
        "Status_of_end_target",
        "Date_of_last_status_update",
        "End_target_text",
        "End_target_source_url",
    ]

    columns_interim = [
        "Name",
        "Country",  # this is the iso3 code
        "Entity_type",  # this is actor_type
        "Interim_target",
        "Interim_target_year",
        "Interim_target_percentage_reduction",
        "Interim_target_baseline_year",
        "Interim_target_text",
        "End_target_source_url",
    ]

    # ------------------------------------------
    # process countries
    # ------------------------------------------
    # !!todo: validation for url check if start with http:// or https://
    # end targets
    df_end = (
        pd.read_excel(fl, sheet_name="Current Snapshot", header=1)
        .loc[:, columns_end]
        .query(
            "End_target=='Emissions reduction target' and End_target_percentage_reduction.notnull()"
        )
        .query("End_target_baseline_year.notnull()")
        .query("Entity_type=='Country'")
        .rename(
            columns={
                "End_target": "target_type",
                "End_target_year": "target_year",
                "End_target_percentage_reduction": "percent_reduction",
                "End_target_baseline_year": "baseline_year",
                "End_target_text": "target_text",
                "End_target_source_url": "url",
            }
        )
    )

    # interim targets
    df_interim = (
        pd.read_excel(fl, sheet_name="Current Snapshot", header=1)
        .loc[:, columns_interim]
        .query(
            "Interim_target=='Emissions reduction target' and Interim_target_percentage_reduction.notnull()"
        )
        .query("Interim_target_baseline_year.notnull()")
        .query("Entity_type=='Country'")
        .rename(
            columns={
                "Interim_target": "target_type",
                "Interim_target_year": "target_year",
                "Interim_target_percentage_reduction": "percent_reduction",
                "Interim_target_baseline_year": "baseline_year",
                "Interim_target_text": "target_text",
                "End_target_source_url": "url",
            }
        )
    )

    df_tmp = pd.concat([df_end, df_interim])

    # merge on actors to get actor_id
    df_country = (
        pd.merge(df_tmp, df_actors, left_on="Country", right_on="iso3")
        .loc[
            :,
            [
                "actor_id",
                "target_type",
                "percent_reduction",
                "baseline_year",
                "target_year",
                "url",
            ],
        ]
        .fillna({"url": ""})
        .astype(
            {
                "actor_id": str,
                "target_type": str,
                "percent_reduction": float,
                "baseline_year": int,
                "target_year": int,
                "url": str,
            }
        )
        .sort_values(by=["actor_id", "target_year"])
        .drop_duplicates()
    )



    # ------------------------------------------
    # process regions
    # ------------------------------------------

    # actors
    df_actors = get_country_codes()

    df_subdiv = get_iso_3166_2_codes().merge(df_actors.rename(columns={"actor_id":"country_iso2"}), on=["country_iso2"])

    # key dictionary
    df_key = climactor_keydict()

    # 3714
    # ['Region', 'SubRegion', 'City', 'Association']
    df_key_merged = (
        df_key.query("entity_type=='Region'")
        .merge(df_subdiv, left_on=["right_simpl", "iso"], right_on=["name", "iso3"], how="inner") 
    )

    df_regions_raw = (
        pd.read_excel(fl, sheet_name="Current Snapshot", header=1).query("Entity_type=='Region'")
        .loc[:, ["Name", "Country"]]
        .rename(columns={"Country":"iso3", "Name":"name"})
    )

    df_simp = (
        df_regions_raw
        .merge(
            df_key_merged.loc[:,["right_simpl", "iso3","actor_id"]], 
            left_on=["name", "iso3"],
            right_on=["right_simpl", "iso3"], 
            how="inner")
        .drop_duplicates()
    )

    df_wrong = (
        df_regions_raw
        .merge(
            df_key_merged.loc[:,["wrong", "iso3","actor_id"]], 
            left_on=["name", "iso3"], 
            right_on=["wrong", "iso3"], 
            how="inner")
        .drop_duplicates()
    )

    #-----------------------
    # these
    #-----------------------

    columns_end = [
        "Name",
        "Country",
        "Entity_type",  # ['Country', 'Region', 'City', 'Company']
        "End_target",  # target type
        "End_target_percentage_reduction",
        "End_target_baseline_year",
        "End_target_year",
        "Status_of_end_target",
        "Date_of_last_status_update",
        "End_target_text",
        "End_target_source_url",
    ]

    columns_interim = [
        "Name",
        "Country",  # this is the iso3 code
        "Entity_type",  # this is actor_type
        "Interim_target",
        "Interim_target_year",
        "Interim_target_percentage_reduction",
        "Interim_target_baseline_year",
        "Interim_target_text",
        "End_target_source_url",
    ]

    # ------------------------------------------
    # process raw data
    # ------------------------------------------
    # !!todo: validation for url check if start with http:// or https://
    # end targets
    df_end = (
        pd.read_excel(fl, sheet_name="Current Snapshot", header=1)
        .loc[:, columns_end]
        .query(
            "End_target=='Emissions reduction target' and End_target_percentage_reduction.notnull()"
        )
        .query("End_target_baseline_year.notnull()")
        .query("Entity_type=='Region'")
        .rename(
            columns={
                "End_target": "target_type",
                "End_target_year": "target_year",
                "End_target_percentage_reduction": "percent_reduction",
                "End_target_baseline_year": "baseline_year",
                "End_target_text": "target_text",
                "End_target_source_url": "url",
            }
        )
    )

    # interim targets
    df_interim = (
        pd.read_excel(fl, sheet_name="Current Snapshot", header=1)
        .loc[:, columns_interim]
        .query(
            "Interim_target=='Emissions reduction target' and Interim_target_percentage_reduction.notnull()"
        )
        .query("Interim_target_baseline_year.notnull()")
        .query("Entity_type=='Region'")
        .rename(
            columns={
                "Interim_target": "target_type",
                "Interim_target_year": "target_year",
                "Interim_target_percentage_reduction": "percent_reduction",
                "Interim_target_baseline_year": "baseline_year",
                "Interim_target_text": "target_text",
                "End_target_source_url": "url",
            }
        )
    )

    df_tmp = pd.concat([df_end, df_interim]).dropna(subset=['target_year'])

    #196
    df_simpl_merged = (
        df_tmp
        .merge(
            df_simp.loc[:,["right_simpl", "iso3", "actor_id"]], 
            left_on=["Name", "Country"], 
            right_on=["right_simpl", "iso3"], 
            how="inner")
        .drop(columns=["right_simpl"])
    )

    df_wrong_merged = (
        df_tmp
        .merge(
            df_wrong.loc[:,["wrong", "iso3", "actor_id"]], 
            left_on=["Name", "Country"], 
            right_on=["wrong", "iso3"], 
            how="inner")
        .drop(columns=["wrong"])
    )

    # this is good data
    df_concat = pd.concat([df_simpl_merged, df_wrong_merged]).drop_duplicates()


    data = [
        ("Thuringia", "DEU", "DE-TH"),
        ("Navarra", "ESP", "ES-NA"), # could me autonomous community
        #("México State", "MEX", ""),
        ("Nuevo León", "MEX", "MX-NLE"),
        ("Paraíba", "BRA", "BR-PB"),
        ("Center-Loire Valley", "FRA", "FR-CVL"),
        ("Grand Est", "FRA", "FR-GES"),
        ("Pays de la Loire", "FRA", "FR-PDL"),
        ("Andalusia", "ESP", "ES-AN"),
        ("Basque Autonomous Community", "ESP", "ES-PV"),
        ("Guangxi", "CHN", "CN-GX"),
        ("Melaka", "MYS", "MY-04"),
        ("Aragon", "ESP", "ES-AR"),
        ("Chartered Community of Navarre", "ESP", "ES-NC"),
        ("Region of Murcia", "ESP", "ES-MC"),
        ("Penghu", "TWN", "TW-PEN"),
        ("Corsica", "FRA", "FR-20R"),
        ("Piedmont", "ITA", "IT-21"),
        ("Baden-Württemberg", "DEU", "DE-BW"),
        ("Jeju", "KOR", "KR-49"),
        ("Auvergne-Rhône-Alpes", "FRA", "FR-ARA"),
        ("Catalonia", "ESP", "ES-CT"),
        ("Hebei", "CHN", "CN-HE"),
        ("Maharashtra", "IND", "IN-MH"),
        ("Federal District", "MEX", "MX-CMX"),
        ("Community of Madrid", "ESP", "ES-MD"),
        ("Kinmen", "TWN", "TW-KIN"),
        ("Pingtung", "TWN", "TW-PIF"),
        ("Yilan", "TWN", "TW-ILA"),
        ("Anhui", "CHN", "CN-AH"),
        ("Fujian", "CHN", "CN-FJ"),
        ("Gansu", "CHN", "CN-GS"),
        ("Henan", "CHN", "CN-HA"),
        ("Hunan", "CHN", "CN-HN"),
        ("Liaoning Province", "CHN", "CN-LN"),
        ("Qinghai", "CHN", "CN-QH"),
        ("Shaanxi", "CHN", "CN-SN"),
        ("Shandong Province", "CHN", "CN-SD"),
        ("Zhejiang", "CHN", "CN-ZJ"),
        ("Ningxia", "CHN", "CN-NX"),
        ("Special Capital Region of Jakarta", "IDN", "ID-JK"),
        ("North Kazakhstan", "KAZ", "KZ-59"),
        ("Chiayi", "TWN", "TW-CYI"), #maybe the county, maybe remove
        ("Nantou", "TWN", "TW-NAN"),
        ("São Paulo", "BRA", "BR-SP"),
    ]

    df_replace = pd.DataFrame(data, columns=["Name", "Country", "actor_id"])


    # do these by hand
    df_by_hand = (
        df_tmp.drop_duplicates()
        .merge(df_concat.loc[:,["Name", "Country"]].drop_duplicates(), how="left_anti")
        .merge(df_replace, on=["Name", "Country"], how="left").dropna(subset=["actor_id"])
        #.merge(df_subdiv.drop_duplicates(), left_on=["Name", "Country"], right_on=["name", "iso3"], how="inner")
    )

    # this is perfect data
    df = pd.concat([df_concat, df_by_hand]).dropna(subset=["actor_id"])

    # merge on actors to get actor_id
    df_regions = (
        pd.concat([df_concat, df_by_hand]).dropna(subset=["actor_id"])
        .loc[
            :,
            [
                "actor_id",
                "target_type",
                "percent_reduction",
                "baseline_year",
                "target_year",
                "url",
            ],
        ]
        .fillna({"url": ""})
        .astype(
            {
                "actor_id": str,
                "target_type": str,
                "percent_reduction": float,
                "baseline_year": int,
                "target_year": int,
                "url": str,
            }
        )
        .sort_values(by=["actor_id", "target_year"])
        .drop_duplicates()
    )

    # ------------------------------------------
    # concat regions and countries
    # ------------------------------------------

    df = pd.concat([df_country, df_regions])

    # ------------------------------------------
    # target table
    # ------------------------------------------
    target_type = TargetType.absolute_reduction

    # model dump returns as dictionary
    targets_validated = [
        Targets(
            id=f"{row.actor_id}:{target_type.value.replace(' ', '-')}:{row.baseline_year}:{row.target_year}",
            actor_id=row.actor_id,
            target_type=target_type,
            target_value=row.percent_reduction,
            baseline_year=row.baseline_year,
            target_year=row.target_year,
            url=row.url,
            datasource_id=datasource.id,
        ).model_dump()
        for row in df.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=Targets.__tablename__,
        data=targets_validated,
        mode="w",
    )


if __name__ == "__main__":
    main()
