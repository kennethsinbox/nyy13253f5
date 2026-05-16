import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime

# --- CONFIGURATION ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/115e9wX6lXo37Q6l3cgXEFI5QTUhnVm8j0Y2sFMubI1A/edit"


def get_google_sheet():
    creds_json = json.loads(os.environ['GOOGLE_CREDENTIALS'])
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)
    return client.open_by_url(SHEET_URL).sheet1


def detect_wd_policy(description):
    desc = description.lower()
    if any(x in desc for x in ["w/d in unit", "washer/dryer in unit", "washer and dryer in unit"]):
        return "In-Unit"
    if any(x in desc for x in ["w/d allowed", "washer allowed", "washer/dryer permitted"]):
        return "Allowed"
    return "Building/No"


def is_junior_4(apt):
    desc = apt.get('description', "").lower()
    title = apt.get('title', "").lower()
    if apt.get('beds') == 1:
        if "junior 4" in desc or "j4" in desc or "dining alcove" in desc or "junior 4" in title:
            return True
    return False


def fetch_listings_from_api(api_key):
    """Fetch listings from Apify StreetEasy scraper."""
    search_url = "https://streeteasy.com/for-sale/manhattan/status:open%7Cbeds%3A2"
    apify_url = f"https://api.apify.com/v2/acts/jupri~streeteasy-scraper/run-sync-get-dataset-items?token={api_key}"
    payload = {
        "search_url": search_url,
        "max_items": 20,
        "proxy_configuration": {"useApifyProxy": True}
    }
    try:
        response = requests.post(apify_url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching from Apify: {e}")
        return []


def run_agent():
    sheet = get_google_sheet()
    existing_addresses = sheet.col_values(2)  # Column B: Address/Unit

    api_key = os.environ.get('API_KEY', '')
    if not api_key:
        print("Warning: API_KEY secret not set. No listings will be fetched.")
        return

    listings = fetch_listings_from_api(api_key)
    print(f"Fetched {len(listings)} listings from API.")

    new_rows = []
    for apt in listings:
        maint = apt.get('maintenance', 0) or 0
        tax = apt.get('monthly_tax', 0) or 0
        total_monthly = maint + tax

        # Apply hard filters: total monthly cost <= 3000 AND doorman building
        if total_monthly <= 3000 and apt.get('doorman'):
            address_key = f"{apt.get('address')} {apt.get('unit')}"
            if address_key not in existing_addresses:
                wd_status = detect_wd_policy(apt.get('description', ""))
                apt_type = "J4 (1BR conv)" if is_junior_4(apt) else apt.get('type')

                new_row = [
                    datetime.now().strftime("%Y-%m-%d"),
                    apt.get('address'),
                    apt.get('unit'),
                    apt_type,
                    apt.get('price'),
                    apt.get('sq_ft'),
                    maint,
                    tax,
                    total_monthly,
                    wd_status,
                    "Yes",
                    apt.get('url')
                ]
                new_rows.append(new_row)

    if new_rows:
        sheet.append_rows(new_rows)
        print(f"Added {len(new_rows)} new listings to the sheet.")
    else:
        print("No new listings found matching your criteria.")


if __name__ == "__main__":
    run_agent()
