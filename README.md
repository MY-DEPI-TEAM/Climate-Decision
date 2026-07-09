# 🌍 Climate-Decision

**Smart Data Lakehouse Platform for Egyptian Climate Intelligence**

Climate-Decision is an end-to-end **ETLT (Extract, Transform, Load, Transform)** data platform built on a **Medallion Architecture (Bronze → Silver → Gold)**. It ingests Egyptian weather data, cleans and models it into an analytics-ready lakehouse, forecasts future climate trends with ML, and exposes everything through a **LangChain + Ollama AI Agent** that answers natural-language questions and supports data-driven decisions.

---

## ✨ Key Features

- 🌦️ **Automated ingestion** of historical & current-year weather data for Egyptian governorates (Open-Meteo + Wikipedia revision history + scraped climate insights)
- 🥉🥈🥇 **Medallion Architecture** — Bronze (raw), Silver (cleaned/conformed), Gold (fact/dimension tables + ML-ready datasets)
- 📊 **Star-schema Gold layer** with `fact_weather` and supporting dimensions (`dim_date`, `dim_location`, `dim_condition`)
- 🤖 **ML forecasting module** producing 6-month-ahead weather predictions
- 🧠 **AI Agent (LangChain + NVIDIA NIM API)** for context-aware, natural-language querying over the lakehouse
- ☁️ **Azure SQL & local SQL support** via dedicated database scripts
- 🐳 **Dockerized** for easy deployment (`Dockerfile`, `compose.yaml`)
- ✅ **Test suite** covering ingestion fallback, cleaning, prediction, and app behavior

---

## 🏗️ Architecture

```
Raw Sources ──▶ Bronze (raw ingest) ──▶ Silver (cleaning) ──▶ Gold (facts/dims + ML-ready)
   │                                                                 │
   ├─ Open-Meteo API (governorate weather)                          ├─ ML Prediction (6-month forecast)
   ├─ Wikipedia revision history                                    └─ AI Agent (LangChain + Ollama)
   └─ Scraped climate insights                                              │
                                                                      Natural-language
                                                                      decision support
```

---

## 📁 Project Structure

```
Climate-Decision
├─ app.py                     # Flask/web app entry point
├─ main.py                    # Pipeline orchestration entry point
├─ compose.yaml / Dockerfile  # Containerized deployment
├─ data/
│  ├─ raw/                    # Raw ingested CSVs (historical + current year)
│  ├─ parsed/                 # Cleaned intermediate data (e.g. Wikipedia history)
│  ├─ lakehouse/gold/         # fact_weather.parquet, ml_ready.parquet
│  └─ predictions/            # 6-month weather forecast outputs
├─ lakehouse/
│  ├─ bronze/                 # Raw data access layer
│  ├─ silver/                 # Cleaning & conforming logic
│  └─ gold/                   # Fact table, ML feature prep, dimension builders (vis/)
├─ ml/
│  └─ prediction.py           # Forecasting model
├─ src/
│  ├─ ingestion/               # Weather + Wikipedia collectors, scraper, orchestrator
│  ├─ database/                # Azure/local DB uploaders & loaders
│  └─ transformation/          # Wikipedia data transformer
├─ templates/ & static/        # Frontend for the web app
├─ db_scripts/                 # Azure.sql / Locally.sql schema scripts
└─ tests/                      # Unit tests for ingestion, cleaning, prediction, app
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Ingestion | Python, Open-Meteo API, Web Scraping |
| Storage | Azure SQL, Parquet (Lakehouse) |
| Transformation | Pandas, custom ETLT pipelines |
| ML Forecasting | Scikit-learn |
| AI Agent | LangChain, NVIDIA NIM API |
| Web App | Flask, HTML/CSS/JS |
| Deployment | Docker, Docker Compose |
| Testing | Pytest |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Docker (optional, for containerized run)
- An Azure SQL instance or local SQL Server (see `db_scripts/`)
- An [NVIDIA API key](https://build.nvidia.com) for the AI Agent (NVIDIA NIM)

### 1. Clone the repository
```bash
git clone https://github.com/MY-DEPI-TEAM/Climate-Decision.git
cd Climate-Decision
```

### 2. Set up environment variables
```bash
cp .env.example .env
# Fill in your Azure SQL connection string, NVIDIA_API_KEY, etc.
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the ETLT pipeline
```bash
python main.py
```

### 5. Launch the web app
```bash
python app.py
```

### Or run everything with Docker
```bash
docker compose up --build
```

---

## 🧪 Running Tests
```bash
pytest tests/
```

---

## 🗺️ Roadmap

- [ ] Expand AI Agent tool coverage for deeper decision-support queries
- [ ] Add more governorates / data sources
- [ ] CI/CD pipeline for automated testing & deployment
- [ ] Interactive dashboard for Gold-layer exploration

---

## 👥 Team

Built by **MY-DEPI-TEAM** as a graduation project — combining data engineering, ML, and AI agent design into a unified climate decision-support platform.

---

## 📄 License

This project is currently unlicensed. Add a license file if you plan to open-source it publicly.
