# Climate Decision

A Python-based climate data pipeline for Egypt. The project collects weather and climate-related data from multiple sources, processes it, and loads SQL Server database objects for analysis.

## What it does

The pipeline currently:

- Collects historical weather data for Egypt governorates from the Open-Meteo archive API.
- Fetches Wikipedia revision history for the "Climate of Egypt" page.
- Scrapes climate-related tables from the Wikipedia Climate of Egypt page.
- Scrapes historical weather data from Weather Underground.
- Executes the SQL script in `db_scripts/SQLQuery1.sql` to create database objects and load data into SQL Server.

## Project structure

- `main.py` - entry point that runs the ingestion workflow and then the SQL loader.
- `src/ingestion/` - data collection scripts.
- `src/processing/` - data cleaning and analysis scripts.
- `src/database/` - SQL Server loader.
- `data/raw/` - generated CSV outputs.
- `db_scripts/` - SQL scripts for database setup.
- `compose.yaml` - Docker Compose setup for SQL Server and the pipeline container.

## Requirements

Install the Python dependencies listed in [requirements.txt](requirements.txt).

Key packages include:

- pandas
- matplotlib
- requests
- beautifulsoup4
- selenium
- openmeteo-requests
- requests-cache
- retry-requests
- pyodbc
- lxml

## Running locally

1. Install the Python dependencies.
2. Make sure SQL Server is available and accessible.
3. Run the pipeline:

```bash
python main.py
```

To skip the collection stage when the raw CSV files already exist:

```bash
python main.py --skip-collection
```

## Running with Docker

The project includes a Docker Compose setup for SQL Server and the pipeline container.

```bash
docker compose up --build
```

The database service is exposed on port `1433`.

## Output files

The pipeline writes generated data to `data/raw/`, including:

- `Egypt_Weather_2022_2025_Final.csv`
- `wikipedia_revision_history.csv`
- `scraped_climate_insights.csv`
- `egypt_governorates_weather.csv`

## Notes

- The project currently uses a hardcoded Windows base path in `main.py`, so the local workflow is set up for this workspace layout.
- The SQL loader expects the database script at `db_scripts/SQLQuery1.sql`.
- If you change the SQL Server password or database name in `compose.yaml`, update the related loader settings too.
