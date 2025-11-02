import requests

# === CONFIGURATION ===
API_TOKEN = 'ngYR5EDCeQcu7gSbXmAxHyW5m4NH5wyf'
BASE_URL = 'https://intelligence.sifted.eu/api/database'
HEADERS = {
    'Authorization': f'Token {API_TOKEN}',
    'Content-Type': 'application/json'
}

TABLE_INVESTORS = 781
TABLE_COMPANY_INVESTORS = 783

# FIELD IDs
FIELD_INVESTOR_ID_INVESTORS = 'field_7547'   # investor_id in Investors
FIELD_INVESTOR_ID_COMPANY = 'field_7594'     # investor_id in Company Investors
FIELD_LINK_INVESTORS = 'field_7671'          # linked Investors field in Company Investors


# === UTILITY: Get all rows with pagination ===
def fetch_all_rows(table_id):
    rows = []
    url = f"{BASE_URL}/rows/table/{table_id}/?size=200"

    while url:
        response = requests.get(url, headers=HEADERS)
        data = response.json()
        rows.extend(data['results'])
        url = data.get('next')  # Baserow includes `next` URL for pagination

    return rows


# === STEP 1: Build map of investor_id → Investors row ID ===
investor_map = {}
print("📥 Fetching investor records...")
for row in fetch_all_rows(TABLE_INVESTORS):
    investor_id = row.get(FIELD_INVESTOR_ID_INVESTORS)
    if investor_id:
        investor_map[investor_id] = row['id']

# === STEP 2: Fetch Company Investors and only update missing links ===
print("📥 Fetching company investor records...")
for row in fetch_all_rows(TABLE_COMPANY_INVESTORS):
    company_row_id = row['id']
    investor_id = row.get(FIELD_INVESTOR_ID_COMPANY)
    current_link = row.get(FIELD_LINK_INVESTORS)

    # Only update if no link exists
    if investor_id in investor_map and not current_link:
        linked_id = investor_map[investor_id]
        data = {FIELD_LINK_INVESTORS: [linked_id]}

        patch_url = f"{BASE_URL}/rows/table/{TABLE_COMPANY_INVESTORS}/{company_row_id}/"
        response = requests.patch(patch_url, headers=HEADERS, json=data)

        if response.status_code == 200:
            print(f"✅ Linked {investor_id} to Company Investor row {company_row_id}")
        else:
            print(f"⚠️ Failed to link {investor_id}: {response.status_code} - {response.text}")
    elif current_link:
        print(f"⏭️ Skipped {investor_id} (already linked)")
    else:
        print(f"❌ No matching Investor for {investor_id}")
