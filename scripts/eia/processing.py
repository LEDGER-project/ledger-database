from datetime import datetime
from pathlib import Path

import pandas as pd

from utils import write_csv
from models import (
    GasType,
    DataSource,
    Emissions,
    EnergyConsumption
)


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
    datasource_name = "state-energy-data-system"
    publisher = "EIA"

    datasource = DataSource(
        id=f"{publisher}:{datasource_name}",
        name="State Energy Data System (SEDS): 1960-2024 (complete)",
        publisher=publisher, 
        published_date=datetime.strptime("2026-06-26", "%Y-%m-%d"),
        version="20260626",
        url="https://www.eia.gov/state/seds/seds-data-complete.php#Keystatisticsrankings",
    )

    # load data and define output directory
    data_dir = (
        Path().cwd().resolve().parent.parent / "data" / "eia"
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
    df_sector= get_crt_sector().rename(columns={"id": "sector_id"}).query("code.isin(['1'])")

    # ------------------------------------------
    # load raw data and process
    # ------------------------------------------
    fl_energy = (
        Path().cwd().parent.parent
        / "data"
        / "eia"
        / "raw"
        / "use_energy_source.xlsx"  
    )

    fl_co2 = (
        Path().cwd().parent.parent
        / "data"
        / "eia"
        / "raw"
        / "co2_total.xlsx"
    )

    YEAR_START = 1960
    YEAR_END = 2024

    # ------------------------------------------
    # Energy Consumption
    # ------------------------------------------

    sheets = [
        'Coal',
        'Natural gas',
        'Petroleum',
        'Nuclear',
        'Total renewable energy'
    ]

    id_vars = ["State"]
    value_vars = [num for num in range(YEAR_START, YEAR_END+1)]

    dfs = []

    for sheet_name in sheets:
        df_tmp = (
            pd.read_excel(fl_energy, sheet_name=sheet_name, header=2)
            .query("State != 'US'")
            .melt(
                id_vars=id_vars,
                value_vars=value_vars,
                value_name="consumption",
                var_name="year",
            )
            .query("consumption >0")
            .assign(
                    actor_id=lambda x: x.apply(
                        lambda row: f"US-{row["State"]}",
                        axis=1,
                    ),
                    units = "GBtu",
                    energy_source = "renewable" if sheet_name == "Total renewable energy" else "nuclear" if sheet_name == "Nuclear" else "fossil",
                    fuel_type = sheet_name.lower()
            )
        )

        dfs.append(df_tmp)

    df = pd.concat(dfs)

    energy_consumption_validated = [
        EnergyConsumption(
            id=f"{row.actor_id}:{row.year}:{row.fuel_type}:{row.energy_source}",
            actor_id=row.actor_id,
            year=row.year,
            consumption=row.consumption,
            units=row.units,
            fuel_type=row.fuel_type,
            energy_source=row.energy_source,
            datasource_id=datasource.id,
        ).model_dump()
        for row in df.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=EnergyConsumption.__tablename__,
        data=energy_consumption_validated,
        mode="w",
    )

    # ------------------------------------------
    # Emissions
    # ------------------------------------------

    id_vars = ["State"]
    value_vars = [num for num in range(YEAR_START, YEAR_END+1)]

    MMT_TO_TONNES= 1_000_000

    df_co2 = (
            pd.read_excel(fl_co2, sheet_name="Total CO2", header=2)
            .query("State != 'US'")
            .melt(
                id_vars=id_vars,
                value_vars=value_vars,
                value_name="emissions",
                var_name="year",
            )
            .query("emissions >0")
            .assign(
                    emissions = lambda x: x["emissions"]*MMT_TO_TONNES,
                    actor_id=lambda x: x.apply(
                        lambda row: f"US-{row["State"]}",
                        axis=1,
                    ),
                    units = "CO2 * tonne",
                    gas = "CO2",
                    sector_id = df_sector.sector_id.values[0]
            )
    )

    emissions_validated = [Emissions(
        id = f"{row.actor_id}:{row.year}:{row.gas}:{row.sector_id}",
        actor_id = row.actor_id,
        gas = GasType(row.gas),
        sector_id = row.sector_id,
        year = row.year,
        emissions = row.emissions,
        units = row.units,
        datasource_id =  datasource.id,
        ).model_dump()
        for row in df_co2.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=Emissions.__tablename__,
        data=emissions_validated,
        mode="w",
    )


if __name__ == "__main__":
    main()