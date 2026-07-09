import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as weather_app


def test_retrieve_context_supports_forecast_csv_dates():
    context, retrieval_info = weather_app._retrieve_context("21/7/2026")

    assert "2026-07-21" in context or "2026-07-21" in retrieval_info
    assert "No matching data found" not in context
    assert "No data available" not in context


def test_extract_date_supports_relative_tomorrow_request():
    tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")

    extracted_date = weather_app._extract_date("Give me advice for tomorrow")

    assert extracted_date == date.today() + timedelta(days=1)
    assert extracted_date is not None
    assert extracted_date.strftime("%Y-%m-%d") == tomorrow
