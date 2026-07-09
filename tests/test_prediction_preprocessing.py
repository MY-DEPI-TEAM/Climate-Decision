from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml.prediction import coerce_numeric_columns


def test_coerce_numeric_columns_converts_decimal_like_values():
    df = pd.DataFrame(
        {
            "temp_range": ["9.10", "7.65", None],
            "max_temp": ["30.0", "31.5", "invalid"],
        }
    )

    result = coerce_numeric_columns(df, ["temp_range", "max_temp"])

    assert result["temp_range"].dtype.kind in "fiu"
    assert result["max_temp"].dtype.kind in "fiu"
    assert result.loc[0, "temp_range"] == 9.10
    assert pd.isna(result.loc[2, "max_temp"])
