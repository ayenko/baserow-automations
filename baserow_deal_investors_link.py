import requests

# === CONFIGURATION ===
API_TOKEN = 'ngYR5EDCeQcu7gSbXmAxHyW5m4NH5wyf'
BASE_URL = 'https://intelligence.sifted.eu/api/database'
HEADERS = {
    'Authorization': f'Token {API_TOKEN}',
    'Content-Type': 'application/json'
}

TABLE_DEALS = 786
TABLE_COMPANY_INVESTORS = 783

FIELD_COMPANY_ID_DEALS = 'field_7682'
FIELD_DEAL_ID_DEALS = 'field_7681'

FIELD_COMPANY_ID_INVESTORS = 'field_7593'
FIELD_DEAL_ID_INVESTORS = 'field_8614'

FIELD_LINK_CI = 'field_7729'  # Link field in Deals to Company Investors


# === Fetch all rows (with pagination) ===
def fetch_all_rows(table_id):
    rows = []
    url = f"{BASE_URL}/rows/table/{table_id}/?size=200"
    while url:
        response = requests.get(url, headers=HEADERS)
        data = response.json()
        rows.extend(data['results'])
        url = data.get('next')
    return rows


# === Step 1: Build index of (company_id, deal_id) → [Company Investor row IDs]
print("📥 Fetching Company Investors...")
ci_map = {}
for row in fetch_all_rows(TABLE_COMPANY_INVESTORS):
    company_id = row.get(FIELD_COMPANY_ID_INVESTORS)
    deal_id = row.get(FIELD_DEAL_ID_INVESTORS)
    if company_id and deal_id:
        key = (company_id, deal_id)
        ci_map.setdefault(key, []).append(row['id'])


# === Step 2: Link each Deal to its matching Company Investors ===
print("📥 Fetching Deals...")
for deal_row in fetch_all_rows(TABLE_DEALS):
    deal_row_id = deal_row['id']
    company_id = deal_row.get(FIELD_COMPANY_ID_DEALS)
    deal_id = deal_row.get(FIELD_DEAL_ID_DEALS)
    already_linked = deal_row.get(FIELD_LINK_CI)

    if company_id and deal_id:
        key = (company_id, deal_id)
        if key in ci_map:
            if already_linked:
                print(f"⏭️ Deal {deal_id} already linked to Company Investors")
            else:
                data = {FIELD_LINK_CI: ci_map[key]}
                patch_url = f"{BASE_URL}/rows/table/{TABLE_DEALS}/{deal_row_id}/"
                r = requests.patch(patch_url, headers=HEADERS, json=data)

                if r.status_code == 200:
                    print(f"✅ Linked Deal {deal_id} → {len(ci_map[key])} Company Investors")
                else:
                    print(f"⚠️ Failed to link Deal {deal_id}: {r.status_code} - {r.text}")
        else:
            print(f"❌ No matching Company Investors for company_id={company_id}, deal_id={deal_id}")
    else:
        print(f"❌ Deal row {deal_row_id} missing company_id or deal_id")
