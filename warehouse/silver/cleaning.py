import sys
from pathlib import Path
from pyspark.sql import functions as F

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from warehouse.bronze.access import get_joined_df

# ─── Load ─────────────────────────────────────────────────────
df = get_joined_df()

# ─── 1. شيل الـ nulls في الأعمدة الأساسية ────────────────────
core_cols = ["governorate", "date", "avg_max_temp", "avg_min_temp", "avg_humidity"]
df = df.dropna(subset=core_cols)

# ─── 2. شيل الـ outliers (قيم مستحيلة) ──────────────────────
df = df.filter(
    (F.col("avg_max_temp").between(-10, 60)) &
    (F.col("avg_min_temp").between(-10, 60)) &
    (F.col("avg_humidity").between(0, 100))
)

# ─── 3. ملء الـ nulls الباقية بالمتوسط (بطريقة احترافية سريعة) ───
fill_cols = ["high_temp_c", "max_temp", "low_temp_c", "min_temp",
             "std_max_temp", "std_min_temp", "range_max_temp", "range_min_temp"]

# حساب متوسط كل الأعمدة في خطوة واحدة فقط لتوفير الذاكرة
mean_expressions = [F.mean(c).alias(c) for c in fill_cols]
means_row = df.select(mean_expressions).collect()[0]

# بناء قاموس بالقيم المراد ملؤها
fill_dict = {}
for col in fill_cols:
    val = means_row[col]
    if val is not None:
        fill_dict[col] = float(round(float(val), 2))

# تطبيق ملء الفراغات دفعة واحدة
if fill_dict:
    df = df.fillna(fill_dict)

# ─── 4. ملء الـ nulls النصية ──────────────────────────────────
df = df.fillna({"condition": "unknown", "user": "unknown", "comment": "unknown"})

# ─── Output ───────────────────────────────────────────────────
def get_cleaned_df():
    return df

if __name__ == "__main__":
    df.show(5, truncate=False)
    print(f"Rows: {df.count()} | Cols: {len(df.columns)}")
    print("Nulls remaining:")
    df.select([F.count(F.when(F.col(c).isNull(), c)).alias(c) for c in df.columns]).show()