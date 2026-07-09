from __future__ import annotations

import os
import re
from pathlib import Path
from datetime import datetime, date, timedelta

import pandas as pd
from flask import Flask, Response, jsonify, render_template, request
from openai import OpenAI

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
FORECAST_CSV_PATH = BASE_DIR / "data" / "predictions" / "weather_forecast_next_6_months.csv"

NVIDIA_BASE_URL = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_MODEL = os.environ.get("NVIDIA_MODEL", "deepseek-ai/deepseek-v4-pro")
NVIDIA_API_KEY = os.environ.get("nvidia_api_key")

app = Flask(__name__)
client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY) if NVIDIA_API_KEY else None

# ---------------------------------------------------------------------------
# Load forecast data once at startup
# ---------------------------------------------------------------------------
try:
    DF: pd.DataFrame = pd.read_csv(FORECAST_CSV_PATH)
    if "date" in DF.columns:
        DF["date"] = pd.to_datetime(DF["date"]).dt.date
    if "governorate" not in DF.columns and "city_encoded" in DF.columns:
        DF["governorate"] = DF["city_encoded"].astype(str)
    if "avg_max_temp" not in DF.columns and "predicted_max_temp" in DF.columns:
        DF["avg_max_temp"] = DF["predicted_max_temp"]
    if "avg_min_temp" not in DF.columns and "predicted_min_temp" in DF.columns:
        DF["avg_min_temp"] = DF["predicted_min_temp"]
    if "avg_humidity" not in DF.columns:
        DF["avg_humidity"] = 0.0
    if "temp_range" not in DF.columns:
        DF["temp_range"] = DF["avg_max_temp"] - DF["avg_min_temp"]
    if "heat_level" not in DF.columns:
        DF["heat_level"] = "moderate"
    if "season" not in DF.columns:
        DF["season"] = "forecast"
    print(f"[✓] Loaded {len(DF):,} rows | {DF['date'].min()} → {DF['date'].max()}")
except Exception as exc:
    print(f"[✗] Failed to load forecast CSV: {exc}")
    DF = pd.DataFrame()

ALL_GOVERNORATES = sorted(DF["governorate"].unique().tolist()) if not DF.empty else []

