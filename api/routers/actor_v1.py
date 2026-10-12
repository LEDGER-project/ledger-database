import asyncio
from fastapi import APIRouter
import psycopg

from api.db.session import get_connection

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


async def fetch_actors_parts(is_part_of: str, actor_type: str | None = None):
    async with await get_connection() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            if actor_type is None:
                await cur.execute("""
                    SELECT 
                        id, 
                        name, 
                        type, 
                        is_part_of 
                    FROM actor
                    WHERE is_part_of = %s;
                    """,
                    (is_part_of,),
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
                    WHERE is_part_of = %s AND type = %s;
                    """,
                    (is_part_of, actor_type),
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
                WHERE actor_id = %s;
                """,
                (actor_id,),
            )
            rows = await cur.fetchall()
            return rows


async def fetch_actor_emissions(actor_id: str,
                                units: str = "native",                # "native" | "co2e"
                                sum_over: list[str] | None = None,    # ["gas"], ["sector"], ["gas","sector"]
                                datasource: str | None = None,
                                sector: str | None = None,
                                gas: str | None = None,
                                include_lulucf: bool = True,):
    

    sum_over_key = frozenset(sum_over or [])

    # summing over gas requires CO2e
    if "gas" in sum_over_key and units != "co2e":
        raise ValueError("Cannot sum over gas unless units='co2e'")

    # native units cannot be summed over
    if units == "native" and sum_over_key:
        raise ValueError("Cannot use sum_over with units='native'")

    TABLE_DISPATCH = {
        ("native", frozenset()): "emissions",
        ("co2e", frozenset()): "emissionsCO2e",
        ("co2e", frozenset({"gas"})): "emissionsTotalSector",
        ("co2e", frozenset({"gas", "sector"})): "emissionsTotalCO2e"
        }
    
    QUERY_DISPATCH: dict[str, str] = {
        "emissions": """
            SELECT
                e.actor_id,
                e.year,
                e.emissions,
                e.units,
                e.gas,
                s.code AS sector_code,
                s.name AS sector_name,
                s.protocol AS sector_protocol
            FROM emissions e
            JOIN sector s ON e.sector_id = s.id
            WHERE e.actor_id = %(actor_id)s
            AND (%(datasource)s IS NULL OR e.datasource_id = %(datasource)s)
            AND (%(gas)s IS NULL OR e.gas = %(gas)s)
            AND (%(sector)s IS NULL OR s.code = %(sector)s);
        """,

        "emissionsCO2e": """
            SELECT
                e.actor_id,
                e.year,
                e.emissions_co2e AS emissions,
                'CO2e' AS units,
                e.gas,
                s.code AS sector_code,
                s.name AS sector_name,
                s.protocol AS sector_protocol
            FROM emissionsCO2e e
            JOIN sector s ON e.sector_id = s.id
            WHERE e.actor_id = %(actor_id)s
            AND (%(datasource)s IS NULL OR e.datasource_id = %(datasource)s)
            AND (%(gas)s IS NULL OR e.gas = %(gas)s)
            AND (%(sector)s IS NULL OR s.code = %(sector)s);
        """,

        "emissionsTotalSector": """
            SELECT
                e.actor_id,
                e.year,
                e.emissions_co2e AS emissions,
                'CO2e' AS units,
                s.code AS sector_code,
                s.name AS sector_name,
                s.protocol AS sector_protocol
            FROM emissionsTotalSector e
            JOIN sector s ON e.sector_id = s.id
            WHERE e.actor_id = %(actor_id)s
            AND (%(sector)s IS NULL OR s.code = %(sector)s);
        """,

        "emissionsTotalCO2e": """
            SELECT
                e.actor_id,
                e.year,
                e.emissions_co2e AS emissions,
                'CO2e' AS units
            FROM emissionsTotalCO2e e
            WHERE e.actor_id = %(actor_id)s
            AND (%(include_lulucf)s OR e.includes_lulucf = FALSE);
        """,
    }

    table = TABLE_DISPATCH[(units, sum_over_key)]
    query = QUERY_DISPATCH[table]

    params = {
        "actor_id": actor_id,
        "datasource": datasource,
        "gas": gas,
        "sector": sector,
        "include_lulucf": include_lulucf,
        }
    
    async with await get_connection() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            
            await cur.execute(query, params)

            rows = await cur.fetchall()
            return rows


    #await cur.execute(
    #    """
    #    SELECT 
    #        e.actor_id, 
    #        e.year, 
    #        e.emissions, 
    #        e.units, 
    #        e.gas, 
    #        s.code AS sector_code
    #        s.name AS sector_name
    #        s.protocol AS sector_protocol
    #    FROM emissions e
    #    JOIN sector s
    #        ON e.sector_id = s.id
    #    WHERE actor_id = %(actor_id)s 
    #        AND (%(datasource)s IS NULL OR e.datasource_id = %(datasource)s)
    #        AND (%(gas)s IS NULL OR e.gas = %(gas)s)
    #        AND (%(sector)s IS NULL OR s.code = %(sector_code)s);
    #    """,
    #    { 
    #        "actor_id": actor_id, 
    #        "datasource": datasource, 
    #        "gas": gas,
    #        "sector_code": sector
    #    },
    #    )
    
async def fetch_actor_targets(actor_id: str):
    async with await get_connection() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                SELECT 
                    actor_id, 
                    target_type,
                    emissions, 
                    baseline_year, 
                    target_year, 
                    target_value, 
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
    "actor/{actor_id}/energy_consumption",
    tags=["Actors"],
    summary="Actor Energy Consumption",
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
    summary="emission targets of an actor",
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
    summary="emissions of an actor",
    response_description="Time series of emissions for a given actor",
)
async def actor_emissions(
        actor_id, 
        datasource: str | None = None, 
        sector: str | None = None,
        gas: str | None = None):
    """
    Returns time series of emissions
    """
    data = await fetch_actor_emissions(actor_id, datasource, sector, gas)
    return data


