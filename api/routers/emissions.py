from fastapi import APIRouter, Query
import psycopg
from collections import defaultdict

from db.session import get_connection

router = APIRouter()


async def fetch_actor_emissions(actor_id, assessment_report=None):
    async with await get_connection() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            if assessment_report and assessment_report.lower() == "all":
                # Return all data across all assessment reports
                await cur.execute(
                    """
                    SELECT actor_id, year, emissions, units, assessment_report 
                    FROM emissionstotalco2e 
                    WHERE actor_id = %s AND aggregation_type = 'total_ex_lulucf'
                    """,
                    (actor_id,),
                )
                rows = await cur.fetchall()
                return rows

            elif assessment_report:
                # Filter for a specific assessment report
                await cur.execute(
                    """
                    SELECT actor_id, year, emissions, units, assessment_report 
                    FROM emissionstotalco2e 
                    WHERE actor_id = %s AND aggregation_type = 'total_ex_lulucf'
                    AND assessment_report = %s;
                    """,
                    (actor_id, assessment_report),
                )
                rows = await cur.fetchall()
                return rows

            else:
                # No assessment_report specified: find the most recent with data
                await cur.execute(
                    """
                    SELECT actor_id, year, emissions, units, assessment_report 
                    FROM emissionstotalco2e 
                    WHERE actor_id = %s AND aggregation_type = 'total_ex_lulucf'
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
                    (actor_id,),
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


@router.get("/emissions/{actor_id}", tags=["emissions"])
async def actor_emissions(
    actor_id: str,
    assessment_report: str = Query(
        None,
        description="Filter by assessment report (e.g. AR6), or use 'all' to get all data",
    ),
):
    """
    Returns total emissions excluding LULUCF for a particular actor.
    - If assessment_report is provided, filters by that report (or returns all if 'all').
    - If not provided, returns data from the most recent report with data.
    Units are tonnes of CO2-eq.
    """
    data = await fetch_actor_emissions(actor_id, assessment_report)
    return data


#####


async def fetch_actor_emissions_old(
    actor_id: str,
    units: str = "native",  # "native" | "co2e"
    sum_over: list[str] = None,  # ["gas"], ["sector"], ["gas","sector"]
    datasource: str = None,
    sector: str = None,
    gas: str = None,
    include_lulucf: bool = True,
):

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
        ("co2e", frozenset({"gas", "sector"})): "emissionsTotalCO2e",
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

    # await cur.execute(
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
