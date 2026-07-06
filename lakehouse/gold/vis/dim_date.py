"""
Gold Layer — warehouse/gold/dim_date.py
==========================================
جدول أبعاد التاريخ (dim_date) — بيفكك كل تاريخ فريد لأجزاءه (سنة، شهر،
يوم، فصل، هل هو ويكند) عشان تحليل Power BI يبقى أسهل وأسرع.
"""

import sys
from pathlib import Path
from pyspark.sql import functions as F
from pyspark.sql.window import Window

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from lakehouse.silver.cleaning import get_cleaned_df


def build_dim_date():
    df = get_cleaned_df()

    dates = df.select("date").distinct()
    w = Window.orderBy("date")

    dim_date = (
        dates
        .withColumn("date_id", F.row_number().over(w))
        .withColumn("year", F.year("date"))
        .withColumn("month", F.month("date"))
        .withColumn("day", F.dayofmonth("date"))
        .withColumn(
            "season",
            F.when(F.col("month").isin(12, 1, 2), "winter")
            .when(F.col("month").isin(3, 4, 5), "spring")
            .when(F.col("month").isin(6, 7, 8), "summer")
            .otherwise("autumn"),
        )
        # dayofweek في Spark: 1=الأحد ... 7=السبت، فالويكند عندنا الجمعة (6) والسبت (7)
        .withColumn("is_weekend", F.dayofweek("date").isin(6, 7))
        .select("date_id", "date", "year", "month", "day", "season", "is_weekend")
    )
    return dim_date


def get_dim_date():
    return build_dim_date()


if __name__ == "__main__":
    dim = get_dim_date()
    dim.show(10, truncate=False)
    print(f"Rows: {dim.count()}")