# ---------------------------------------------------------------------------
# RAG Retriever
# ---------------------------------------------------------------------------
def _extract_date(text: str) -> date | None:
    normalized_text = (text or "").strip().lower()

    relative_terms = {
        "today": date.today(),
        "اليوم": date.today(),
        "tomorrow": date.today() + timedelta(days=1),
        "غدا": date.today() + timedelta(days=1),
        "غدًا": date.today() + timedelta(days=1),
        "yesterday": date.today() - timedelta(days=1),
        "امس": date.today() - timedelta(days=1),
        "أمس": date.today() - timedelta(days=1),
    }

    for term, resolved_date in relative_terms.items():
        if term in normalized_text:
            return resolved_date

    patterns = [
        r"\b(\d{4}-\d{2}-\d{2})\b",           # 2026-07-15
        r"\b(\d{1,2}/\d{1,2}/\d{4})\b",        # 15/7/2026
        r"\b(\d{1,2}-\d{1,2}-\d{4})\b",        # 15-7-2026
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    return datetime.strptime(m.group(1), fmt).date()
                except ValueError:
                    continue
    return None


def _extract_governorate(text: str) -> str | None:
    if not ALL_GOVERNORATES:
        return None
    
    # استخدام تفكيك الكلمات لمنع التطابق الجزئي الخاطئ
    words = re.findall(r'\b\w+ \b', text.lower()) or text.lower().split()
    for gov in ALL_GOVERNORATES:
        if gov.lower() in text.lower(): 
            # حماية بسيطة للتأكد من مطابقة اسم المحافظة ككلمة كاملة أو جزء منطقي
            return gov
    return None


def _retrieve_context(user_message: str) -> tuple[str, str]:
    if DF.empty:
        return "No data available.", "No data loaded."

    target_date  = _extract_date(user_message)
    target_gov   = _extract_governorate(user_message)

    # فلترة مباشرة بدون استخدام .copy() الكامل غير المبرر
    mask = pd.Series(True, index=DF.index)
    retrieval_info = []

    if target_date:
        mask &= (DF["date"] == target_date)
        retrieval_info.append(f"Date: {target_date}")

    if target_gov:
        mask &= (DF["governorate"] == target_gov)
        retrieval_info.append(f"Governorate: {target_gov}")

    # إذا لم يحدد شيء، نجلب أحدث تاريخ للمحافظة المحددة أو أحدث تاريخ عام
    if not target_date and not target_gov:
        latest = DF["date"].max()
        mask &= (DF["date"] == latest)
        retrieval_info.append(f"Latest available date: {latest}")
    elif not target_date and target_gov:
        latest_for_gov = DF[DF["governorate"] == target_gov]["date"].max()
        mask &= (DF["date"] == latest_for_gov)
        retrieval_info.append(f"Latest date for {target_gov}: {latest_for_gov}")

    filtered = DF[mask]

    # إذا لم يجد التاريخ المطلوب، يبحث عن الأقرب
    if filtered.empty and target_date:
        available_dates = pd.Series(DF["date"].unique())
        closest = min(available_dates, key=lambda d: abs((d - target_date).days))
        
        fallback_mask = (DF["date"] == closest)
        if target_gov:
            fallback_mask &= (DF["governorate"] == target_gov)
            
        filtered = DF[fallback_mask]
        retrieval_info.append(f"Closest available date: {closest} (requested: {target_date})")

    if filtered.empty:
        return "No matching data found for your query.", " | ".join(retrieval_info)

    # تحديد حد أقصى للـ rows المرسلة منعاً لضخامة الـ Context (مثلاً أول 5 صفوف فقط لو تشابهت المحافظات)
    lines = []
    for _, row in filtered.head(5).iterrows():
        lines.append(
            f"- {row['governorate']} on {row['date']}: "
            f"Max {row['avg_max_temp']}°C, Min {row['avg_min_temp']}°C, "
            f"Humidity {row['avg_humidity']}%, "
            f"Temp Range {row['temp_range']}°C, "
            f"Heat Level: {row['heat_level']}, "
            f"Season: {row['season']}"
        )

    context = "\n".join(lines)
    return context, " | ".join(retrieval_info)


# ---------------------------------------------------------------------------
# NVIDIA LLM Client
# ---------------------------------------------------------------------------
def _ask_llm(user_message: str):
    context, _ = _retrieve_context(user_message)

    system_prompt = f"""You are an expert Climate & Weather Advisor for Egypt.
You ONLY answer based on the retrieved weather data below. Do NOT use external knowledge.

=== RETRIEVED WEATHER DATA ===
{context}
=== END OF DATA ===

Rules:
- Give specific, actionable advice based on the temperatures and heat level.
- Cover: health, agriculture, transport, energy, daily activities.
- If heat_level is "extreme" (≥45°C): warn strongly about outdoor activities.
- If heat_level is "high" (≥35°C): recommend hydration, avoid midday sun.
- If heat_level is "moderate" (≥25°C): general comfort tips.
- If heat_level is "low": pleasant weather tips.
- Be concise and use bullet points.
- If the data doesn't cover the requested date/location, say so clearly.
"""

    if client is None:
        yield "⚠️ NVIDIA API key is not configured. Set the 'nvidia_api_key' environment variable."
        return

    try:
        response = client.chat.completions.create(
            model=NVIDIA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            top_p=0.95,
            max_tokens=1024,
            extra_body={"chat_template_kwargs": {"thinking": False}},
            stream=True,
        )

        for chunk in response:
            delta = getattr(chunk.choices[0], "delta", None)
            content = getattr(delta, "content", None)
            if content:
                yield content
    except Exception as exc:
        yield f"⚠️ Error: {exc}"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html",
                           date_range=f"{DF['date'].min()} → {DF['date'].max()}" if not DF.empty else "N/A",
                           governorates=ALL_GOVERNORATES)


@app.route("/ask", methods=["POST"])
def ask():
    data    = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message is required"}), 400

    return Response(
        _ask_llm(message),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/suggestions", methods=["GET"])
def suggestions():
    if DF.empty:
        return jsonify({"suggestions": ["What data is available?"]})

    try:
        latest = DF["date"].max()
        hottest_row = DF.loc[DF["avg_max_temp"].idxmax()]
        
        # صياغة مرنة للاقتراحات
        return jsonify({"suggestions": [
            f"What are the weather conditions in Cairo on {latest}? Give me health advice.",
            f"The hottest recorded day was {hottest_row['date']} in {hottest_row['governorate']} ({hottest_row['avg_max_temp']}°C). What precautions should I take?",
            f"Compare weather between Alexandria and Cairo on {latest}.",
        ]})
    except Exception:
        return jsonify({"suggestions": ["What is the weather like today?"]})


@app.route("/governorates", methods=["GET"])
def governorates():
    return jsonify({"governorates": ALL_GOVERNORATES})


@app.route("/data/<governorate>/<date_str>", methods=["GET"])
def get_data(governorate: str, date_str: str):
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    row = DF[(DF["date"] == target_date) & (DF["governorate"] == governorate)]
    if row.empty:
        return jsonify({"error": f"No data for {governorate} on {date_str}"}), 404

    return jsonify(row.iloc[0].to_dict())


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)