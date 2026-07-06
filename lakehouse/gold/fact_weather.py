"""
Gold Layer — warehouse/gold/fact_weather.py
==============================================
جدول الحقائق (fact_weather) — قلب الـ Star Schema. بيربط البيانات
النظيفة بالأبعاد التلاتة (location, date, condition) عن طريق
foreign keys، وبيحتوي القياسات (measures) بس.

heat_level اتحطت هنا (مش في dim_condition) لأنها بتعتمد على
avg_max_temp اللي بتختلف لكل صف، مش صفة ثابتة لنوع الطقس (راجعي
الملحوظة في dim_condition.py لتفاصيل السبب).
"""

import shutil
import sys
from pathlib import Path
from pyspark.sql import functions as F

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from lakehouse.silver.cleaning import get_cleaned_df
from lakehouse.gold.vis.dim_location import get_dim_location
from lakehouse.gold.vis.dim_date import get_dim_date
from lakehouse.gold.vis.dim_condition import get_dim_condition


def build_fact_weather():
    df = get_cleaned_df()
    dim_location = get_dim_location()
    dim_date = get_dim_date()
    dim_condition = get_dim_condition()

    fact = (
        df
        .join(dim_location, on="governorate", how="left")
        .join(dim_date, on="date", how="left")
        .join(dim_condition, on="condition", how="left")
        .withColumn("temp_range", F.round(F.col("avg_max_temp") - F.col("avg_min_temp"), 2))
        .withColumn(
            "heat_level",
            F.when(F.col("avg_max_temp") >= 45, "extreme")
            .when(F.col("avg_max_temp") >= 35, "high")
            .when(F.col("avg_max_temp") >= 25, "moderate")
            .otherwise("low"),
        )
        .select(
            "id", "location_id", "date_id", "condition_id",
            "avg_max_temp", "avg_min_temp", "avg_humidity",
            "temp_range", "heat_level",
        )
    )
    return fact


# ─── تغليف كود المعالجة والحفظ بالكامل هنا ───────────────────────
def get_fact_weather():
    fact = build_fact_weather()
    
    # نقل كود حفظ الـ Parquet إلى داخل الدالة ليتم استدعاؤه في وقته المناسب
    output_path = PROJECT_ROOT / "data" / "lakehouse" / "gold" / "fact_weather.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if output_path.exists():
        if output_path.is_dir():
            shutil.rmtree(output_path)
        else:
            output_path.unlink()

    try:
        pandas_df = fact.toPandas()
        pandas_df.to_parquet(output_path, engine="pyarrow", index=False)
        print(f"Saved Parquet to {output_path}")
    except Exception as exc:
        print(f"Parquet export failed: {exc}")
        raise
        
    return fact


# ─── اختبار الملف عند تشغيله بشكل منفصل فقط ─────────────────────
if __name__ == "__main__":
    fact_df = get_fact_weather()
    fact_df.show(5, truncate=False)
    print(f"Rows: {fact_df.count()} | Cols: {len(fact_df.columns)}")