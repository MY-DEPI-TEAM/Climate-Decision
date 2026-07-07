```
Climate-Decision
├─ .dockerignore
├─ compose.yaml
├─ data
│  ├─ lakehouse
│  │  └─ gold
│  │     ├─ fact_weather.parquet
│  │     └─ ml_ready.parquet
│  ├─ parsed
│  │  └─ wikipedia_revision_history_clean.csv
│  └─ raw
│     ├─ current_year
│     │  ├─ Egypt_Weather_2026_01.csv
│     │  ├─ Egypt_Weather_2026_02.csv
│     │  ├─ Egypt_Weather_2026_03.csv
│     │  ├─ Egypt_Weather_2026_04.csv
│     │  ├─ Egypt_Weather_2026_05.csv
│     │  └─ Egypt_Weather_2026_06.csv
│     ├─ egypt_governorates_weather.csv
│     ├─ Egypt_Weather_2022_2025_Final.csv
│     ├─ scraped_climate_insights.csv
│     └─ wikipedia_revision_history.csv
├─ db_scripts
│  ├─ Azure.sql
│  └─ Locally.sql
├─ Dockerfile
├─ lakehouse
│  ├─ bronze
│  │  ├─ access.py
│  │  └─ __init__.py
│  ├─ gold
│  │  ├─ fact_weather.py
│  │  ├─ ml.py
│  │  ├─ vis
│  │  │  ├─ dim_condition.py
│  │  │  ├─ dim_date.py
│  │  │  ├─ dim_location.py
│  │  │  └─ __init__.py
│  │  └─ __init__.py
│  ├─ silver
│  │  ├─ cleaning.py
│  │  └─ __init__.py
│  └─ __init__.py
├─ main.py
├─ README.Docker.md
├─ requirements.txt
├─ src
│  ├─ database
│  │  ├─ data_uploader.py
│  │  ├─ db_loader.py
│  │  ├─ db_uploader.py
│  │  ├─ run_azure_data.py
│  │  └─ __init__.py
│  ├─ ingestion
│  │  ├─ current_year_collector.py
│  │  ├─ orchestrator.py
│  │  ├─ weather_data_collector.py
│  │  ├─ weather_wikipedia_data.py
│  │  ├─ weather_wikipedia_scrapping.py
│  │  ├─ wunderground.py
│  │  └─ __init__.py
│  ├─ transformation
│  │  ├─ wiki_transformer.py
│  │  └─ __init__.py
│  └─ __init__.py
├─ tests
│  ├─ test_cleaning_fallback.py
│  └─ test_orchestrator.py
└─ tree.txt

```