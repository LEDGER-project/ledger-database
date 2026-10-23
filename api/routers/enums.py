from fastapi import APIRouter
import psycopg

from db.session import get_connection

router = APIRouter()


async def fetch_type(type_name):
    async with await get_connection() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                SELECT e.enumlabel
                FROM pg_type AS t
                JOIN pg_enum AS e ON e.enumtypid = t.oid
                JOIN pg_namespace AS n ON n.oid = t.typnamespace
                WHERE n.nspname = current_schema()
                AND t.typname = %(type_name)s
                ORDER BY e.enumsortorder;
                """,
                {
                    "type_name": type_name,
                },
            )
            rows = await cur.fetchall()
            return rows


@router.get(
    "/enum/actor",
    tags=["Enumerated Types"],
    summary="Types of actors",
)
async def enum_actor():
    data = await fetch_type("actortype")
    return data


@router.get(
    "/enum/assessment_report",
    tags=["Enumerated Types"],
    summary="Types of assessment reports",
)
async def enum_assessment_report():
    data = await fetch_type("assessmentreport")
    return data


@router.get(
    "/enum/target",
    tags=["Enumerated Types"],
    summary="Types of emission targets",
)
async def enum_target():
    data = await fetch_type("targettype")
    return data


@router.get(
    "/enum/aggregation",
    tags=["Enumerated Types"],
    summary="Types of emission aggregations",
)
async def enum_aggregation():
    data = await fetch_type("aggregationtype")
    return data
