import csv
from pathlib import Path
from typing import List
from typing import Dict

import pandas as pd


def get_iso_3166_2_codes():
    """get subdision codes
    returns dataframe with actor_id and iso3 code for countries
    """
    fl_actors = (
        Path().cwd().parent.parent
        / "data"
        / "iso-3166-2"
        / "raw"
        / "subdivisions.csv"
    )

    df_actors = pd.read_csv(fl_actors)[
        ["#country_code_alpha2", "subdivision_code_iso3166-2", "subdivision_name"]
    ].rename(
        columns={"subdivision_code_iso3166-2": "actor_id", "subdivision_name":"name", "#country_code_alpha2": "country_iso2"}
    )
    return df_actors



def get_country_codes():
    """get country codes
    returns dataframe with actor_id and iso3 code for countries
    """
    fl_actors = (
        Path().cwd().parent.parent
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
    return df_actors


def climactor_keydict(all_columns: bool=False):
    file = Path(__file__).resolve().parent.parent /"data" / "climactor" / "raw" /  "ClimActor_1_keydict.parquet"

    columns = [
        'right',
        'wrong',
        'iso',
        'entity_type',
        'right_simpl',
        'ent_type_eng',
        'ent_type_local',
        'admin1_code',
        'GDAM_id',
    ]

    if all_columns:
        return pd.read_parquet(file) 
    else:
        return pd.read_parquet(file).loc[:, columns]


def write_csv(
    output_dir: str = None,
    name: str = None,
    data: List[Dict] | Dict = None,
    mode: str = "w",
    extension: str = "csv",
) -> None:
    """converts dictionary to CSV"""
    if isinstance(data, dict):
        data = [data]

    file = Path(output_dir).resolve() / f"{name}.{extension}"
    with file.open(mode=mode) as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)


def display_excel_sheets(fl):
    return pd.ExcelFile(fl).sheet_names
