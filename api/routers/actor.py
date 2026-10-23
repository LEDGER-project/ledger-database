from fastapi import APIRouter
import psycopg
from collections import defaultdict

from db.session import get_connection

router = APIRouter()


async def fetch_actors():
    async with await get_connection() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute("""
            SELECT 
                id,
                name, 
                type, 
                is_part_of 
            FROM actor;
            """)
            rows = await cur.fetchall()
            return rows


async def fetch_actors_parts(is_part_of: str, actor_type: str = None):
    async with await get_connection() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            if actor_type is None:
                await cur.execute(
                    """
                    SELECT 
                        id, 
                        name, 
                        type, 
                        is_part_of 
                    FROM actor
                    WHERE is_part_of = %(is_part_of)s;
                    """,
                    {
                        "is_part_of": is_part_of,
                    },
                )
            else:
                await cur.execute(
                    """
                    SELECT 
                        id, 
                        name, 
                        type, 
                        is_part_of
                    FROM actor 
                    WHERE is_part_of = %(is_part_of)s AND type = %(actor_type)s;
                    """,
                    {"actor_type": actor_type, "is_part_of": is_part_of},
                )
            rows = await cur.fetchall()
            return rows


async def fetch_actor_gdp(actor_id: str):
    async with await get_connection() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                SELECT
                    actor_id,
                    year,
                    gdp
                FROM gdp
                WHERE actor_id = %(actor_id)s;
                """,
                {
                    "actor_id": actor_id,
                },
            )
            rows = await cur.fetchall()
            return rows


async def fetch_actor_population(actor_id: str):
    async with await get_connection() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                SELECT
                    actor_id,
                    year,
                    population
                FROM population
                WHERE actor_id = %(actor_id)s;
                """,
                {
                    "actor_id": actor_id,
                },
            )
            rows = await cur.fetchall()
            return rows


async def fetch_energy_consumption(actor_id):
    async with await get_connection() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                SELECT 
                    actor_id,
                    year,
                    consumption,
                    units,
                    fuel_type,
                    energy_source,
                    datasource_id  
                FROM energyconsupmtion 
                WHERE actor_id = %(actor_id)s;
                """,
                {
                    "actor_id": actor_id,
                },
            )
            rows = await cur.fetchall()
            return rows


async def fetch_actor_emissions(actor_id, assessment_report=None):
    async with await get_connection() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            if assessment_report and assessment_report.lower() == "all":
                # Return all data across all assessment reports
                await cur.execute(
                    """
                    SELECT actor_id, year, emissions, units, assessment_report 
                    FROM emissionstotalco2e 
                    WHERE actor_id = %(actor_id)s AND aggregation_type = 'total_ex_lulucf'
                    """,
                    {
                        "actor_id": actor_id,
                    },
                )
                rows = await cur.fetchall()
                return rows

            elif assessment_report:
                # Filter for a specific assessment report
                await cur.execute(
                    """
                    SELECT actor_id, year, emissions, units, assessment_report 
                    FROM emissionstotalco2e 
                    WHERE actor_id = %(actor_id)s AND aggregation_type = 'total_ex_lulucf'
                    AND assessment_report = %(assessment_report)s;
                    """,
                    {
                        "actor_id": actor_id,
                        "assessment_report": assessment_report,
                    },
                )
                rows = await cur.fetchall()
                return rows

            else:
                # No assessment_report specified: find the most recent with data
                await cur.execute(
                    """
                    SELECT actor_id, year, emissions, units, assessment_report 
                    FROM emissionstotalco2e 
                    WHERE actor_id = %(actor_id)s AND aggregation_type = 'total_ex_lulucf'
                    AND assessment_report IN ('AR6','AR5','AR4','AR3','AR2')
                    ORDER BY 
                        CASE assessment_report
                            WHEN 'AR6' THEN 1
                            WHEN 'AR5' THEN 2
                            WHEN 'AR4' THEN 3
                            WHEN 'AR3' THEN 4
                            WHEN 'AR2' THEN 5
                            ELSE 6
                        END
                    """,
                    {
                        "actor_id": actor_id,
                    },
                )
                rows = await cur.fetchall()

                # Group by assessment_report, pick the first with data
                grouped = defaultdict(list)
                for row in rows:
                    grouped[row["assessment_report"]].append(row)

                for ar in ["AR6", "AR5", "AR4", "AR3", "AR2"]:
                    if ar in grouped:
                        return grouped[ar]

                return []


async def fetch_actor_targets(actor_id):
    async with await get_connection() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                SELECT 
                    actor_id, 
                    target_type, 
                    baseline_year, 
                    target_year, 
                    target_value AS percent_reduction, 
                    url 
                FROM targets 
                WHERE actor_id = %(actor_id)s;
                """,
                {
                    "actor_id": actor_id,
                },
            )
            rows = await cur.fetchall()
            return rows


@router.get(
    "/actor",
    tags=["Actors"],
    summary="List all actors",
    response_description="Actor name and identifier",
)
async def read_actors():
    """
    Returns all actors in the database including their name and identifier
    """
    data = await fetch_actors()
    return data


@router.get(
    "/actor/{actor_id}/parts",
    tags=["Actors"],
    summary="Parts of an actor",
    response_description="Actor names and identifiers contained within",
)
async def actor_parts(actor_id: str, type: str = None):
    """
    Returns all the actors within a given actor

    ** add function to filter by `type`, which can be `adm1`, `adm2`, or `city`**
    """
    data = await fetch_actors_parts(actor_id, type)
    return data


@router.get(
    "/actor/{actor_id}/gdp",
    tags=["Actors"],
    summary="GDP of an actor",
    response_description="Time series of GDP for a given actor",
)
async def actor_gdp(actor_id: str):
    """
    Returns time series of GDP
    """
    data = await fetch_actor_gdp(actor_id)
    return data


@router.get(
    "/actor/{actor_id}/population",
    tags=["Actors"],
    summary="Population of an actor",
    response_description="Time series of population for a given actor",
)
async def actor_population(actor_id: str):
    """
    Returns time series of population
    """
    data = await fetch_actor_population(actor_id)
    return data


@router.get(
    "/actor/{actor_id}/energy_consumption",
    tags=["Actors"],
    summary="Energy consumption of an actor",
    response_description="Time series of energy consumption for given actor",
)
async def get_energy_consumption(actor_id: str):
    """
    Returns energy consumption for specific actor
    """
    data = await fetch_energy_consumption(actor_id)
    return data


@router.get(
    "/actor/{actor_id}/targets",
    tags=["Actors"],
    summary="Emission targets of an actor",
    response_description="emission targets for given actor",
)
async def actor_targets(actor_id: str):
    """
    Returns emission targets
    """
    data = await fetch_actor_targets(actor_id)
    return data


@router.get(
    "/actor/{actor_id}/emissions",
    tags=["Actors"],
    summary="Emissions of an actor",
    response_description="Time series of emissions for a given actor",
)
async def actor_emissions(actor_id: str, assessment_report: str = "all"):
    """
    Returns total emissions excluding LULUCF for a particular actor.
    - If assessment_report is provided, filters by that report (or returns all if 'all').
    - If not provided, returns data from the most recent report with data.
    Units are tonnes of CO2-eq.
    """
    data = await fetch_actor_emissions(actor_id, assessment_report)
    return data
