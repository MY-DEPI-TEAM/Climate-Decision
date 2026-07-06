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


def _load_local_fallback_df():
    csv_path = PROJECT_ROOT / "data" / "raw" / "Egypt_Weather_2022_2025_Final.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Local weather data not found at {csv_path}")

    return (
        _get_spark()
        .read.option("header", True)
        .csv(str(csv_path))
        .withColumnRenamed("Governorate", "governorate")
        .withColumnRenamed("Date", "date")
        .withColumnRenamed("Weather_Code", "weather_code")
        .withColumnRenamed("Max_Temp", "avg_max_temp")
        .withColumnRenamed("Min_Temp", "avg_min_temp")
        .withColumnRenamed("Avg_Humidity", "avg_humidity")
        .withColumnRenamed("Source", "source")
        .withColumn("id", F.monotonically_increasing_id())
        .withColumn("condition", F.lit("weather_data"))
        .withColumn("date", F.to_date(F.col("date")))
        .withColumn("avg_max_temp", F.col("avg_max_temp").cast("double"))
        .withColumn("avg_min_temp", F.col("avg_min_temp").cast("double"))
        .withColumn("avg_humidity", F.col("avg_humidity").cast("double"))
        .withColumn("weather_code", F.col("weather_code").cast("int"))
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

        df_weather = spark_local.read.jdbc(url=azure_url, table="dbo.merged_weather", properties=azure_props)
        df_wiki = spark_local.read.jdbc(url=azure_url, table="dbo.wikipedia_revision_history", properties=azure_props)

        df_wiki = df_wiki.withColumn("revision_date", F.to_date("revision_timestamp"))
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