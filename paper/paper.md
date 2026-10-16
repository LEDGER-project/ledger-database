---
# Use plain text in the title; do not use backticks for code formatting.
title: 'LEDGER: A platform to retrieve national and subnational emissions data and associated contexual data'
tags:
  - python
  - emissions
  - climate
  - postgres
authors:
  - name: Lucas Gloege
    orcid: 0000-0001-9062-6960
    corresponding: true
    affiliation: "1, 2"
  - name: Jennifer R. Marlon
    orcid: 0000-0002-8299-9609
    affiliation: "3, 4"
  - name: Austin Madson
    orcid: 0000-0001-8039-4908
    affiliation: 4
affiliations:
 - name: Department of Earth and Planetary Sciences, Yale University, New Haven, CT 06511, USA
   index: 1
 - name: Yale Center for Natural Carbon Capture, Yale University, New Haven, CT 06511, USA
   index: 2
 - name: Yale Center for Geospatial Solutions, Yale University, New Haven, CT 06511, USA
   index: 3
 - name: School of the Environment, Yale University, New Haven, CT 06511, USA
   index: 4

date: 12 October 2026
bibliography: paper.bib
---

# Summary

The Linked Environmental Data and Greenhouse Emissions Resource (LEDGER) brings together greenhouse gas emissions inventories and contextual data--including climate targets, population, gross domestic product, and energy consumption--for nation states and subnational actors. It harmonizes these data into a consistent schema and makes them easy to retrieve in an analysis-ready format through an open-source Python client and a Representational State Transfer Application Programming Interface (REST API) [@fielding2000architectural]. LEDGER is designed to streamline the process of analyzing emissions data.

# Statement of need

States, provinces, and cities are increasingly adopting greenhouse gas (GHG) reduction targets [@c2es_state_targets], yet most lack the technical familiarity or resources to continuously track emissions [@lyandres2023state_inventory]. This information is critical for determining whether an actor is on track to meet its climate targets and assessing whether policies are delivering measurable GHG reductions within a given sector [@wei2021keeping,hsu2020performance]. Emissions inventories are produced by different institutions using distinct reporting protocols, sector classifications, spatial boundaries, and units, and are frequently distributed across disparate datasets and file formats, including Excel, CSV, and NetCDF [@lancellotti2025closing]. For example, as part of the Intergovernmental Panel on Climate Change (IPCC) process, countries report annual GHG emissions using standardized electronic reporting tables [@eggleston2006ipcc], while cities often report emissions using the Global Protocol for Community-Scale Greenhouse Gas Emission Inventories (GPC) [@fong2014gpc]. These differences create barriers to assembling comparable emissions data across jurisdictions and make data pre-processing necessary before the data can be analyzed. 

LEDGER addresses these challenges through an open source, publicly accessible relational database that harmonizes emissions inventories and contextual data. One benefit of having emissions and coentextual data in same place is it allows emissions to be decomposed via the Kaya identity [@kaya1989impact,dell2026decomposing], which provides a high-level picture of what is driving emissions. The data in LEDGER is organized using a common schema and can be accessed programmatically through a REST API and a high-level Python client. A schematic of the LEDGER architecture is shown in \autoref{schematic}A, and the database entity-relationship diagram is shown in \autoref{schematic}B. 

![Schematic of the Linked Environmental Data and Greenhouse Emissions Resource  (LEDGER) architecture is shown in A. Raw processed data is ingested in to a relational database. A Representational State Transfer Application Programming Interface (REST API) allows the database to be queried and high-level Python package allows the data to be returned as a Pandas DataFrame. B shows the entity relationship diagram for the LEDGER database, showing the different tables in the database and the relationship between them. \label{schematic}](figures/figure1.png)


# State of the field

