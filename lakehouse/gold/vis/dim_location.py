"""
Gold Layer — warehouse/gold/dim_location.py
==============================================
جدول أبعاد المحافظات (dim_location) — بيتبني مرة واحدة من قائمة
المحافظات الفريدة الموجودة في البيانات، وبياخد location_id ثابت لكل
محافظة.

ملحوظة: عمود "region" مبدئيًا "Unknown" لكل المحافظات، لأن مفيش
مصدر بيانات فيه تصنيف المحافظات لمناطق (شمال/جنوب/وسط) حتى الآن.
لو حابين، ممكن نضيف قاموس تصنيف يدوي بسيط (governorate -> region)
لاحقًا.
"""

import sys
from pathlib import Path
from pyspark.sql import functions as F
from pyspark.sql.window import Window

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from lakehouse.silver.cleaning import get_cleaned_df

# قاموس مبدئي لتصنيف المحافظات المصرية لمناطق (يمكن التعديل عليه)
REGION_MAP = {
    "Cairo": "Central", "Giza": "Central", "Qalyubia": "Central",
    "Alexandria": "North", "Beheira": "North", "Kafr El Sheikh": "North",
    "Damietta": "North", "Port Said": "North", "Dakahlia": "North",
    "Gharbia": "North", "Menofia": "North", "Sharkia": "North",
    "Ismailia": "North", "Suez": "North",
    "Fayoum": "Central", "Beni Suef": "Central", "Minya": "Central",
    "Assiut": "Upper Egypt", "Sohag": "Upper Egypt", "Qena": "Upper Egypt",
    "Luxor": "Upper Egypt", "Aswan": "Upper Egypt",
    "Red Sea": "East", "South Sinai": "East", "North Sinai": "East",
    "New Valley": "West", "Matrouh": "West",
}


def build_dim_location():
    df = get_cleaned_df()

    map_expr = F.create_map(*[item for k, v in REGION_MAP.items() for item in (F.lit(k), F.lit(v))])

    locations = df.select("governorate").distinct()
    w = Window.orderBy("governorate")

    dim_location = (
        locations
        .withColumn("location_id", F.row_number().over(w))
        .withColumn("region", F.coalesce(map_expr[F.col("governorate")], F.lit("Unknown")))
        .select("location_id", "governorate", "region")
    )
    return dim_location


def get_dim_location():
    return build_dim_location()


if __name__ == "__main__":
    dim = get_dim_location()
    dim.show(30, truncate=False)
    print(f"Rows: {dim.count()}")