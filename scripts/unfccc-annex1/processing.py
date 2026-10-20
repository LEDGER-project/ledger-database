from datetime import datetime
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from utils import write_csv

from models import (
    DataSource,
    GasType,
    EmissionsTotalCO2e,
    EmissionsTotalSector,
    AggregationType,
)


if __name__ == "__main__":
    # load data and define output directory
    data_dir = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "unfccc-annex1"
        / "processed"
    )
    output_dir = data_dir / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------
    # DataSource table
    # ------------------------------------------
    datasource_name = "ghg-profiles-annex-1"
    publisher = "UNFCCC"

    datasource = DataSource(
        id=f"{publisher}:{datasource_name}",
        name="GHG Profiles - Annex I",
        publisher=publisher,
        published_date=datetime.strptime("2025-10-28", "%Y-%m-%d"),
        version="20251028",
        url="https://di.unfccc.int/ghg_profile_annex1",
    )

    write_csv(
        output_dir=output_dir,
        name=DataSource.__tablename__,
        data=datasource.model_dump(),
        mode="w",
    )

    # ------------------------------------------
    # get actors
    # change Path(__file__) to Path.cwd() if using notebook
    # and will have to remove one of the .parent
    # ------------------------------------------
    fl_actors = (
         Path(__file__).resolve().parent.parent.parent
        / "data"
        / "iso-3166-1"
        / "raw"
        / "countries.csv"
    )

    df_actors = (
        pd.read_csv(fl_actors, keep_default_na=False)
        .loc[:, ["#country_code_alpha2", "country_code_alpha3"]]
        .rename(
            columns={"#country_code_alpha2": "alpha2", "country_code_alpha3": "alpha3"}
        )
    )

    # ------------------------------------------
    # get sector codes
    # ------------------------------------------
    fl_codes = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "crt-on-nir"
        / "processed"
        / "sector.csv"
    )

    df_codes = (
        pd.read_csv(fl_codes)
        .rename(columns={"id": "sector_id"})
        .loc[:, ["sector_id", "code", "name"]]
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
    # EmissionsTotalSector
    # ------------------------------------------

    files = (
         Path(__file__).resolve().parent.parent.parent/ "data" / "unfccc-annex1" / "raw"
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
                    d.index[
                        d["GHG emissions, kt CO2 equivalent"].eq(
                            "Breakdown by sub-sectors"
                        )
                    ][0]
                    + 1,
                    d.index[
                        d["GHG emissions, kt CO2 equivalent"].eq(
                            "Average annual change, in percent"
                        )
                    ][0],
                )
            ]
            .drop(columns=["Base year"], errors="ignore")
            .drop(
                columns=["1990.1"], errors="ignore"
            )  # this shows in KAZ for some reason
            .melt(
                id_vars="GHG emissions, kt CO2 equivalent",
                var_name="year",
                value_name="emissions_kt_co2_eq",
            )
            .rename(columns={"GHG emissions, kt CO2 equivalent": "sector"})
            .loc[
                lambda d: pd.to_numeric(
                    d["emissions_kt_co2_eq"], errors="coerce"
                ).notna()
            ]
            .assign(
                code=lambda d: d["sector"].str.split(" ", n=1).str[0],
                name=lambda d: d["sector"].str.split(" ", n=1).str[1],
                emissions=lambda d: d["emissions_kt_co2_eq"] * kt_to_tonne,
                units="CO2 * tonne / yr",
            )
            .assign(
                code=lambda d: d["code"].str.rstrip("."),
                actor_id=actor_id,
                gases_included="KYOTOGHGS",
                datasource_id=datasource.id,
            )
            .merge(df_codes, on=["code"])
            .loc[
                :,
                [
                    "sector_id",
                    "actor_id",
                    "year",
                    "emissions",
                    "units",
                    "datasource_id",
                    "gases_included",
                ],
            ]
            .astype(
                {
                    "sector_id": str,
                    "actor_id": str,
                    "year": int,
                    "emissions": float,
                    "datasource_id": str,
                    "gases_included": str,
                    "units": str,
                }
            )
        )

        list_of_dfs.append(df_tmp)

    df_totalsector = pd.concat(list_of_dfs).astype(
        {"actor_id": str, "year": int, "emissions": float, "units": str}
    )

    emissionstotalsector_validated = [
        EmissionsTotalSector(
            id=f"{row.actor_id}:{row.year}:{row.sector_id}",  # don't know assessment_report
            actor_id=row.actor_id,
            sector_id=row.sector_id,
            year=row.year,
            emissions=row.emissions,
            units="CO2 tonnes / yr",
            gases_included=GasType(row.gases_included),
            datasource_id=datasource.id,
        ).model_dump()
        for row in df_totalsector.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=EmissionsTotalSector.__tablename__,
        data=emissionstotalsector_validated,
        mode="w",
    )

    # ------------------------------------------
    # EmissionsTotalCO2e
    # aggregated
    # ------------------------------------------

    keys = ["actor_id", "year", "units", "datasource_id", "gases_included"]

    df_agg_total = (
        df_totalsector.query(
            "sector_id.isin(['crt:1','crt:2','crt:3','crt:4','crt:5','crt:6'])"
        )
        .groupby(keys, as_index=False)
        .agg({"emissions": "sum"})
        .reset_index()
        .assign(aggregation_type="total")
    )

    df_agg_total_ex_lulucf = (
        df_totalsector.query(
            "sector_id.isin(['crt:1','crt:2','crt:3','crt:5','crt:6'])"
        )
        .groupby(keys, as_index=False)
        .agg({"emissions": "sum"})
        .reset_index()
        .assign(aggregation_type="total_ex_lulucf")
    )

    df_agg = pd.concat([df_agg_total, df_agg_total_ex_lulucf])

    # finish this
    emissionstotalco2e_validated = [
        EmissionsTotalCO2e(
            id=f"{row.actor_id}:{row.year}:{row.aggregation_type}",
            actor_id=row.actor_id,
            year=row.year,
            emissions=row.emissions,
            aggregation_type=AggregationType(row.aggregation_type),
            units="CO2 tonnes / yr",
            gases_included=row.gases_included,
            datasource_id=datasource.id,
        ).model_dump()
        for row in df_agg.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=EmissionsTotalCO2e.__tablename__,
        data=emissionstotalco2e_validated,
        mode="w",
    )
