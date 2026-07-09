import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import lakehouse.bronze.access as access


def test_local_weather_file_discovery_includes_current_year_monthly_csvs(tmp_path: Path) -> None:
    raw_dir = tmp_path / "data" / "raw"
    current_year_dir = raw_dir / "current_year"
    current_year_dir.mkdir(parents=True)

    historical_csv = raw_dir / "Egypt_Weather_2022_2025_Final.csv"
    historical_csv.write_text(
        "Governorate,Date,Weather_Code,Max_Temp,Min_Temp,Avg_Humidity,Source\n"
        "Cairo,2022-01-01,1,20,10,50,Test\n",
        encoding="utf-8",
    )

    monthly_csv = current_year_dir / "Egypt_Weather_2026_01.csv"
    monthly_csv.write_text(
        "Governorate,Date,Year,Month,Weather_Code,Max_Temp,Min_Temp,Avg_Humidity,Source\n"
        "Cairo,2026-01-01,2026,1,1,21,11,52,Open-Meteo\n",
        encoding="utf-8",
    )

    with patch.object(access, "PROJECT_ROOT", tmp_path):
        paths = access._get_local_weather_paths()

    assert historical_csv in paths
    assert monthly_csv in paths
