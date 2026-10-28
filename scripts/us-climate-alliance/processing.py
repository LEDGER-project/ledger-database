from datetime import datetime
from pathlib import Path

from models import DataSource, InitiativeType, Initiatives
from utils import write_csv


def main():
    # ------------------------------------------
    # datasource table
    # ------------------------------------------
    datasource_name = "us-climate-alliance"
    longname = "U.S. Climate Alliance"
    publisher = "US Climate Alliance"

    datasource = DataSource(
        id=datasource_name,
        name=longname,
        publisher=publisher,
        published_date=datetime.strptime("2026-10-28", "%Y-%m-%d"),
        version="2026-10-28",
        url="https://usclimatealliance.org/",
    )

    # load data
    # Note: Path(__file__).resolve().parent.parent same as "../"
    data_dir = (
        Path(__file__).resolve().parent.parent.parent / "data" / f"{datasource_name}"
    )
    output_dir = data_dir / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    write_csv(
        output_dir=output_dir,
        name=datasource.__tablename__,
        data=datasource.model_dump(),
        mode="w",
    )

    # ------------------------------------------
    # Initiatives table
    # ------------------------------------------

    # list of actors in US Climate Alliance
    actors_in_alliance = [
        "US-AZ",
        "US-CA",
        "US-CO",
        "US-CT",
        "US-DE",
        "US-HI",
        "US-IL",
        "US-MA",
        "US-MD",
        "US-ME",
        "US-MI",
        "US-MN",
        "US-NC",
        "US-NJ",
        "US-NM",
        "US-NY",
        "US-OR",
        "US-PA",
        "US-RI",
        "US-VA",
        "US-VT",
        "US-WA",
        "US-WI",
    ]

    initiative_id = "us_climate_alliance"

    # model dump returns as dictionary
    initiatives_validated = [
        Initiatives(
            id=f"{actor_id}:{initiative_id}",
            actor_id=actor_id,
            initiative=InitiativeType[initiative_id],
            datasource_id=datasource.id,
        ).model_dump()
        for actor_id in actors_in_alliance
    ]

    write_csv(
        output_dir=output_dir,
        name=Initiatives.__tablename__,
        data=initiatives_validated,
        mode="w",
    )


if __name__ == "__main__":
    main()