A closely related resource to LEDGER is [ClimActor 2.0](https://dataverse.unc.edu/dataset.xhtml?persistentId=doi:10.15139/S3/GGWVVQ) [@manya2026climactor], which compiles climate targets, action plans, and self-reported emission inventories from subnational governments. Climactor 2.0 also provides population, GDP, land cover, and other globally-gridded datasets and provides all the data in tabular datasets. LEDGER has a complementary, but broader,in scope, with a greater emphasis on emissions data and integration across inventory types and spatial scales. LEDGER also includes national inventories, whereas ClimActor 2.0 soley focuses on subnational jurisdictions. Whereas ClimActor 2.0 places particular emphasis on subnational climate targets, plans, and initiatives, LEDGER is designed primarily as an emissions data infrastructure that integrates heterogeneous inventories, third-party estimates, and contextual datasets within a common schema. Finally, LEDGER places an emphasis on programatic access, while ClimActor 2.0 simply provides a suite of files with the data, which requires the user to link them together. 

In addition to ClimActor 2.0, other projects that allow access to emissions data are: 

- [Climate Watch](https://www.climatewatchdata.org/)[@ge2024climate], which compiles emissions data for countries based mainly on data from government agencies.
- [ClimateTRACE](https://climatetrace.org/) combines remote sensing, facility-level information, activity data, and other sources to produce independently estimated emissions at increasingly fine spatial and temporal scales, with data available for countries, cities, and other subnational areas [@lancellotti2025closing]
- [Crosswalk Labs](https://www.crosswalk.io/), which integrates activity datasets with mechanistic models to produce high-resolution emissions estimates for U.S. geographies. 
- [Emissions Database for Global Atmospheric Research (EDGAR)](https://edgar.jrc.ec.europa.eu/) [@crippa2024insights], provides estimates of greenhouse gas emissions by gas, sector, and country on a 0.1&deg; grid. 


# Software design

LEDGER uses a Python-based architecture for all aspects to make the project developer friendly. [SQLModel](https://sqlmodel.tiangolo.com/) defines the database tables and validates data ingested into a [PostgreSQL](https://www.postgresql.org/) relational database [@postgresql18]. We use enumerated types to constain and maintain fields such as gas and assessment report. Raw data are pre-processed before they are ingested into the database to ensure consistent units and to check the data for invalid records. LEDGER exposes the resulting data through a REST API written with [FastAPI](https://fastapi.tiangolo.com/) and a high-level Python client, `ledgerdata`, which abstracts API calls for analysis. The Python client is mainly intended for research purposes while the REST API enables use by web applications. In the subsections below we discuss the database architecture, REST API endpoints, and the `ledgerdata` client.

## Database Architecture

The LEDGER database is designed to support emissions and contextual data across multiple geographic scales, from countries to first-order administrative subdivisions and cities. Each actor's name, and a standardized code to identify them, is stored in the `actor` table. Countries and first-order adminstrative subivisions use ISO 3166 codes and cities are indentified with a [UN/LOCODE](https://unece.org/trade/cefact/unlocode-code-list-country-and-territory). These codes are chosen given that they are internationally accepted standards. Any nation state or subdivision not included in these standards is not included in our database. Also, code representing uninhabitated regions are removed from the database. 

The `actor` table is linked to other tables containing emissions, emission targets, population, GDP, and energy use. This design is flexible enough so additional variables can be added in future releases. Each of these tables also links to a `datasource` table which stores metadata data source and provenance information, such as the publisher of the datasource, version number, and download Uniform Resource Locator (URL).

LEDGER is designed to flexible enough to store raw emission broken down by gas and subsector or aggregate emissions that represent total across multiple sectors and gases with CO$_2$ equivalent units. Emissions records can be represented at multiple levels of sectoral detail, including sector, subsector, and category, and by individual greenhouse gas (CO$_2$, CH$_4$, N$_2$O, and fluorinated gases). National inventories generally follow IPCC reporting categories, whereas subnational inventories may use jurisdiction-specific sector classifications. This approach allows inventories with different reporting structures to be incorporated without requiring all sources to conform to a single sectoral classification. In many cases it is not easy to crosswalk between different sector/subsector classifications.

LEDGER database uses a semantic versioning scheme with the format `YYYY.minor.patch`. The four-digit year (YYYY) serves as the major version, the minor version increments for new features or data additions released during that year, and the patch version increments for bug fixes and other backward-compatible code changes. For instance this version of the database is version 2026.0.0. We chose this versioning system since the database will be updated annually, so this makes it easy to see when the database was last updated. 

## API Endpoints

The LEDGER database is accessed through a RESTful application programming interface (API) [@fielding2000rest] implemented using the Python web framework `FastAPI` [@fastapi]. The API provides programmatic access to GHG emissions data and associated socioeconomic variables stored in a PostgreSQL relational database [@postgresql18]. Each endpoint returns structured responses and allows users to query data for specific actors (e.g., countries, states, provinces, or cities) using unique identifiers. The API supports retrieval of emissions time series, population, GDP, energy consumption, and emissions reduction targets.

The API design emphasizes flexible and reproducible data access. Query parameters allow users to filter emissions data by datasource, gas species, or sector classification. In addition, the emissions endpoint supports multiple aggregation modes, including retrieval of emissions in native units by gas and sector, or conversion to carbon dioxide equivalent (CO\textsubscript{2}e) for aggregated reporting. This design enables efficient integration of LEDGER data into computational workflows, modeling pipelines, and external applications.

The LEDGER API is versioned independently from the database using sequential major versions beginning with `v1`. Separating the database and API versioning allows the underlying data to evolve without requiring changes to the API contract, while API versions can be incremented only when interface changes affect client applications (e.g. LEDGER python client).

Summary of LEDGER API endpoints used to query actors and associated datasets. \texttt{\{actor\_id\}} denotes a path parameter representing the unique identifier of an actor (e.g., country, state, province, or city) in the LEDGER database. Countries, states, and provinces use ISO3 codes while cities use LOCODE. Paramters in square brackets indicates the parameter is optinoal. 

: API endpoints for retrieving actor records, parts of an actors (e.g. states within a country), socioeconomic and energy time series, emissions targets, and greenhouse gas emissions. Optional filters are shown as query parameters. []{label="api-endpoints"}

+-----------------------------------------------------------------------------------------------+
| Endpoint                                                                                      |
+===============================================================================================+
| `/actor`                                                                                      |
+-----------------------------------------------------------------------------------------------+
| `/actor/{actor_id}/parts?type={type}`                                                         |
+-----------------------------------------------------------------------------------------------+
| `/actor/{actor_id}/gdp`                                                                       |
+-----------------------------------------------------------------------------------------------+
| `/actor/{actor_id}/population`                                                                |
+-----------------------------------------------------------------------------------------------+
| `/actor/{actor_id}/energy_consumption`                                                        |
+-----------------------------------------------------------------------------------------------+
| `/actor/{actor_id}/targets`                                                                   |
+-----------------------------------------------------------------------------------------------+
| `/actor/{actor_id}/emissions?datasource={datasource}&sector={sector}&gas={gas}`               |
+-----------------------------------------------------------------------------------------------+

## Python client

`ledgerdata` is the high-level Python interface to the RESTful API, which maps endpoints to Python functions. Path parameters, such as \texttt{actor\_id}, and query parameters, such as `sector`, `gas`, or `datasource`, are exposed as function arguments, including optional parameters. The `ledgerdata` client returns the data as a Pandas `DataFrame`. The client simplifies programmatic access by abstracting away API requests and response handling. The client is available on PyPI (`pip install ledger-api`) or via `uv` (`uv add ledger-api`). The source code is hosted on GitHub to encourage community contributions. The latest version at the time of writing is v0.1 and is archived on Zenodo for long-term preservation.

```python
from ledgerdata import Client

client = Client()

data = (
    client.population(actor_id="US")
    .merge(client.emissions(actor_id="US"), on="year")
    .assign(
        emissions_per_capita=lambda x: x["emissions"] / x["population"]
    )
)
```

# Research impact statement

LEDGER is being used in an ongoing research project to retrieve harmonized greenhouse gas emissions and contextual data to analyze whether U.S states are on track to meet emission targets. Although the project manuscript has not yet been published, a public example is available that demonstrates this use.

![This figure outlines some of the potential use cases for LEDGER. It can be uses for product intercomparisons, since it incorporate multiple data sources; it can be used to quantify part-whole relationship, for instance, does the sum of subnational emissions add up to the national total; it can be used to decompose emissions into sector/subsector or via the Kaya identity; and it can be used to track progress on an actor's emission targets. \label{uses}](figures/figure2.png)

# Acknowledgement 

We acknowledge the [Yale Center for Natural Carbon Capture](https://naturalcarboncapture.yale.edu/) for funding this work. We also thank the pYale Center for Geospatial Solutions](https://geospatial.yale.edu/) for the financial support to host the database and API. We thank the [Yale Center for Research Computing](https://research.computing.yale.edu/), specifically Tom Langford, for guidance and assistance in computation run on the [Bouchet cluster](https://docs.ycrc.yale.edu/clusters/bouchet/).

# AI usage disclosure

No generative AI tools were used in the development of this software, the writing of this manuscript, or the preparation of supporting materials.

# References 
