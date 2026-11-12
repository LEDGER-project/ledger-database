from datetime import datetime
from pathlib import Path

import pandas as pd

from utils import write_csv
from models import DataSource, Sector


def main():
    # output directory
    data_dir = Path(__file__).resolve().parent.parent.parent / "data" / "crt-on-nir"
    output_dir = data_dir / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    fl = data_dir / "raw" / "crt.xls"

    # ------------------------------------------
    # DataSource table
    # ------------------------------------------
    datasource_name = "crt"
    publisher = "ipcc"

    datasource = DataSource(
        id=f"{publisher}:{datasource_name}",
        name="Common Reporting Tables (CRT) on NIRS",
        publisher=publisher,
        published_date=datetime.strptime("2015-03-05", "%Y-%m-%d"),
        url="https://unfccc.int/documents/311076",
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
    fl = data_dir / "raw" / "crt.xlsx"

    df_crt = (
        pd.read_excel(fl, sheet_name="Summary1", header=9)
        .loc[lambda x: x["Total national emissions and removals"].str.match(r"^\d", na=False)]
        .assign(
            code=lambda x: x["Total national emissions and removals"].str.split(n=1, expand=True)[0].str.rstrip("."),
            name=lambda x: x["Total national emissions and removals"].str.split(n=1, expand=True)[1].str.rstrip().str.replace(r"(?:\s*\([^)]+\))+$", "", regex=True).str.strip(),
        )
        .assign(
            parent_code = lambda x: x["code"].str.extract(r"^(.*)\.[^.]+$")[0]
        )
        .loc[:, lambda d: ~d.columns.str.contains("^Unnamed")]
        .fillna("")
        .astype({"code": str, "parent_code": str, "name": str})
        .drop(columns=["Total national emissions and removals"])
    )

    # Note: these are not in this particular dataset
    # but they are part of the IPCC guidelines
    # including them to breakdown EPA state inventories
    # see table 2.1 in https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_2_Ch2_Stationary_Combustion.pdf
    df_1A4 = pd.DataFrame(
        [
            ("1.A.4.a", "Commercial", "1.A.4"),
            ("1.A.4.b", "Residential", "1.A.4"),
        ],
        columns=["code", "name", "parent_code"],
    )

    df = pd.concat([df_crt, df_1A4], ignore_index=True).sort_values(by="code")

    sector_validated = [
        Sector(
            id=f"crt:{row.code}",
            code=row.code,
            parent_code=row.parent_code,
            name=row.name,
            taxonomy="Common Reporting Table (CRT)",
            datasource_id=datasource.id,
        ).model_dump()
        for row in df.itertuples()
    ]

    write_csv(
        output_dir=output_dir,
        name=Sector.__tablename__,
        data=sector_validated,
        mode="w",
    )


if __name__ == "__main__":
    main()
