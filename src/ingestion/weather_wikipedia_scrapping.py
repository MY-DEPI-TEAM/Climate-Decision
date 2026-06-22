import os
import textwrap
import pandas as pd
import requests
from bs4 import BeautifulSoup


def scrape_extreme_weather_egypt():
    print("Starting Web Scraping for Egypt Extreme Weather Events...")

    # Wikipedia URL as an example source rich in historical weather and extreme event data for Egypt
    # You can change this to any local meteorological source (preferably for scraping)
    url = "https://en.wikipedia.org/wiki/Climate_of_Egypt"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Failed to fetch data. Status Code: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, "html.parser")

        # Target tables within the page (example: tables of record temperatures or phenomena)
        tables = soup.find_all("table", {"class": "wikitable"})

        if not tables:
            print("No data tables found on the page.")
            return

        # We'll extract data from the first table as an example (adjust as needed for the target site's structure)
        scraped_data = []

        # Loop through the rows in the table
        for row in tables[0].find_all("tr")[1:]:  # skip header row
            cols = row.find_all(["td", "th"])
            cols_text = [col.text.strip() for col in cols]

            if cols_text:
                scraped_data.append(cols_text)

        # Convert data to a DataFrame
        # Column names are defaults based on a typical climate table on Wikipedia
        df = pd.DataFrame(scraped_data)

        # Quick columns cleanup (initial naming)
        df.columns = [f"Column_{i}" for i in range(df.shape[1])]

        # Add Source column to confirm lineage in the Lakehouse
        df["Source"] = "Web Scraping - Wikipedia Climate Data"

        # Ensure the output directory exists according to your architecture
        output_dir = "data/raw"
        os.makedirs(output_dir, exist_ok=True)

        # Save the file
        file_path = os.path.join(output_dir, "scraped_climate_insights.csv")
        df.to_csv(file_path, index=False, encoding="utf-8-sig")

        print(f"Scraping completed successfully! File saved to: {file_path}")
        print(f"Total rows scraped: {len(df)}")

    except Exception as e:
        print(f"An error occurred during scraping: {e}")


if __name__ == "__main__":
    scrape_extreme_weather_egypt()