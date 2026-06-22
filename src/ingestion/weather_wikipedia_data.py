import pandas as pd
import requests

# 1. Set the base URL for the Wikipedia API
url = "https://en.wikipedia.org/w/api.php"

# 2. Prepare the parameters required by the API
params = {
    "action": "query",  # operation type: query
    "prop": "revisions",  # we want to fetch revision history
    "titles": "Climate of Egypt",  # exact target page title
    "rvprop": "timestamp|user|comment",  # data fields: timestamp, user, comment
    "rvlimit": 500,  # number of revisions to fetch (max 500)
    "format": "json",  # response format
}

# 3. Add headers to avoid blocking and identify the project
headers = {
    "User-Agent": "ClimateDataPipeline/1.0 (contact_email@example.com)"  # change the email to yours if desired
}

try:
    print("Connecting to the Wikipedia API to fetch revision history...")
    response = requests.get(url, params=params, headers=headers, timeout=15)

    if response.status_code == 200:
        data = response.json()

        # 4. Extract revisions from the JSON structure
        pages = data["query"]["pages"]
        revisions_list = []

        for page_id in pages:
            revisions = pages[page_id].get("revisions", [])
            for rev in revisions:
                revisions_list.append(
                    {
                        "Timestamp": rev.get("timestamp"),
                        "User": rev.get("user"),
                        "Comment": rev.get("comment", ""),  # some revisions may not have a comment
                    }
                )

        # 5. Convert the data to a DataFrame for organization
        df_revisions = pd.DataFrame(revisions_list)

        # Add a Source column to document lineage in the Lakehouse
        df_revisions["Source"] = "Wikipedia API - Revision History"

        # 6. Display sample and save as CSV
        print("\nSample of extracted data:")
        print(df_revisions.head())

        output_path = "data/raw/wikipedia_revision_history.csv"
        # Ensure directories exist
        import os

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        df_revisions.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"\nSaved revision history successfully to Raw folder: {output_path}")
        print(f"Total revisions fetched: {len(df_revisions)}")

    else:
        print(f"Failed to connect to the API. Status code: {response.status_code}")

except Exception as e:
    print(f"An unexpected error occurred while fetching: {e}")