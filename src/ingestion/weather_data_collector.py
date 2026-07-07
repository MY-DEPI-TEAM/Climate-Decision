import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
from pathlib import Path

import pandas as pd
import time

# cities list with their coordinates
locations = [
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
    {"city": "Sohag", "lat": 26.5570, "lon": 31.6948}
]

all_dfs = []
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("starting data retrieval...")

for loc in locations:
    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={loc['lat']}&longitude={loc['lon']}&start_date=2022-01-01&end_date=2025-12-31&daily=weather_code,temperature_2m_max,temperature_2m_min,relative_humidity_2m_mean&timezone=Africa%2FCairo&format=csv"

    success = False
    retries = 3

    while not success and retries > 0:
        try:
            df = pd.read_csv(url, skiprows=3)
            df.columns = ['Date', 'Weather_Code', 'Max_Temp', 'Min_Temp', 'Avg_Humidity']
            df.insert(0, 'Governorate', loc['city'])
            df['Source'] = "Open-Meteo Historical Weather API"

            all_dfs.append(df)
            print(f"Data retrieved successfully for {loc['city']}")
            success = True
            time.sleep(2)
        except Exception as e:
            if "429" in str(e):
                print(f"Rate limit hit for {loc['city']}. Sleeping for 10 seconds...")
                time.sleep(10) # retry after 10 seconds
                retries -= 1
            else:
                print(f"Error in {loc['city']}: {e}")
                break


if all_dfs:
    final_table = pd.concat(all_dfs, ignore_index=True)
    
    # columns order
    final_table = final_table[['Governorate', 'Date', 'Weather_Code', 'Max_Temp', 'Min_Temp', 'Avg_Humidity', 'Source']]

    # save to Excel and CSV
    file_name_csv = OUTPUT_DIR / "Egypt_Weather_2022_2025_Final.csv"
    
    # CSV
    final_table.to_csv(file_name_csv, index=False, encoding='utf-8-sig') # encoding

    print("\nFinal files prepared!")
    print(f"Saved as CSV: {file_name_csv}")
    print(f"Total rows collected: {len(final_table)}")
else:
    print("No data retrieved for any location.")