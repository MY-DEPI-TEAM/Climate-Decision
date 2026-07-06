import os
from pathlib import Path
import pyodbc
from dotenv import load_dotenv

# شحن المتغيرات البيئية من ملف .env
load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]

def run_db_script():
    server = os.getenv('AZURE_SQL_SERVER')
    database = os.getenv('AZURE_SQL_DATABASE')
    user = os.getenv('AZURE_SQL_USER')
    password = os.getenv('AZURE_SQL_PASSWORD')

    if not all([server, database, user, password]):
        raise ValueError("Missing Azure SQL connection details in .env file.")
    
    conn_str = (
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={server};'
        f'DATABASE={database};'
        f'UID={user};'
        f'PWD={password};'
        f'Encrypt=yes;'
        f'TrustServerCertificate=no;'
        f'Connection Timeout=30;'
    )
    script_path = BASE_DIR / 'db_scripts' / 'Azure.sql'

    if not script_path.exists():
        raise FileNotFoundError(f"SQL file not found at path: {script_path}")
        
    print(f"Reading and executing SQL file: {script_path} ...")
    
    try:
        with pyodbc.connect(conn_str) as conn:
            with conn.cursor() as cursor:
                with open(script_path, 'r', encoding='utf-8') as file:
                    sql_script = file.read()
                
                # تنفيذ كود الـ SQL بالكامل جوه الـ Docker Database
                cursor.execute(sql_script)
                conn.commit()
                
        print("Tables created and Bulk Insert completed successfully in SQL Server Container!")
    except pyodbc.Error as e:
        print(f"حدث خطأ أثناء الاتصال أو التنفيذ داخل الـ Container: {e}")
        raise e
    
if __name__ == "__main__":
    run_db_script()
