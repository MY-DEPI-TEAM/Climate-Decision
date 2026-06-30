import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

# شحن المتغيرات البيئية من ملف .env
load_dotenv()

def upload_files_to_azure():
    # الحصول على سلسلة الاتصال واسم الحاوية من ملف .env
    connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    container_name = "climate-data"
    
    if not connect_str:
        print("خطأ: لم يتم العثور على AZURE_STORAGE_CONNECTION_STRING في ملف .env")
        return

    try:
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
        container_client = blob_service_client.get_container_client(container_name)
        
        print("جاري التحقق من الملفات الموجودة على Azure...")
        existing_blobs = {blob.name for blob in container_client.list_blobs()}
        
        # تحديد المجلدات المحلية التي نريد رفع ملفاتها (Raw و Processed)
        base_dir = os.path.dirname(__file__)
        local_folders = [
            os.path.join(base_dir, '../../data/raw'),
            os.path.join(base_dir, '../../data/processed')
        ]

        for folder_path in local_folders:
            if not os.path.exists(folder_path):
                print(f"تنبيه: المسار المحلي غير موجود، سيتم تخطيه: {folder_path}")
                continue

            # المرور على جميع الملفات داخل المجلد المحلي ورفعها
            for file_name in os.listdir(folder_path):
                if file_name.endswith('.csv'):
                    local_file_path = os.path.join(folder_path, file_name)
                    blob_client = container_client.get_blob_client(file_name)

                    if blob_client.exists():
                        print(f"تخطي {file_name}: الملف موجود بالفعل على Azure Blob.")
                        continue

                    print(f"جاري رفع {file_name}...")
                    with open(local_file_path, "rb") as data:
                        blob_client.upload_blob(data, overwrite=True)

                    print(f"تم رفع {file_name} بنجاح.")

        print("اكتملت عملية الرفع بنجاح!")

    except Exception as e:
        print(f"حدث خطأ أثناء الرفع: {e}")

if __name__ == "__main__":
    upload_files_to_azure()