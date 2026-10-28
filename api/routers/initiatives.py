from fastapi import APIRouter
import psycopg

from db.session import get_connection

router = APIRouter()

async def fetch_initiatives(initiative):
    async with await get_connection() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                "SELECT actor_id, initiative, datasource_id FROM initiatives WHERE initiative = %s;",
                (initiative,),
            )
            rows = await cur.fetchall()
            return rows


@router.get(
    "/initiatives",
    tags=["Initiatives"],
    summary="Retrieve all actors part of the initiative",
)
async def initiatives(initiative: str = "us_climate_alliance"):
    """
    Returns actors part of the initiative
    """
    data = await fetch_initiatives(initiative)
    return data
