from fastapi import APIRouter
import psycopg

from db.session import get_connection

router = APIRouter()


async def fetch_datasource(datasource_id=None):
    async with await get_connection() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            if datasource_id is None:
                await cur.execute("""
                    SELECT 
                        id AS datasource_id,
                        name, 
                        publisher, 
                        published_date, 
                        version, 
                        url
                    FROM datasource;
                """)
            else:
                await cur.execute(
                    """
                    SELECT 
                        id AS datasource_id,
                        name,   
                        publisher,  
                        published_date, 
                        version, 
                        url  
                    FROM datasource
                    WHERE id = %(datasource_id)s;
                    """,
                    {
                        "datasource_id": datasource_id,
                    },
                )
            rows = await cur.fetchall()
            return rows


@router.get(
    "/datasource",
    tags=["Datasource"],
    summary="Datasource information",
)
async def actor_datasource(datasource_id=None):
    """
    Returns datasrouce
    """
    data = await fetch_datasource(datasource_id)
    return data
