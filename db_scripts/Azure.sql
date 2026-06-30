/* ============================================================
   Egypt Weather Database — SQL Server / Azure SQL
   النسخة النهائية بعد حل مشاكل BULK INSERT و SELECT INTO
   ============================================================ */


-- ============================================================
-- 0) STAGING TABLES  (تحميل الملفات الخام زي ما هي)
-- ============================================================

DROP TABLE IF EXISTS stg_governorates_weather;
CREATE TABLE stg_governorates_weather (
    governorate     VARCHAR(100),
    condition       VARCHAR(100),
    high_temp_c     NUMERIC(5,2),
    low_temp_c      NUMERIC(5,2),
    weather_date    DATE
);
BULK INSERT stg_governorates_weather
FROM 'egypt_governorates_weather.csv'
WITH (
    DATA_SOURCE = 'AzureBlobStorage',
    FORMAT = 'CSV',
    FIRSTROW = 2,
    FIELDQUOTE = '"',
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '0x0d0a',
    CODEPAGE = '65001',
    TABLOCK
);

DROP TABLE IF EXISTS stg_egypt_weather_final;
CREATE TABLE stg_egypt_weather_final (
    governorate     VARCHAR(100),
    weather_date    DATE,
    weather_code    INT,
    max_temp        NUMERIC(5,2),
    min_temp        NUMERIC(5,2),
    avg_humidity    NUMERIC(5,2),
    source          VARCHAR(200)
);
BULK INSERT stg_egypt_weather_final
FROM 'Egypt_Weather_2022_2025_Final.csv'
WITH (
    DATA_SOURCE = 'AzureBlobStorage',
    FORMAT = 'CSV',
    FIRSTROW = 2,
    FIELDQUOTE = '"',
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '0x0d0a',
    CODEPAGE = '65001',
    TABLOCK
);

DROP TABLE IF EXISTS stg_climate_insights;
CREATE TABLE stg_climate_insights (
    metric_name     VARCHAR(200),
    jan VARCHAR(50), feb VARCHAR(50), mar VARCHAR(50), apr VARCHAR(50),
    may VARCHAR(50), jun VARCHAR(50), jul VARCHAR(50), aug VARCHAR(50),
    sep VARCHAR(50), oct VARCHAR(50), nov VARCHAR(50), dec VARCHAR(50),
    year_value      VARCHAR(50),
    source          VARCHAR(200)
);
BULK INSERT stg_climate_insights
FROM 'scraped_climate_insights.csv'
WITH (
    DATA_SOURCE = 'AzureBlobStorage',
    FORMAT = 'CSV',
    FIRSTROW = 2,
    FIELDQUOTE = '"',
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '0x0d0a',
    CODEPAGE = '65001',
    TABLOCK
);

-- ملحوظة مهمة: استخدم النسخة المنظفة من الملف
-- (wikipedia_revision_history_clean.csv) بدل الأصلي،
-- لأن الأصلي كان فيه BOM + line endings غير قياسية سببت فشل التحميل.
DROP TABLE IF EXISTS stg_wikipedia_revision_history;
CREATE TABLE stg_wikipedia_revision_history (
    revision_timestamp  DATETIME2,
    [user]              NVARCHAR(MAX),
    comment             NVARCHAR(MAX),
    source              NVARCHAR(MAX)
);
BULK INSERT stg_wikipedia_revision_history
FROM 'wikipedia_revision_history_clean.csv'
WITH (
    DATA_SOURCE = 'AzureBlobStorage',
    FORMAT = 'CSV',
    FIRSTROW = 2,
    FIELDQUOTE = '"',
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '0x0d0a',
    CODEPAGE = '65001',
    TABLOCK
);

-- ============================================================
-- 1) FIRST TABLE: merged_weather
--    دمج ملف 1 (egypt_governorates_weather) وملف 2 (Egypt_Weather_2022_2025_Final)
--    على (governorate + date)
-- ============================================================

DROP TABLE IF EXISTS merged_weather;

