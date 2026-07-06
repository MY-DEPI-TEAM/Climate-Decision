"""
Gold Layer — warehouse/gold/dim_condition.py
===============================================
جدول أبعاد حالة الطقس (dim_condition).

ملحوظة هندسية مهمة (يفيد توضيحها لزميلك):
    في التصميم المقترح، heat_level كان المفروض يبقى عمود جوه
    dim_condition (زي: "sunny" -> "high"). لكن heat_level فعليًا
    بيتحسب من avg_max_temp، ودرجة الحرارة بتختلف من صف لصف حتى لو
    الـ condition نفسه ("sunny") متكرر في تواريخ ومحافظات مختلفة
    بدرجات حرارة مختلفة تمامًا. يعني ربط heat_level بـ dim_condition
    هيدّي نفس heat_level لكل الصفوف اللي عندها نفس condition، حتى لو
    درجة الحرارة الفعلية مختلفة تمامًا — وده غلط منطقيًا.

    الحل الصح: heat_level اتحط في fact_weather.py بدل كده (لأنه صفة
    بتتغيّر لكل صف/قياس، مش صفة ثابتة لكل "نوع طقس"). ده بيخلي الـ
    star schema أدق، وبردو Power BI هيقدر يفلتر عليها عادي من الـ fact.
"""

import sys
from pathlib import Path
from pyspark.sql import functions as F
from pyspark.sql.window import Window

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from lakehouse.silver.cleaning import get_cleaned_df


def build_dim_condition():
    df = get_cleaned_df()

    conditions = df.select("condition").distinct()
    w = Window.orderBy("condition")

    dim_condition = (
        conditions
        .withColumn("condition_id", F.row_number().over(w))
        .select("condition_id", "condition")
    )
    return dim_condition


def get_dim_condition():
    return build_dim_condition()


if __name__ == "__main__":
    dim = get_dim_condition()
    dim.show(30, truncate=False)
    print(f"Rows: {dim.count()}")