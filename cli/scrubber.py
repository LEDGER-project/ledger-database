import csv
import os
from pathlib import Path
import subprocess

from dotenv import load_dotenv

import pandas as pd
import psycopg
from psycopg import Cursor
from rich import print
from sqlmodel import SQLModel
import typer

import models 

# set the DEFAULT_URL from the .env file
# If running locally it should be 
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DEFAULT_URL = os.getenv("HOST_DATABASE_URL") or os.getenv("DATABASE_URL")
if not DEFAULT_URL:
    raise RuntimeError("DATABASE_URL is not set")

app = typer.Typer(help="Remove a datasource's records from the database.")


def has_datasource_id(curs: Cursor, table: str) -> bool:
    """Return True if the table has a datasource_id column."""
    curs.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = %s
          AND column_name = 'datasource_id'
        """,
        (table,),
    )
    return curs.fetchone() is not None


def scrub_table(curs: Cursor, table: str, datasource_id: str):
    """Delete all rows in a table belonging to a datasource."""
    qry = f'''
    DELETE FROM "{table}"
    WHERE datasource_id = %s
    '''
    curs.execute(qry, [datasource_id])


@app.command()
def datasource(datasource_id: str, url: str = DEFAULT_URL):
    """Scrubs each table's records for a datasource.
    Tables are cleared in reverse dependency order so child rows
    are removed before the rows they reference. Tables without a
    datasource_id column are skipped."""
    # all tables in dependency order, reversed so children go first
    sorted_tables = [table.name for table in SQLModel.metadata.sorted_tables]
    sorted_tables.reverse()

    print(f"[green]scrubbing datasource {datasource_id}")

    with psycopg.connect(url) as conn:
        with conn.cursor() as curs:
            for table in sorted_tables:
                if not has_datasource_id(curs, table):
                    print(f"[yellow]    skipping {table} (no datasource_id column)")
                    continue

                print(f"[green]    scrubbing the {table} table...")
                scrub_table(curs, table, datasource_id)

            conn.commit()

    print(f"[green]\nSuccessfully scrubbed {datasource_id} from the database !!\n")


if __name__ == "__main__":
    app()