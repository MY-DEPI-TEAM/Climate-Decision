import sys
from pathlib import Path

# إضافة المجلد الحالي للمسار لضمان إمكانية استيراد الملفات بشكل صحيح
sys.path.append(str(Path(__file__).resolve().parent))

# استيراد الدوال الرئيسية من الملفات الثلاثة
from db_loader import run_db_script
from db_uploader import upload_monthly_files_to_db
from data_uploader import upload_files_to_azure

def run_azure_data_pipeline():
    print("=" * 50)
    print("Starting Data Pipeline Execution...")
    print("=" * 50)

    # 1. تهيئة قاعدة البيانات وتشغيل سكريبت SQL
    print("\n[Step 1/3] Running Database Initialization Script...")
    try:
        run_db_script()
        print("✔ Step 1 completed successfully.")
    except Exception as e:
        print(f"❌ Step 1 failed: {e}")
        print("Stopping pipeline execution.")
        return

    # 2. رفع ملفات الطقس الشهرية لقاعدة البيانات
    print("\n[Step 2/3] Uploading Monthly CSV Files to SQL Database...")
    try:
        uploaded_count = upload_monthly_files_to_db()
        print(f"✔ Step 2 completed. Total files uploaded to DB: {uploaded_count}")
    except Exception as e:
        print(f"❌ Step 2 failed: {e}")
        print("Stopping pipeline execution.")
        return

    # 3. نسخ وأرشفة الملفات على Azure Blob Storage
    print("\n[Step 3/3] Uploading Files to Azure Blob Storage...")
    try:
        upload_files_to_azure()
        print("✔ Step 3 completed successfully.")
    except Exception as e:
        print(f"❌ Step 3 failed: {e}")
        print("Stopping pipeline execution.")
        return

    print("\n" + "=" * 50)
    print("Pipeline Execution Finished Successfully!")
    print("=" * 50)

if __name__ == "__main__":
    run_azure_data_pipeline()