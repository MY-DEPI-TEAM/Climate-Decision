from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pyodbc
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_CURRENT_YEAR_DIR = BASE_DIR / "data" / "raw" / "current_year"


def get_db_connection_string() -> str | None:
    server = os.getenv("AZURE_SQL_SERVER")
    database = os.getenv("AZURE_SQL_DATABASE")
    user = os.getenv("AZURE_SQL_USER")
    password = os.getenv("AZURE_SQL_PASSWORD")

    if not all([server, database, user, password]):
        return None

    return (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=no;"
        f"Connection Timeout=30;"
    )


def get_monthly_csv_files() -> list[Path]:
    if not RAW_CURRENT_YEAR_DIR.exists():
        return []
    return sorted(RAW_CURRENT_YEAR_DIR.glob("Egypt_Weather_*.csv"))


def upload_monthly_files_to_db(csv_files: list[Path] | None = None) -> int:
    files_to_upload = csv_files or get_monthly_csv_files()
    conn_str = get_db_connection_string()
    if not conn_str:
        raise RuntimeError("Database credentials not found. Set AZURE_SQL_* values first.")

    if not files_to_upload:
        print("No monthly CSV files found to upload.")
        return 0

    table_name = "dbo.weather_monthly_current_year"
    uploaded_count = 0

    try:
        with pyodbc.connect(conn_str) as conn:
            with conn.cursor() as cursor:
                # 1. إنشاء الجدول إن لم يكن موجوداً
                cursor.execute(
                    f"""
                    IF OBJECT_ID('{table_name}', 'U') IS NULL
                    BEGIN
                        CREATE TABLE {table_name} (
                            Governorate NVARCHAR(100),
                            Date DATE,
                            Year INT,
                            Month INT,
                            Weather_Code FLOAT,
                            Max_Temp FLOAT,
                            Min_Temp FLOAT,
                            Avg_Humidity FLOAT,
                            Source NVARCHAR(200)
                        )
                    END
                    """
                )
                conn.commit()

                # 2. جلب الشهور والسنوات الموجودة بالفعل في قاعدة البيانات لمنع التكرار
                cursor.execute(f"SELECT DISTINCT Year, Month FROM {table_name}")
                existing_records = {(row[0], row[1]) for row in cursor.fetchall()}

                for csv_file in files_to_upload:
                    df = pd.read_csv(csv_file)
                    if df.empty:
                        continue

                    # قراءة السنة والشهر المستهدفين من أول صف في الملف للتحقق سريعاً
                    file_year = int(df.iloc[0]["Year"])
                    file_month = int(df.iloc[0]["Month"])

                    # إذا كان الشهر والسنة موجودين مسبقاً في القاعدة، يتم تخطي الملف بالكامل
                    if (file_year, file_month) in existing_records:
                        print(f"Skipping {csv_file.name}: Data for {file_year}-{file_month:02d} already exists in SQL Database.")
                        continue

                    print(f"Uploading {csv_file.name}...")
                    for _, row in df.iterrows():
                        cursor.execute(
                            f"""
                            INSERT INTO {table_name} (
                                Governorate, Date, Year, Month, Weather_Code, Max_Temp, Min_Temp, Avg_Humidity, Source
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            row["Governorate"],
                            row["Date"],
                            int(row["Year"]),
                            int(row["Month"]),
                            row.get("Weather_Code"),
                            row.get("Max_Temp"),
                            row.get("Min_Temp"),
                            row.get("Avg_Humidity"),
                            row.get("Source"),
                        )
                    conn.commit()
                    print(f"Successfully uploaded {csv_file.name}")
                    uploaded_count += 1

        print(f"Finished processing. Total new files uploaded to {table_name}: {uploaded_count}")
        return uploaded_count
    except pyodbc.Error as exc:
        raise RuntimeError(f"Failed to upload monthly files to database: {exc}") from exc

def main() -> None:
    upload_monthly_files_to_db()


if __name__ == "__main__":
    main()