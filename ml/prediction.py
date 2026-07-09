from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier, XGBRegressor


BASE_DIR = Path(__file__).resolve().parents[1]
PARQUET_PATH = BASE_DIR / "data" / "lakehouse" / "gold" / "ml_ready.parquet"
OUTPUT_PATH = BASE_DIR / "data" / "predictions" / "weather_forecast_next_6_months.csv"


def coerce_numeric_columns(df: pd.DataFrame, columns=None) -> pd.DataFrame:
    """Convert object/decimal-like columns to numeric values when possible."""
    if columns is None:
        columns = [
            "avg_max_temp",
            "avg_min_temp",
            "avg_humidity",
            "temp_range",
            "max_temp",
            "range_max_temp",
            "min_temp",
            "range_min_temp",
            "std_max_temp",
            "std_min_temp",
        ]

    for column in columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    return df


def load_and_prepare_data(parquet_path: Path = PARQUET_PATH) -> tuple[pd.DataFrame, list[str], LabelEncoder, LabelEncoder | None]:
    df = pd.read_parquet(parquet_path)
    print("the shape of the data:", df.shape)
    print("available columns:", df.columns.tolist())

    if "date" not in df.columns and "id" in df.columns:
        df["date"] = df["id"].apply(lambda value: value.split("_")[-1] if isinstance(value, str) else None)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date")

    df["month"] = df["date"].dt.month
    df["day_of_year"] = df["date"].dt.dayofyear
    df["year"] = df["date"].dt.year

    df = coerce_numeric_columns(df)

    le_city = LabelEncoder()
    if "governorate" in df.columns:
        df["city"] = df["governorate"]
    elif "city" in df.columns:
        df["city"] = df["city"]
    elif "id" in df.columns:
        df["city"] = df["id"].apply(lambda value: value.split("_")[0] if isinstance(value, str) else "")

    if "city" in df.columns:
        df["city_encoded"] = le_city.fit_transform(df["city"].fillna("unknown"))

    le_condition = LabelEncoder()
    if "condition" in df.columns:
        df["condition_encoded"] = le_condition.fit_transform(df["condition"].fillna("unknown"))

    le_heat = LabelEncoder()
    if "heat_level" in df.columns:
        df["heat_level_encoded"] = le_heat.fit_transform(df["heat_level"].fillna("moderate"))

    features = [
        "month",
        "day_of_year",
        "year",
        "city_encoded",
        "temp_range",
        "std_min_temp",
        "std_max_temp",
    ]
    features = [feature for feature in features if feature in df.columns]

    return df, features, le_city, le_condition


def train_models(df: pd.DataFrame, features: list[str], le_city: LabelEncoder, le_condition: LabelEncoder | None):
    X = df[features]
    max_temp_col = "avg_max_temp" if "avg_max_temp" in df.columns else "max_temp"
    min_temp_col = "avg_min_temp" if "avg_min_temp" in df.columns else "min_temp"

    if max_temp_col not in df.columns or min_temp_col not in df.columns:
        raise KeyError(f"Expected temperature columns not found. Checked {max_temp_col} and {min_temp_col}.")

    y_max = df[max_temp_col]
    y_min = df[min_temp_col]
    y_condition = df["condition_encoded"] if le_condition is not None and "condition_encoded" in df.columns else None

    X_train, _, y_train_max, _ = train_test_split(X, y_max, test_size=0.2, shuffle=False)
    _, _, y_train_min, _ = train_test_split(X, y_min, test_size=0.2, shuffle=False)

    model_max = XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=6, random_state=42)
    model_max.fit(X_train, y_train_max)

    model_min = XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=6, random_state=42)
    model_min.fit(X_train, y_train_min)

    print("temperature prediction models trained successfully!")

    model_cond = None
    if y_condition is not None:
        _, _, y_train_cond, _ = train_test_split(X, y_condition, test_size=0.2, shuffle=False)
        model_cond = XGBClassifier(n_estimators=100, random_state=42)
        model_cond.fit(X_train, y_train_cond)
        print("condition prediction model trained successfully!")

    return model_max, model_min, model_cond, le_condition


def get_prediction_df():
    df, features, le_city, le_condition = load_and_prepare_data()
    model_max, model_min, model_cond, le_condition = train_models(df, features, le_city, le_condition)

    last_date = df["date"].max()
    future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=180, freq="D")

    target_city = "Cairo"
    city_code = le_city.transform([target_city])[0] if hasattr(le_city, "classes_") and target_city in le_city.classes_ else 0

    future_df = pd.DataFrame(
        {
            "date": future_dates,
            "month": future_dates.month,
            "day_of_year": future_dates.dayofyear,
            "year": future_dates.year,
            "city_encoded": city_code,
        }
    )

    for column in ["temp_range", "std_min_temp", "std_max_temp"]:
        if column in features:
            future_df[column] = df[column].mean()

    future_df["predicted_max_temp"] = model_max.predict(future_df[features])
    future_df["predicted_min_temp"] = model_min.predict(future_df[features])

    if model_cond is not None and le_condition is not None:
        cond_preds = model_cond.predict(future_df[features])
        future_df["predicted_condition"] = le_condition.inverse_transform(cond_preds)

    print(f"\nWeather forecasts for {target_city} during the coming period:")
    print(future_df[["date", "predicted_max_temp", "predicted_min_temp", "predicted_condition"]].head(10))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    future_df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nForecasts saved successfully in file: {OUTPUT_PATH}")


if __name__ == "__main__":
    get_prediction_df()
