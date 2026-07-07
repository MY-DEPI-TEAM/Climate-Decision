from __future__ import annotations

import io
import threading
import time
from calendar import monthrange
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = BASE_DIR / "data" / "raw" / "current_year"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Tune these based on how forgiving the API / your connection is.
MAX_WORKERS = 8
REQUEST_TIMEOUT = 20  # seconds

LOCATIONS = [
    {"city": "Cairo", "lat": 30.0444, "lon": 31.2357},
    {"city": "Alexandria", "lat": 31.2001, "lon": 29.9187},
    {"city": "Giza", "lat": 30.0131, "lon": 31.2089},
    {"city": "Dakahlia", "lat": 31.0409, "lon": 31.3785},
    {"city": "Red Sea", "lat": 27.2579, "lon": 33.8116},
    {"city": "Beheira", "lat": 31.0357, "lon": 30.4700},
    {"city": "Fayoum", "lat": 29.3084, "lon": 30.8428},
    {"city": "Gharbia", "lat": 30.7865, "lon": 31.0004},
    {"city": "Ismailia", "lat": 30.5965, "lon": 32.2715},
    {"city": "Menofia", "lat": 30.5765, "lon": 30.9985},
    {"city": "Minya", "lat": 28.0991, "lon": 30.7503},
    {"city": "Qalyubia", "lat": 30.4591, "lon": 31.1786},
    {"city": "New Valley", "lat": 25.4390, "lon": 30.5586},
    {"city": "Suez", "lat": 29.9668, "lon": 32.5498},
    {"city": "Aswan", "lat": 24.0889, "lon": 32.8998},
    {"city": "Assiut", "lat": 27.1783, "lon": 31.1849},
    {"city": "Beni Suef", "lat": 29.0744, "lon": 31.0978},
    {"city": "Port Said", "lat": 31.2653, "lon": 32.3019},
    {"city": "Damietta", "lat": 31.4175, "lon": 31.8144},
    {"city": "Sharkia", "lat": 30.5765, "lon": 31.5041},
    {"city": "South Sinai", "lat": 28.5063, "lon": 34.1166},
    {"city": "Kafr El Sheikh", "lat": 31.1049, "lon": 30.9402},
    {"city": "Matrouh", "lat": 31.3543, "lon": 27.2373},
    {"city": "Luxor", "lat": 25.6872, "lon": 32.6396},
    {"city": "Qena", "lat": 26.1551, "lon": 32.7160},
    {"city": "North Sinai", "lat": 31.1325, "lon": 33.8033},
    {"city": "Sohag", "lat": 26.5570, "lon": 31.6948},
]

# Thread-local storage so each worker thread gets its own requests.Session
# (Session objects are not guaranteed thread-safe, connection pooling is
# still shared efficiently per-thread).
_thread_local = threading.local()


def get_session() -> requests.Session:
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = requests.Session()
        retry = Retry(
            total=4,
            backoff_factor=1.5,  # 1.5s, 3s, 6s, 12s...
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=MAX_WORKERS, pool_maxsize=MAX_WORKERS)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        _thread_local.session = session
    return session


def get_months_to_collect(today: datetime | None = None) -> list[tuple[int, int]]:
    today = today or datetime.now()
    year = today.year
    month = today.month

    last_day_of_current_month = monthrange(year, month)[1]
    if today.day < last_day_of_current_month:
        month -= 1
        if month < 1:
            year -= 1
            month = 12

    return [(year, m) for m in range(1, month + 1)]


def build_monthly_url(lat: float, lon: float, year: int, month: int) -> str:
    start_date = f"{year:04d}-{month:02d}-01"
    end_day = monthrange(year, month)[1]
    end_date = f"{year:04d}-{month:02d}-{end_day:02d}"
    return (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date={start_date}&end_date={end_date}"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,relative_humidity_2m_mean"
        "&timezone=Africa%2FCairo&format=csv"
    )


def fetch_monthly_weather(location: dict, year: int, month: int) -> pd.DataFrame:
    url = build_monthly_url(location["lat"], location["lon"], year, month)
    session = get_session()
    response = session.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    df = pd.read_csv(io.StringIO(response.text), skiprows=3)
    df.columns = ["Date", "Weather_Code", "Max_Temp", "Min_Temp", "Avg_Humidity"]
    df.insert(0, "Governorate", location["city"])
    df["Source"] = "Open-Meteo Historical Weather API"
    df["Year"] = year
    df["Month"] = month
    return df[["Governorate", "Date", "Year", "Month", "Weather_Code", "Max_Temp", "Min_Temp", "Avg_Humidity", "Source"]]


def month_file_path(year: int, month: int) -> Path:
    return OUTPUT_DIR / f"Egypt_Weather_{year:04d}_{month:02d}.csv"


def is_current_month(year: int, month: int) -> bool:
    now = datetime.now()
    return year == now.year and month == now.month


def save_monthly_csv(df: pd.DataFrame, year: int, month: int) -> Path:
    file_path = month_file_path(year, month)

    if file_path.exists() and is_current_month(year, month):
        print(f"Refreshing current month file: {file_path.name}")
        file_path.unlink(missing_ok=True)

    df.to_csv(file_path, index=False, encoding="utf-8-sig")
    print(f"Saved monthly CSV: {file_path}")
    return file_path


def collect_current_year_weather() -> list[Path]:
    print("starting current-year data retrieval (concurrent)...")
    start_time = time.time()

    months = get_months_to_collect()

    # Skip months that already have a saved file (unless it's the current
    # month, which we always refresh). This avoids firing any network
    # requests at all for data we already have on disk.
    months_to_fetch = [
        (year, month)
        for year, month in months
        if is_current_month(year, month) or not month_file_path(year, month).exists()
    ]
    skipped = len(months) - len(months_to_fetch)
    if skipped:
        print(f"Skipping {skipped} month(s) with existing files.")

    if not months_to_fetch:
        print("Nothing to fetch, all monthly files already exist.")
        return []

    # Build the full list of (location, year, month) tasks and run them
    # concurrently, then group the results back by (year, month).
    tasks = [
        (location, year, month)
        for year, month in months_to_fetch
        for location in LOCATIONS
    ]

    results_by_month: dict[tuple[int, int], list[pd.DataFrame]] = {ym: [] for ym in months_to_fetch}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_task = {
            executor.submit(fetch_monthly_weather, location, year, month): (location, year, month)
            for location, year, month in tasks
        }

        completed, total = 0, len(future_to_task)
        for future in as_completed(future_to_task):
            location, year, month = future_to_task[future]
            completed += 1
            try:
                df = future.result()
                results_by_month[(year, month)].append(df)
            except Exception as exc:
                print(f"Error retrieving data for {location['city']} in {year:04d}-{month:02d}: {exc}")

            if completed % 20 == 0 or completed == total:
                print(f"Progress: {completed}/{total} requests done")

    created_files: list[Path] = []
    for year, month in months_to_fetch:
        month_df_parts = results_by_month[(year, month)]
        if month_df_parts:
            monthly_df = pd.concat(month_df_parts, ignore_index=True)
            saved_path = save_monthly_csv(monthly_df, year, month)
            created_files.append(saved_path)
        else:
            print(f"No data retrieved for {year:04d}-{month:02d}, nothing saved.")

    elapsed = time.time() - start_time
    print(f"Done in {elapsed:.1f}s")
    return created_files


def main() -> None:
    created_files = collect_current_year_weather()
    if created_files:
        print(f"Collected {len(created_files)} monthly files in {OUTPUT_DIR}")
    else:
        print("No monthly files were created.")


if __name__ == "__main__":
    main()