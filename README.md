# The Linked Environmental Data and Greenhouse Emissions Resource (LEDGER)

LEDGER provides comprehensive data on greenhouse gas (GHG) emissions and contextual data (e.g. climate targets, GDP, population, and energy consumption), focusing on both national and subnational actors. The goal of lEDGER is to create a comprehensive, open source database that serves as a reliable resource for researchers, policymakers, and stakeholders. LEDGER is written entirely in Python to facilitate easier collaboration, maintainability, and integration with the broader data science ecosystem. 

## Project Structure

```sh
.
├── LICENSE          # Project license specifying usage terms
├── README.md        # Project overview and setup
├── compose.yml      # Docker Compose defining container setup
├── data/            # Raw or processed data files. Created after you run dvc pull
├── data.dvc        # Data Version Control tracking file for data/
├── migrations/     # Migration scripts to manage DB schema
├── models/         # SQLModel defintitions
├── pyproject.toml  # Python project metadata and dependencies
├── scripts/        # Scripts to process raw data
└── utils/          # Helper functions and common utilities
```

## Python Envionrment setup
We use [uv](https://docs.astral.sh/uv/) as our package manager for this project. If you want a crash course in `uv`, I suggest [Corey Schafer's tutorial](https://www.youtube.com/watch?v=AMdG7IjgSPM). The steps below will outline how to get started:

1. See the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/) to find instructions on how to install `uv` for your operating system. If you are on MacOS, and use the [homebrew](https://brew.sh/) package manager, then you can use the following command:
```sh
brew install uv
```
2. Once installed, you can setup your virtual environment with the following command:
```sh
uv sync
```
3. Now install the project’s own code (e.g. `models` and `utils` packages) into your Python environment in editable mode.
```sh
uv pip install -e .
```
This makes it so you can include `import utils` or `import models` into your scripts. 

That's all there is to it because all the information to setup the environment is in the `uv.lock` and `pyproject.toml` files.

> [!NOTE]
> We may have to add additional packages in the future. In that case, use `uv add PackageName` to update `pyproject.toml` and `uv.lock`. Then open a merge request to update the `.toml` and `.lock` files.


## Database Setup

We use [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/) to setup the database. Here are the steps to get start developing the database locally.

1. Make sure you have [Docker](https://docs.docker.com/get-started/get-docker/) installed on your machine.
2. Make sure you are in the same directory as this `README.md` file.
3. Copy the command below to rename the environment variable file. This creates environment variables so you can access the database in the following steps:
```sh
mv ./.env-example ./.env
```
4. Run the following command to start the database in a container and expose it on localhost port 5432:
```sh
docker-compose up -d
```

How you have an empty [Postgres](https://www.postgresql.org/) database server running in a Docker container. Any data you add to the database will persist in a docker volume. What this means is the data will persist after you stop the container or even remove the container.

### Query the database
There is no data in here ... yet. But when there is, one tool you can use is `psql` to send SQL queries to the database. Here the connection string:

```sh
psql -h localhost -p 5432 -U postgres -W -d ledger
```

Alternatively, you could use a scripting language such as Python with the `psycopg` package to query the database. Dealer's choice.

### Stopping the database

Use the folling command
```sh
docker-compose down
```


## Database migrations

We use [alembic](https://alembic.sqlalchemy.org/en/latest/) for migrations and have it setup to autogenerate. What this means is all you have to do is change the schema in `models/models.py`. Then to create the migration file you run the following:

```sh
alembic revision --autogenerate -m "put message here" --rev-id $(date +"%Y%m%d%H%M%S")
```

this will create a new migration file with your given message in `./migrations/versions/`, it will use the timestamp as the revision `id`

Use the following command to apply the change:

```sh
alembic upgrade head
```

> [!NOTE]
> since we are still in development phase, let's stick with a single migration file for the time being


> [!NOTE]
> had to update `env.py` so knows about `.env`, made sure `.env` was right and update `scriptpy.mako` so imports `sqlmodel`

## Snakemake Workflows

Once the raw data is processed with scripts, the data can be imported into the data with [snakemake](https://snakemake.readthedocs.io/en/stable/) rules. To populate the database, navigate to `/workflows/populate_database` and run `snakemake -j 1` this runs the snakemake rules on a single CPU. These rules ensure the data is imported in dependency order.

## Wiping the database

If you absolutely have to wipe the database for some reason and re-import the data, here are the steps you should follow:

1. `psql` into the database
2. run ` DROP SCHEMA public CASCADE; CREATE SCHEMA public;`
3. run `alembic upgrade head` to rebuild the tables. You may have to delete the version and rerun `alembic revision ...`
4. populate the database by navigating to workflows/populate_database and run `snakemake -j 1`