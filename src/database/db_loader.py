import os
from pathlib import Path
import pyodbc

BASE_DIR = Path(__file__).resolve().parents[2]

def run_db_script():
    # اسم السيرفر بتاعك من الـ SSMS
    server = 'localhost'
    database = 'Climate_Decision'
    # قراءة إعدادات الاتصال ديناميكياً من البيئة الممررة للـ Container
    # وفي حال تشغيله خارج دوكر يرجع لقيم افتراضية
    # server = os.getenv('DB_SERVER', 'database,1433')
    # database = os.getenv('DB_NAME', 'Climate_Decision')
    # user = os.getenv('DB_USER', 'sa')
    # password = os.getenv('DB_PASSWORD', 'YourStrong@Password123')
    
    # بناء الـ Connection String المتوافقة مع الـ Linux والـ Docker SQL Server
    conn_str = (
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={server};'
        f'DATABASE={database};'
        # f'UID={user};'
        # f'PWD={password};'
        f'Trusted_Connection=yes;'
    )
    
    script_path = BASE_DIR / 'db_scripts' / 'SQLQuery1.sql'
    
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