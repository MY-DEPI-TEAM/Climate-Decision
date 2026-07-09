import os
from pathlib import Path
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
spark = None
df_result = None


def _get_spark():
    global spark
    if spark is None:
        spark = (
            SparkSession.builder
            .appName("AsOfJoin")
            .master("local[*]")
            .config("spark.jars.packages", "com.microsoft.sqlserver:mssql-jdbc:12.4.2.jre11")
            .config("spark.driver.memory", "4g")
            .config("spark.sql.shuffle.partitions", "1")
            .getOrCreate()
        )
        spark.sparkContext.setLogLevel("ERROR")
    return spark


def _get_local_weather_paths():
    csv_paths = []
    historical_csv = PROJECT_ROOT / "data" / "raw" / "Egypt_Weather_2022_2025_Final.csv"
    if historical_csv.exists():
        csv_paths.append(historical_csv)

    current_year_dir = PROJECT_ROOT / "data" / "raw" / "current_year"
    if current_year_dir.exists():
        csv_paths.extend(sorted(current_year_dir.glob("Egypt_Weather_*.csv")))

    return csv_paths


def _standardize_weather_df(df):
    rename_map = {
        "Governorate": "governorate",
        "Date": "date",
        "Weather_Code": "weather_code",
        "Avg_Humidity": "avg_humidity",
        "Source": "source",
        "avg_humidity": "avg_humidity",
        "weather_code": "weather_code",
        "source": "source",
    }

    for old_name, new_name in rename_map.items():
        if old_name in df.columns:
            df = df.withColumnRenamed(old_name, new_name)

    if "avg_max_temp" not in df.columns and "Max_Temp" in df.columns:
        df = df.withColumnRenamed("Max_Temp", "avg_max_temp")
    elif "avg_max_temp" not in df.columns and "max_temp" in df.columns:
        df = df.withColumnRenamed("max_temp", "avg_max_temp")

    if "avg_min_temp" not in df.columns and "Min_Temp" in df.columns:
        df = df.withColumnRenamed("Min_Temp", "avg_min_temp")
    elif "avg_min_temp" not in df.columns and "min_temp" in df.columns:
        df = df.withColumnRenamed("min_temp", "avg_min_temp")

    if "id" not in df.columns:
        df = df.withColumn("id", F.concat_ws("_", F.col("governorate"), F.col("date")))
    if "condition" not in df.columns:
        df = df.withColumn("condition", F.lit("weather_data"))
    if "source" not in df.columns:
        df = df.withColumn("source", F.lit("unknown"))

    if "date" in df.columns:
        df = df.withColumn("date", F.to_date(F.col("date")))

    for col_name, cast_type in {
        "weather_code": "int",
        "avg_max_temp": "double",
        "avg_min_temp": "double",
        "avg_humidity": "double",
    }.items():
        if col_name in df.columns:
            df = df.withColumn(col_name, F.col(col_name).cast(cast_type))

    return df


def _load_local_fallback_df():
    csv_paths = _get_local_weather_paths()
    if not csv_paths:
        raise FileNotFoundError("No local weather CSV files were found under data/raw")

    spark_local = _get_spark()
    data_frames = []
    for csv_path in csv_paths:
        df = (
            spark_local.read.option("header", True)
            .csv(str(csv_path))
        )
        data_frames.append(_standardize_weather_df(df))

    combined_df = data_frames[0]
    for extra_df in data_frames[1:]:
        combined_df = combined_df.unionByName(extra_df, allowMissingColumns=True)

    return combined_df


def _read_weather_tables(spark_local, azure_url, azure_props):
    weather_tables = ["dbo.merged_weather", "dbo.weather_monthly_current_year"]
    data_frames = []

    for table_name in weather_tables:
        try:
            table_df = spark_local.read.jdbc(url=azure_url, table=table_name, properties=azure_props)
            data_frames.append(_standardize_weather_df(table_df))
            print(f"Loaded weather data from {table_name}")
        except Exception as exc:
            print(f"Skipping missing or unreadable table {table_name}: {exc}")

    if not data_frames:
        raise RuntimeError("No weather tables could be read from Azure SQL")

    combined_df = data_frames[0]
    for extra_df in data_frames[1:]:
        combined_df = combined_df.unionByName(extra_df, allowMissingColumns=True)

    return combined_df


def _read_wikipedia_df(spark_local, azure_url, azure_props):
    try:
        df_wiki = spark_local.read.jdbc(url=azure_url, table="dbo.wikipedia_revision_history", properties=azure_props)
        return df_wiki.withColumn("revision_date", F.to_date(F.col("revision_timestamp")))
    except Exception as exc:
        print(f"Falling back to empty wiki history because it could not be loaded: {exc}")
        return (
            spark_local.createDataFrame([], "revision_timestamp timestamp, user string, comment string, source string")
            .withColumn("revision_date", F.to_date(F.col("revision_timestamp")))
        )


# ─── Output ───────────────────────────────────────────────────
def get_joined_df():
    global df_result
    if df_result is not None:
        return df_result

    try:
        spark_local = _get_spark()
        azure_url = (
            f"jdbc:sqlserver://{os.getenv('AZURE_SQL_SERVER')};"
            f"databaseName={os.getenv('AZURE_SQL_DATABASE')};"
            f"encrypt=true;trustServerCertificate=false;"
        )
        azure_props = {
            "user": os.getenv("AZURE_SQL_USER"),
            "password": os.getenv("AZURE_SQL_PASSWORD"),
            "driver": "com.microsoft.sqlserver.jdbc.SQLServerDriver"
        }

        df_weather = _read_weather_tables(spark_local, azure_url, azure_props)
        df_wiki = _read_wikipedia_df(spark_local, azure_url, azure_props)

        join_cond = df_wiki["revision_date"] <= df_weather["date"]
        df_joined = df_weather.join(df_wiki, join_cond, "left")

        window_spec = Window \
            .partitionBy(df_weather["id"], df_weather["date"]) \
            .orderBy(F.col("revision_timestamp").desc())

        df_result = (
            df_joined
            .withColumn("row_num", F.row_number().over(window_spec))
            .filter(F.col("row_num") == 1)
            .drop("row_num", "revision_date")
        )
    except Exception as exc:
        print(f"⚠️ Azure SQL read failed, using local weather data instead: {exc}")
        df_result = _load_local_fallback_df()

    return df_result


if __name__ == "__main__":
    result_df = get_joined_df()
    result_df.show(5, truncate=False)
    print(f"Rows: {result_df.count()} | Cols: {len(result_df.columns)}")