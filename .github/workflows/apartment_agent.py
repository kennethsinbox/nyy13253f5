import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime

# --- CONFIGURATION ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/115e9wX6lXo37Q6l3cgXEFI5QTUhnVm8j0Y2sFMubI1A/edit"

def get_google_sheet():
    # Authenticate using the secret stored in GitHub
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
    # Check if 1BR is actually a J4
    if apt.get('beds') == 1:
        if "junior 4" in desc or "j4" in desc or "dining alcove" in desc or "junior 4" in title:
            return True
    return False

def run_agent():
    sheet = get_google_sheet()
    existing_addresses = sheet.col_values(2) # Column B: Address/Unit
    
    # 3. FETCH DATA
    # Note: Replace this with your actual Scraper API call (e.g., Apify or RapidAPI)
    # This is a conceptual fetch loop
    listings = fetch_listings_from_api(os.environ['API_KEY']) 
    
    new_rows = []
    for apt in listings:
        maint = apt.get('maintenance', 0)
        tax = apt.get('monthly_tax', 0)
        total_monthly = maint + tax
        
        # APPLY YOUR HARD FILTERS
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
                    total_monthly, # Spreadsheet formula: =F[row]+G[row]
                    wd_status,
                    "Yes",
                    apt.get('url')
                ]
                new_rows.append(new_row)

    if new_rows:
        sheet.append_rows(new_rows)
        print(f"Added {len(new_rows)} listings.")

def fetch_listings_from_api(key):
    # This would contain your specific GET request to StreetEasy data
    return [] 

if __name__ == "__main__":
    run_agent()
