"""
Silver Layer — warehouse/silver/cleaning.py
=============================================
تنضيف البيانات الجاية من Bronze Layer (get_joined_df):
    1. إزالة التكرار (نفس المحافظة + نفس التاريخ)
    2. حذف الصفوف اللي ناقصها بيانات أساسية (governorate/date/avg_max_temp/
       avg_min_temp/avg_humidity)
    3. حذف القيم المستحيلة (outliers) في الحرارة والرطوبة
    4. ملء القيم الناقصة في الأعمدة المساعدة بمتوسط كل عمود (بدل ما تفضل NULL)
    5. ملء القيم النصية الناقصة بـ "unknown"

التعديلات عن النسخة القديمة:
    - إضافة dropDuplicates على (governorate, date) — كان ممكن يبقى عندنا
      أكتر من صف لنفس المحافظة ونفس التاريخ لو حصل تكرار في المصدر.
    - فصل حساب كل عمود عن التاني بدل استعلام واحد شامل، عشان لو عمود
      اتشال أو اتغيّر اسمه، الكود يفضل يشتغل من غير كراش.
    - إضافة طباعة (logging) بسيطة توضح كام صف اتشال في كل خطوة، عشان
      يبقى واضح تأثير التنضيف على البيانات (مهم للتوثيق الأكاديمي).
    - التأكد إن الأعمدة الموجودة فعلاً بس هي اللي بتتعالج (باستخدام
      [c for c in cols if c in df.columns]) عشان الكود يفضل مرن مع أي
      تغيير مستقبلي في مخرجات الـ Bronze Layer.
"""

import sys
from pathlib import Path
from pyspark.sql import functions as F

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from lakehouse.bronze.access import get_joined_df, _load_local_fallback_df


def _clean_df(df, source_name):
    df = df.persist()
    try:
        _rows_before = df.count()

        dedup_keys = [c for c in ["governorate", "date"] if c in df.columns]
        if dedup_keys:
            df = df.dropDuplicates(dedup_keys)
        _rows_after_dedup = df.count()
        print(f"[cleaning] Removed duplicates: {_rows_before - _rows_after_dedup} rows removed (was {_rows_before}, now {_rows_after_dedup})")

        core_cols = [c for c in ["governorate", "date", "avg_max_temp", "avg_min_temp", "avg_humidity"] if c in df.columns]
        _rows_before_core = df.count()
        df = df.dropna(subset=core_cols)
        _rows_after_core = df.count()
        print(f"[cleaning] Removed NULLs in core columns: {_rows_before_core - _rows_after_core} rows removed")

        _rows_before_outliers = df.count()
        df = df.filter(
            (F.col("avg_max_temp").between(-10, 60))
            & (F.col("avg_min_temp").between(-10, 60))
            & (F.col("avg_humidity").between(0, 100))
        )
        _rows_after_outliers = df.count()
        print(f"[cleaning] Removed outliers: {_rows_before_outliers - _rows_after_outliers} rows removed")

        fill_cols = [
            c for c in [
                "high_temp_c", "max_temp", "low_temp_c", "min_temp",
                "std_max_temp", "std_min_temp", "range_max_temp", "range_min_temp",
            ]
            if c in df.columns
        ]

        if fill_cols:
            mean_expressions = [F.mean(c).alias(c) for c in fill_cols]
            means_row = df.select(mean_expressions).collect()[0]

            fill_dict = {}
            for col in fill_cols:
                val = means_row[col]
                if val is not None:
                    fill_dict[col] = float(round(float(val), 2))

            if fill_dict:
                df = df.fillna(fill_dict)
                print(f"[cleaning] Filled numeric NULLs with the mean in columns: {list(fill_dict.keys())}")

        text_fill = {c: "unknown" for c in ["condition", "user", "comment", "source"] if c in df.columns}
        if text_fill:
            df = df.fillna(text_fill)
            print(f"[cleaning] Filled text NULLs with 'unknown' in columns: {list(text_fill.keys())}")

        print(f"[cleaning] Source={source_name} Final result: {df.count()} rows from an initial {_rows_before} rows before cleaning")
        return df
    except Exception as exc:
        print(f"[cleaning] Cleaning pipeline failed for {source_name}: {exc}")
        raise


_cached_df = None


def get_cleaned_df():
    global _cached_df
    if _cached_df is None:
        try:
            _cached_df = _clean_df(get_joined_df(), source_name="azure-sql")
        except Exception as exc:
            print(f"[cleaning] Azure SQL source failed, falling back to local weather data: {exc}")
            _cached_df = _clean_df(_load_local_fallback_df(), source_name="local-csv")
    return _cached_df


if __name__ == "__main__":
    df = get_cleaned_df()
    df.show(5, truncate=False)
    print(f"Rows: {df.count()} | Cols: {len(df.columns)}")
    print("Nulls remaining:")
    df.select([F.count(F.when(F.col(c).isNull(), c)).alias(c) for c in df.columns]).show()