#weps2
import re
import time
import csv
import calendar
from pathlib import Path
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ---- قاموس يضم جميع محافظات ومحطات مصر المتاحة على الموقع ----
GOVERNORATES_STATIONS = {
    "Cairo": "Cairo",                      # القاهرة
    "Giza": "Giza",                        # الجيزة
    "Alexandria": "Alexandria",            # الإسكندرية
    "Port Said": "Port-Said",              # بور سعيد
    "Suez": "Suez",                        # السويس
    "Damietta": "Damietta",                # دمياط
    "Dakahlia": "Al-Mansurah",             # الدقهلية (المنصورة)
    "Sharkia": "Zagazig",                  # الشرقية (الزقازيق)
    "Kalyoubia": "Banha",                  # القليوبية (بنها)
    "Kafr El Sheikh": "Kafr-el-Sheikh",    # كفر الشيخ
    "Gharbia": "Tanta",                    # الغربية (طنطا)
    "Monufia": "Shibin-al-Kawm",           # المنوفية (شبين الكوم)
    "Beheira": "Damanhur",                 # البحيرة (دمنهور)
    "Ismailia": "Ismailia",                # الإسماعيلية
    "Giza_6th_October": "6th-of-October",  # السادس من أكتوبر
    "Beni Suef": "Beni-Suef",              # بني سويف
    "Fayoum": "Al-Fayyum",                 # الفيوم
    "Minya": "Al-Minya",                   # المنيا
    "Asyut": "Asyut",                      # أسيوط
    "Sohag": "Sohag",                      # سوهاج
    "Qena": "Qena",                        # قنا
    "Luxor": "Luxor",                      # الأقصر
    "Aswan": "Aswan",                      # أسوان
    "Red Sea": "Hurghada",                 # البحر الأحمر (الغردقة)
    "New Valley": "Al-Khargah",            # الوادي الجديد (الخارجة)
    "Matrouh": "Siwa",                     # مطروح (سيوة / مرسى مطروح)
    "North Sinai": "Al-Arish",             # شمال سيناء (العريش)
    "South Sinai": "El-Tor"                # جنوب سيناء (الطور)
}

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def f_to_c(text):
    """Convert temperature from Fahrenheit to Celsius (rounded to one decimal place)."""
    m = re.search(r"-?\d+", text)
    if not m:
        return ""
    f = int(m.group())
    return str(round((f - 32) * 5 / 9, 1))

def extract_day_number(cell):
    """Read the actual day number printed inside a calendar cell."""
    frag = BeautifulSoup(str(cell), "lxml")
    for cls in ("phrase", "hi", "low"):
        for el in frag.find_all(class_=cls):
            el.decompose()
    m = re.search(r"\d{1,2}", frag.get_text())
    return int(m.group()) if m else None

def longest_increasing_run(seq):
    """Return the longest increasing consecutive run of numbers."""
    if not seq:
        return (0, -1)
    best_start, best_len = 0, 1
    cur_start = 0
    for k in range(1, len(seq)):
        if seq[k] <= seq[k - 1]:
            cur_start = k 
        cur_len = k - cur_start + 1
        if cur_len > best_len:
            best_len, best_start = cur_len, cur_start
    return best_start, best_start + best_len - 1

def main():
    # Configure the headless browser
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)

    weather_list = []

    # المرور على جميع المحافظات المتواجدة في القاموس
    for gov_name, station_code in GOVERNORATES_STATIONS.items():
        print(f"\n[+] Starting data collection for: {gov_name} ({station_code})")
        
        # تصفير التواريخ المشاهدة لكل محافظة على حدة
        seen_dates = set()

        for n in range(2022, 2026):          # من سنة 2022 إلى 2025
            for i in range(1, 13):           # الشهور من 1 إلى 12
                url = f"https://www.wunderground.com/calendar/eg/{station_code}/HEAT/date/{n}-{i:02d}"

                try:
                    driver.get(url)
                    time.sleep(6)  # الانتظار حتى تحميل بيانات التقويم

                    src = driver.page_source
                    soup = BeautifulSoup(src, "lxml")

                    # جلب خلايا الأيام
                    days = soup.find_all("li", class_=lambda x: x and 'calendar-day' in x)

                    month_cells = []
                    for day in days:
                        phrase_elem = day.find("div", class_="phrase")
                        hi_elem = day.find("span", class_="hi")
                        low_elem = day.find("span", class_="low")

                        if phrase_elem and hi_elem and low_elem:
                            day_num = extract_day_number(day)
                            if day_num is None:
                                continue
                            condition = phrase_elem.text.strip()
                            high_temp = f_to_c(hi_elem.text.strip())
                            low_temp = f_to_c(low_elem.text.strip())
                            month_cells.append((day_num, condition, high_temp, low_temp))

                    # تصفية الأيام الخاصة بالشهر الحالي فقط
                    nums = [c[0] for c in month_cells]
                    start, end = longest_increasing_run(nums)
                    real_days = month_cells[start:end + 1]

                    dim = calendar.monthrange(n, i)[1]
                    for day_num, condition, high_temp, low_temp in real_days:
                        if not (1 <= day_num <= dim):
                            continue
                        full_date = f"{n}-{i:02d}-{day_num:02d}"

                        if full_date in seen_dates:
                            continue
                        seen_dates.add(full_date)

                        # إدراج اسم المحافظة الحالية المتغيرة في القائمة
                        weather_list.append([gov_name, condition, high_temp, low_temp, full_date])

                    print(f"   -> {n}-{i:02d} | Rows in this batch: {len(real_days)} | Total collected: {len(weather_list)}")
                
                except Exception as e:
                    print(f"   [!] Error loading {n}-{i:02d} for {gov_name}: {e}")
                    continue

    driver.quit()

    # حفظ جميع البيانات المجمعة في ملف CSV واحد
    if weather_list:
        output_path = OUTPUT_DIR / "egypt_governorates_weather.csv"
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Governorate", "Condition", "High Temp (C)", "Low Temp (C)", "Date"])
            writer.writerows(weather_list)

        print(f"\n[✓] Done! Data for all governorates successfully saved to: {output_path}")
    else:
        print("\n[X] No weather data was found.")

if __name__ == "__main__":
    main()