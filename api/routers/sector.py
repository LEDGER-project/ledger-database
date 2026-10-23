from fastapi import APIRouter
import psycopg

from db.session import get_connection

router = APIRouter()


async def fetch_sector():
    async with await get_connection() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(
                """
                SELECT 
                    code,
                    parent_code, 
                    name,  
                    taxonomy, 
                    description,
                    datasource_id 
                FROM sector;
                """,
            )
            rows = await cur.fetchall()
            return rows


@router.get(
    "/sector",
    tags=["Emissions Contextual Data"],
    summary="Sectors",
)
async def sector():
    """
    Returns all sectors
    """
    data = await fetch_sector()
    return data
