import shutil
import sys
from pathlib import Path
import pandas as pd
from pyspark.sql import SparkSession, functions as F

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from lakehouse.silver.cleaning import get_cleaned_df

# ─── تغليف الأكواد داخل الدالة ──────────────────────────────────
def get_ml_ready_df():
    # ─── Load ─────────────────────────────────────────────────────
    df = get_cleaned_df()

    # ─── 1. استخراج features من التاريخ ──────────────────────────
    df = df \
        .withColumn("year",    F.year("date")) \
        .withColumn("month",   F.month("date")) \
        .withColumn("day",     F.dayofmonth("date")) \
        .withColumn("season",  F.when(F.col("month").isin(12, 1, 2),  "winter")
                               .when(F.col("month").isin(3, 4, 5),   "spring")
                               .when(F.col("month").isin(6, 7, 8),   "summer")
                               .otherwise("autumn"))

    # ─── 2. حساب temp_range (فرق الحرارة النهاري) ────────────────
    df = df.withColumn("temp_range", F.round(F.col("avg_max_temp") - F.col("avg_min_temp"), 2))

    # ─── 3. تصنيف درجة الحرارة (heat_level) للـ AI Agent ─────────
    df = df.withColumn("heat_level",
        F.when(F.col("avg_max_temp") >= 45, "extreme")
         .when(F.col("avg_max_temp") >= 35, "high")
         .when(F.col("avg_max_temp") >= 25, "moderate")
         .otherwise("low")
    )

    # ─── 4. شيل الأعمدة اللي مش محتاجها الـ ML ───────────────────
    drop_cols = ["source", "comment", "user", "revision_timestamp",
                 "weather_code", "high_temp_c", "low_temp_c"]
    df = df.drop(*[c for c in drop_cols if c in df.columns])

    # ─── 5. ترتيب الأعمدة ─────────────────────────────────────────
    priority_cols = ["id", "governorate", "date", "year", "month", "day", "season",
                     "avg_max_temp", "avg_min_temp", "avg_humidity",
                     "temp_range", "heat_level", "condition"]
    remaining = [c for c in df.columns if c not in priority_cols]
    df = df.select(priority_cols + remaining)

    # ─── 6. حفظ كـ Parquet محلي (Gold Layer) ────────────────────────
    output_path = PROJECT_ROOT / "data" / "lakehouse" / "gold" / "ml_ready.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        if output_path.is_dir():
            shutil.rmtree(output_path)
        else:
            output_path.unlink()

    try:
        pandas_df = df.toPandas()
        pandas_df.to_parquet(output_path, engine="pyarrow", index=False)
        print(f"Saved Parquet to {output_path}")
    except Exception as exc:
        print(f"Parquet export failed: {exc}")
        raise

    return df  # الدالة الآن تقوم بالمعالجة، الحفظ، ثم إرجاع الـ Dataframe

# ─── اختبار الملف عند تشغيله مباشرة فقط ────────────────────────
if __name__ == "__main__":
    # استدعاء الدالة هنا لتجربتها عند تشغيل هذا الملف منفصلاً
    processed_df = get_ml_ready_df()
    
    processed_df.show(5, truncate=False)
    print(f"Rows: {processed_df.count()} | Cols: {len(processed_df.columns)}")
    print("Columns:", processed_df.columns)