WITH joined AS (
    SELECT
        COALESCE(g.governorate, e.governorate)   AS governorate,
        COALESCE(g.weather_date, e.weather_date) AS date,
        e.weather_code                           AS weather_code,
        g.condition                              AS condition,
        g.high_temp_c                            AS high_temp_c,
        e.max_temp                               AS max_temp,
        g.low_temp_c                             AS low_temp_c,
        e.min_temp                               AS min_temp,
        e.avg_humidity                           AS avg_humidity,
        (CASE WHEN g.high_temp_c IS NULL THEN 0 ELSE 1 END
       + CASE WHEN e.max_temp   IS NULL THEN 0 ELSE 1 END) AS max_cnt,
        (CASE WHEN g.low_temp_c IS NULL THEN 0 ELSE 1 END
       + CASE WHEN e.min_temp  IS NULL THEN 0 ELSE 1 END)  AS min_cnt
    FROM stg_governorates_weather g
    FULL OUTER JOIN stg_egypt_weather_final e
           ON g.governorate  = e.governorate
          AND g.weather_date = e.weather_date
)
SELECT
    CONCAT(governorate, '_', FORMAT(date, 'yyyy-MM-dd')) AS id,
    governorate,
    date,
    weather_code,
    condition,
    high_temp_c,
    max_temp,
    ROUND( (ISNULL(high_temp_c, 0) + ISNULL(max_temp, 0)) / NULLIF(max_cnt, 0), 2 ) AS avg_max_temp,
    ROUND(
        CASE
            WHEN high_temp_c IS NOT NULL AND max_temp IS NOT NULL THEN
                (CASE WHEN high_temp_c > max_temp THEN high_temp_c ELSE max_temp END) -
                (CASE WHEN high_temp_c < max_temp THEN high_temp_c ELSE max_temp END)
            ELSE 0
        END, 2) AS range_max_temp,
    CASE
        WHEN max_cnt = 2 THEN ROUND( SQRT(
                ( POWER(high_temp_c - ((high_temp_c + max_temp) / 2.0), 2)
                + POWER(max_temp   - ((high_temp_c + max_temp) / 2.0), 2) ) / 2.0
            ), 2)
        WHEN max_cnt = 1 THEN 0
        ELSE NULL
    END AS std_max_temp,
    low_temp_c,
    min_temp,
    ROUND( (ISNULL(low_temp_c, 0) + ISNULL(min_temp, 0)) / NULLIF(min_cnt, 0), 2 ) AS avg_min_temp,
    ROUND(
        CASE
            WHEN low_temp_c IS NOT NULL AND min_temp IS NOT NULL THEN
                (CASE WHEN low_temp_c > min_temp THEN low_temp_c ELSE min_temp END) -
                (CASE WHEN low_temp_c < min_temp THEN low_temp_c ELSE min_temp END)
            ELSE 0
        END, 2) AS range_min_temp,
    CASE
        WHEN min_cnt = 2 THEN ROUND( SQRT(
                ( POWER(low_temp_c - ((low_temp_c + min_temp) / 2.0), 2)
                + POWER(min_temp   - ((low_temp_c + min_temp) / 2.0), 2) ) / 2.0
            ), 2)
        WHEN min_cnt = 1 THEN 0
        ELSE NULL
    END AS std_min_temp,
    avg_humidity
INTO merged_weather
FROM joined;

ALTER TABLE merged_weather ADD CONSTRAINT PK_merged_weather PRIMARY KEY (id);


-- ============================================================
-- 2) SECOND TABLE: climate_insights
-- ============================================================

DROP TABLE IF EXISTS climate_insights;
DROP TABLE IF EXISTS climate_insights_long;

SELECT
    metric_name, jan, feb, mar, apr, may, jun,
    jul, aug, sep, oct, nov, dec, year_value, source
INTO climate_insights
FROM stg_climate_insights;

SELECT metric_name, 1  AS month_num, jan AS value INTO climate_insights_long FROM stg_climate_insights
UNION ALL SELECT metric_name, 2,  feb FROM stg_climate_insights
UNION ALL SELECT metric_name, 3,  mar FROM stg_climate_insights
UNION ALL SELECT metric_name, 4,  apr FROM stg_climate_insights
UNION ALL SELECT metric_name, 5,  may FROM stg_climate_insights
UNION ALL SELECT metric_name, 6,  jun FROM stg_climate_insights
UNION ALL SELECT metric_name, 7,  jul FROM stg_climate_insights
UNION ALL SELECT metric_name, 8,  aug FROM stg_climate_insights
UNION ALL SELECT metric_name, 9,  sep FROM stg_climate_insights
UNION ALL SELECT metric_name, 10, oct FROM stg_climate_insights
UNION ALL SELECT metric_name, 11, nov FROM stg_climate_insights
UNION ALL SELECT metric_name, 12, dec FROM stg_climate_insights;


-- ============================================================
-- 3) THIRD TABLE: wikipedia_revision_history
--    ملحوظة: استخدمنا CREATE TABLE + INSERT INTO بدل SELECT INTO
--    لأن SELECT INTO كانت بتسبب Error 8601 (internal Azure SQL error)
-- ============================================================

DROP TABLE IF EXISTS wikipedia_revision_history;

CREATE TABLE wikipedia_revision_history (
    revision_timestamp  DATETIME2,
    [user]              NVARCHAR(MAX),
    comment             NVARCHAR(MAX),
    source              NVARCHAR(MAX)
);

INSERT INTO wikipedia_revision_history (revision_timestamp, [user], comment, source)
SELECT
    CAST(revision_timestamp AS DATETIME2),
    [user],
    comment,
    source
FROM stg_wikipedia_revision_history;


-- ============================================================
-- 4) RELATIONS / EXAMPLE QUERIES
-- ============================================================

-- (أ) الربط بين merged_weather و climate_insights_long بالشهر
SELECT
    mw.*,
    ci.metric_name,
    ci.value AS climate_normal_value
FROM merged_weather mw
JOIN climate_insights_long ci
     ON MONTH(mw.date) = ci.month_num;

-- (ب) الربط بين merged_weather و wikipedia_revision_history
--     Snapshot / As-Of Join: لكل صف طقس، نجيب آخر revision
--     حصلت في صفحة الويكيبيديا في نفس يوم أو قبل تاريخ الطقس
SELECT
    mw.*,
    w.revision_timestamp,
    w.[user],
    w.comment
FROM merged_weather mw
OUTER APPLY (
    SELECT TOP 1 revision_timestamp, [user], comment
    FROM wikipedia_revision_history w
    WHERE CAST(w.revision_timestamp AS DATE) <= mw.date
    ORDER BY w.revision_timestamp DESC
) w;