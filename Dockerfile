FROM python:3.11-slim

# منع بايثون من كتابة ملفات الكاش وللإخراج المباشر في الـ Logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# نسخ ملف المتطلبات وتثبيته
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ ملفات المشروع
COPY . .

# فتح منفذ الويب
EXPOSE 5000

# تشغيل تطبيق الويب مباشرة
CMD ["python", "app.py"]