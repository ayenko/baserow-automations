import requests
import time

# === CONFIGURATION ===
API_TOKEN = 'ngYR5EDCeQcu7gSbXmAxHyW5m4NH5wyf'
BASE_URL = 'https://intelligence.sifted.eu/api/database'
HEADERS = {
    'Authorization': f'Token {API_TOKEN}',
    'Content-Type': 'application/json'
}

# === TABLE IDs ===
TABLE_INVESTORS = 781
TABLE_COMPANY_INVESTORS = 783
TABLE_DEALS = 780
TABLE_INVESTOR_TRACKER = 789
TABLE_LOG = 790
TABLE_SYNC_TRACKER = 791

# === FIELD IDs ===
# Investors Table
INVESTOR_ID = 'field_7547'
INVESTOR_NAME = 'field_7548'
HQ_COUNTRY = 'field_7551'
INVESTOR_TYPE = 'field_7553'
WEBSITE = 'field_7556'
IS_CURRENT = 'field_7559'

# Company Investors Table
CI_INVESTOR_ID = 'field_7594'
CI_COMPANY_ID = 'field_7593'
CI_INVESTOR_ROLE = 'field_7595'

# Deals Table
DEALS_COMPANY_ID = 'field_7521'
DEALS_SIZE = 'field_7528'
DEALS_HQ = 'field_7531'
DEALS_VERTICAL = 'field_7533'
DEALS_STAGE = 'field_7536'
DEALS_SECTOR = 'field_7534'

# Investor Tracker Table
IT_NAME = 'field_7754'
IT_URL = 'field_7757'
IT_HQ = 'field_7758'
IT_TYPE = 'field_7759'
IT_DEALCOUNT_LEAD = 'field_7760'
IT_DEALCOUNT_PARTICIPATING = 'field_7761'
IT_AVG_DEAL_SIZE = 'field_7763'
IT_COUNTRY_FOCUS = 'field_7764'
IT_VERTICAL_FOCUS = 'field_7765'
IT_STAGE_FOCUS = 'field_7766'
IT_SECTOR_FOCUS = 'field_7767'

# Log Table
LOG_PRODUCT_NAME = 'field_7768'
LOG_INVESTOR_NAME = 'field_7771'
LOG_ERROR_DETAILS = 'field_7772'

# Sync Tracker Table
SYNC_PRODUCT_NAME = 'field_7774'
SYNC_RECORDS_CREATED = 'field_7778'
SYNC_TOTAL_RECORDS = 'field_7779'
SYNC_RECORDS_UPDATED = 'field_7780'

# === Helper Functions ===

def fetch_all_rows(table_id):
    rows = []
    url = f"{BASE_URL}/rows/table/{table_id}/?size=200"
    while url:
        response = requests.get(url, headers=HEADERS)
        data = response.json()
        rows.extend(data['results'])
        url = data.get('next')
    return rows

def split_multi_value(text):
    if text:
        return [x.strip() for x in text.split(',') if x.strip()]
    return []

def api_request(method, url, data=None, retries=3):
    for attempt in range(retries):
        try:
            if method == "POST":
                r = requests.post(url, headers=HEADERS, json=data)
            elif method == "PATCH":
                r = requests.patch(url, headers=HEADERS, json=data)
            else:
                raise ValueError("Unsupported method")

            if r.status_code in [200, 201]:
                return True
            else:
                print(f"⚠️ API call failed (attempt {attempt+1}/{retries}): {r.status_code} - {r.text}")
                time.sleep(2)
        except Exception as e:
            print(f"⚠️ Exception during API call (attempt {attempt+1}/{retries}): {e}")
            time.sleep(2)
    return False

def safe_deal_size(deal):
    size = deal.get(DEALS_SIZE, 0)
    try:
        return float(size)
    except (ValueError, TypeError):
        return 0

# 🛠️ Corrected Sector Cleaning
def clean_sector_list(sector_list):
    cleaned = []
    temp = set()

    for sector in sector_list:
        sector = sector.strip()
        if sector == '"Smart homes':
            temp.add('Smart homes')
        elif sector == 'buildings & cities"':
            temp.add('buildings & cities')
        else:
            cleaned.append(sector)

    if 'Smart homes' in temp and 'buildings & cities' in temp:
        cleaned.append('Smart homes & cities')

    return cleaned

# 📝 Log Error into Error Table
def log_error_to_baserow(investor_name, error_message):
    log_data = {
        LOG_PRODUCT_NAME: 'Investor Tracker',
        LOG_INVESTOR_NAME: investor_name,
        LOG_ERROR_DETAILS: error_message
    }
    url = f"{BASE_URL}/rows/table/{TABLE_LOG}/"
    api_request("POST", url, log_data)

# 🗓️ Log Sync Summary into Sync Tracker Table
def log_sync_summary(created_count, updated_count, total_records):
    sync_data = {
        SYNC_PRODUCT_NAME: 'Investor Tracker',
        SYNC_RECORDS_CREATED: created_count,
        SYNC_RECORDS_UPDATED: updated_count,
        SYNC_TOTAL_RECORDS: total_records
    }
    url = f"{BASE_URL}/rows/table/{TABLE_SYNC_TRACKER}/"
    api_request("POST", url, sync_data)

