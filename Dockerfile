# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.11.9
FROM python:${PYTHON_VERSION}-slim as base

# منع بايثون من كتابة ملفات الـ pyc وضمان ظهور اللوجز فوراً
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# تسطيب الـ ODBC Drivers للـ SQL Server متوافق مع Debian 12
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    build-essential \
    unixodbc-dev \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# تحميل المكتبات باستخدام الـ Cache mount لتسريع الـ Builds الجاية
COPY requirements.txt requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install -r requirements.txt

# نسخ كود المشروع بالكامل جوه الـ Container
COPY . .

# تشغيل الـ Pipeline الرئيسي عند قومة الـ Container
CMD ["python", "main.py"]