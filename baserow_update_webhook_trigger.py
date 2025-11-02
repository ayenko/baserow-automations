import requests

# --- Config ---
API_TOKEN = 'ngYR5EDCeQcu7gSbXmAxHyW5m4NH5wyf'
BASE_URL = 'https://intelligence.sifted.eu'
TABLE_ID = 786
ROWS_URL = f'{BASE_URL}/api/database/rows/table/{TABLE_ID}/'
HEADERS = {
    'Authorization': f'Token {API_TOKEN}',
    'Content-Type': 'application/json'
}

# --- Field IDs ---
ROUND_TYPE_FIELD = 'field_7677'
DEAL_TYPE_FIELD = 'field_7676'
WEBHOOK_TRIGGER_FIELD = 'field_9448'

# --- Setup ---
session = requests.Session()
session.headers.update(HEADERS)

def get_all_rows():
    rows = []
    next_url = ROWS_URL
    while next_url:
        resp = session.get(next_url)
        data = resp.json()
        rows.extend(data['results'])
        next_url = data.get('next')
    return rows

def should_update_webhook(row):
    # Only update if trigger is None or False
    current_value = row.get(WEBHOOK_TRIGGER_FIELD)
    if current_value is True:
        return False  # already set

    round_type = row.get(ROUND_TYPE_FIELD)
    deal_type = row.get(DEAL_TYPE_FIELD)

    return round_type != "Undisclosed" and deal_type != "M&A"

def update_webhook_field(row_id):
    payload = {WEBHOOK_TRIGGER_FIELD: True}
    resp = session.patch(f'{ROWS_URL}{row_id}/', json=payload)
    if resp.status_code == 200:
        print(f"✅ Updated row {row_id} → Webhook trigger = True")
    else:
        print(f"❌ Failed to update row {row_id}: {resp.status_code} - {resp.text}")

def main():
    print("🔄 Fetching rows...")
    rows = get_all_rows()

    print(f"🔍 Checking {len(rows)} rows for webhook updates...")
    for row in rows:
        if should_update_webhook(row):
            update_webhook_field(row['id'])

    print("✅ Webhook trigger update complete.")

if __name__ == '__main__':
    main()