# === MAIN SCRIPT ===

print("📥 Fetching investors...")
investors = fetch_all_rows(TABLE_INVESTORS)

print("📥 Fetching company investors...")
company_investors = fetch_all_rows(TABLE_COMPANY_INVESTORS)

print("📥 Fetching deals...")
deals = fetch_all_rows(TABLE_DEALS)

print("📥 Fetching existing investor tracker rows...")
existing_tracker = fetch_all_rows(TABLE_INVESTOR_TRACKER)

tracker_by_name = {row.get(IT_NAME): row['id'] for row in existing_tracker if row.get(IT_NAME)}

# Build lookup dictionaries
ci_by_investor = {}
for ci in company_investors:
    inv_id = ci.get(CI_INVESTOR_ID)
    if inv_id:
        ci_by_investor.setdefault(inv_id, []).append(ci)

deals_by_company = {}
for deal in deals:
    company_id = deal.get(DEALS_COMPANY_ID)
    if company_id:
        deals_by_company.setdefault(company_id, []).append(deal)

# Counters
created_count = 0
updated_count = 0

# Process each investor
for investor in investors:
    try:
        if not investor.get(IS_CURRENT):
            continue

        inv_id = investor.get(INVESTOR_ID)
        if not inv_id:
            log_error_to_baserow(investor.get(INVESTOR_NAME, 'Unknown'), 'Missing investor_id')
            continue

        name = investor.get(INVESTOR_NAME)
        url = investor.get(WEBSITE)
        hq_country = investor.get(HQ_COUNTRY)
        inv_type = investor.get(INVESTOR_TYPE) or 'Unknown'

        deal_lead = 0
        deal_participating = 0
        total_deal_sizes = []

        focus_country = None
        focus_vertical = []
        focus_stage = None
        focus_sector = []

        investor_cis = ci_by_investor.get(inv_id, [])
        all_investor_deals = []

        for ci in investor_cis:
            role = ci.get(CI_INVESTOR_ROLE)
            company_id = ci.get(CI_COMPANY_ID)
            company_deals = deals_by_company.get(company_id, [])

            for deal in company_deals:
                deal_size = deal.get(DEALS_SIZE)
                if deal_size is not None and deal_size != '':
                    try:
                        deal_size = float(deal_size)
                        total_deal_sizes.append(deal_size)
                    except (ValueError, TypeError):
                        pass
                all_investor_deals.append(deal)

            if role == 'Lead':
                deal_lead += len(company_deals)
            elif role == 'Other':
                deal_participating += len(company_deals)

        if total_deal_sizes:
            avg_deal_size = round(sum(total_deal_sizes) / len(total_deal_sizes))
        else:
            avg_deal_size = None

        if all_investor_deals:
            best_deal = max(all_investor_deals, key=safe_deal_size)
            focus_country = best_deal.get(DEALS_HQ) or None
            focus_vertical = split_multi_value(best_deal.get(DEALS_VERTICAL) or '')
            focus_stage = best_deal.get(DEALS_STAGE) or None
            raw_sector = split_multi_value(best_deal.get(DEALS_SECTOR) or '')
            focus_sector = clean_sector_list(raw_sector)

        # Prepare payload
        data = {
            IT_NAME: name,
            IT_URL: url,
            IT_HQ: hq_country,
            IT_TYPE: inv_type,
            IT_DEALCOUNT_LEAD: deal_lead,
            IT_DEALCOUNT_PARTICIPATING: deal_participating,
            IT_AVG_DEAL_SIZE: avg_deal_size,
            IT_COUNTRY_FOCUS: focus_country,
            IT_VERTICAL_FOCUS: focus_vertical,
            IT_STAGE_FOCUS: focus_stage,
            IT_SECTOR_FOCUS: focus_sector
        }

        if name in tracker_by_name:
            tracker_row_id = tracker_by_name[name]
            url_api = f"{BASE_URL}/rows/table/{TABLE_INVESTOR_TRACKER}/{tracker_row_id}/"
            success = api_request("PATCH", url_api, data)
            if success:
                print(f"🔄 Updated tracker entry for {name}")
                updated_count += 1
            else:
                log_error_to_baserow(name, 'Failed to update: API error')
        else:
            url_api = f"{BASE_URL}/rows/table/{TABLE_INVESTOR_TRACKER}/"
            success = api_request("POST", url_api, data)
            if success:
                print(f"✅ Created tracker entry for {name}")
                created_count += 1
            else:
                log_error_to_baserow(name, 'Failed to create: API error')

    except Exception as e:
        log_error_to_baserow(investor.get(INVESTOR_NAME, 'Unknown'), f'Exception: {e}')

# Save sync summary
total_records = len(fetch_all_rows(TABLE_INVESTOR_TRACKER))
log_sync_summary(created_count, updated_count, total_records)

print("✅ Finished processing investors")
