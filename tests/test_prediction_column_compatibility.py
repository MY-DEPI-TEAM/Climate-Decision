import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml.prediction import train_models


def test_train_models_accepts_avg_temperature_columns() -> None:
    df = pd.DataFrame(
        {
            "month": [1, 2, 3, 4],
            "day_of_year": [10, 20, 30, 40],
            "year": [2024, 2024, 2024, 2024],
            "city_encoded": [0, 0, 1, 1],
            "temp_range": [5.0, 6.0, 7.0, 8.0],
            "std_min_temp": [1.0, 1.1, 1.2, 1.3],
            "std_max_temp": [2.0, 2.1, 2.2, 2.3],
            "avg_max_temp": [20.0, 21.0, 22.0, 23.0],
            "avg_min_temp": [10.0, 11.0, 12.0, 13.0],
            "condition_encoded": [0, 0, 1, 1],
        }
    )

    model_max, model_min, model_cond, le_condition = train_models(
        df,
        ["month", "day_of_year", "year", "city_encoded", "temp_range", "std_min_temp", "std_max_temp"],
        None,
        None,
    )

    assert model_max is not None
    assert model_min is not None
    assert model_cond is None
    assert le_condition is None
