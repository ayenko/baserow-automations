import re
import requests

# --- Config ---
API_TOKEN = 'ngYR5EDCeQcu7gSbXmAxHyW5m4NH5wyf'
BASE_URL = 'https://intelligence.sifted.eu'
DEALS_TABLE_ID = 786
COMPANIES_TABLE_ID = 782
ROWS_URL = f'{BASE_URL}/api/database/rows/table/{DEALS_TABLE_ID}/'
FIELDS_URL = f'{BASE_URL}/api/database/fields/table/{DEALS_TABLE_ID}/'

HEADERS = {
    'Authorization': f'Token {API_TOKEN}',
    'Content-Type': 'application/json'
}

# ─── Field Mappings ───────────────────────────────────────────────
FIELD_MAP = {
    'vertical': {'source': 'field_7693', 'target': 'field_7749', 'type': 'multi'},
    'sector':   {'source': 'field_7694', 'target': 'field_7753', 'type': 'multi'},
    'round':    {'source': 'field_7695', 'target': 'field_7751', 'type': 'single'},
    'stage':    {'source': 'field_7696', 'target': 'field_7752', 'type': 'single'},
    # NEW: funding_deployment_tags (string) → Funding Deployment Tags (array)
    'funding_deployment_tags': {'source': 'field_9453', 'target': 'field_9454', 'type': 'multi'},
}

COMPANY_LINK_FIELD = 'field_8615'

# ─── Company Field IDs ─────────────────────────────────────────────
COMPANY_ID_FIELD = 'field_7561'
DEAL_COMPANY_ID_FIELD = 'field_7682'
IS_CURRENT_FIELD = 'field_7591'

# ─── Option Cache ─────────────────────────────────────────────────
valid_options = {}

# ─── Synonym Mapping for Funding Deployment Tags ──────────────────
FD_SYNONYMS = {
    'geographical expansion': 'Geographical expansion',
    'geographic expansion': 'Geographical expansion',
    'market expansion': 'Market expansion',
    'expansion': 'Market expansion',
    'partnership': 'Partnerships',
    'partnerships': 'Partnerships',
    'hiring': 'Hiring',
    'recruitment': 'Hiring',
    'operations & infrastructure': 'Product development & R&D',
    'operations': 'Product development & R&D',
    'infrastructure': 'Product development & R&D',
    'product development': 'Product development & R&D',
    'r&d': 'Product development & R&D',
    'regulatory & compliance': 'Regulatory & compliance',
    'regulatory': 'Regulatory & compliance',
    'compliance': 'Regulatory & compliance',
    'm&a': 'M&A',
    'mergers and acquisitions': 'M&A',
}

# ─── Setup ────────────────────────────────────────────────────────
session = requests.Session()
session.headers.update(HEADERS)

SPLIT_RE = re.compile(r"[,\n;•]|(?:\s{2,})")

def clean_split(val: str):
    parts = [p.strip() for p in SPLIT_RE.split(val or '')]
    return [p for p in parts if p]

def get_field_options():
    resp = session.get(FIELDS_URL)
    resp.raise_for_status()
    data = resp.json()
    for field in data:
        field_id = f"field_{field['id']}"
        if field['type'] in ['multiple_select', 'single_select']:
            options = {opt['value']: opt['id'] for opt in field['select_options']}
            valid_options[field_id] = options

def normalize_funding_deployment_tags(values):
    """
    Normalize labels for funding_deployment_tags (field_9453 → field_9454)
    """
    if not values:
        return []

    option_labels = set(valid_options.get('field_9454', {}).keys())
    normalized = []

    for v in values:
        raw = v.strip()
        if not raw:
            continue
        low = raw.lower()

        # Synonym
        if low in FD_SYNONYMS:
            normalized.append(FD_SYNONYMS[low])
            continue

        # Direct match
        if raw in option_labels:
            normalized.append(raw)
            continue

        # Case-insensitive match
        matched = next((opt for opt in option_labels if opt.lower() == low), None)
        if matched:
            normalized.append(matched)
            continue

    # De-duplicate
    seen, deduped = set(), []
    for item in normalized:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped

def match_option(field_id, values, is_multi=True):
    options = valid_options.get(field_id, {})
    matched = [label for label in values if label in options]
    return matched if is_multi else (matched[0] if matched else None)

def get_all_deal_rows():
    rows = []
    next_url = ROWS_URL
    while next_url:
        resp = session.get(next_url)
        resp.raise_for_status()
        data = resp.json()
        rows.extend(data['results'])
        next_url = data.get('next')
    return rows

def get_companies():
    companies = []
    url = f'{BASE_URL}/api/database/rows/table/{COMPANIES_TABLE_ID}/'
    while url:
        resp = session.get(url)
        resp.raise_for_status()
        data = resp.json()
        companies.extend(data['results'])
        url = data.get('next')
    return companies

def find_matching_company(deal, companies):
    deal_company_id = deal.get(DEAL_COMPANY_ID_FIELD)
    if not deal_company_id:
        return None
    for company in companies:
        if (
            company.get(COMPANY_ID_FIELD) == deal_company_id
            and company.get(IS_CURRENT_FIELD) is True
        ):
            return company['id']
    return None

def update_row(row_id, row, companies):
    payload = {}

    for key, meta in FIELD_MAP.items():
        source = meta['source']
        target = meta['target']
        is_multi = meta['type'] == 'multi'

        raw_val = row.get(source)
        if not raw_val:
            continue

        if is_multi:
            tokens = clean_split(raw_val) if isinstance(raw_val, str) else (raw_val or [])
            if key == 'funding_deployment_tags':
                tokens = normalize_funding_deployment_tags(tokens)
            values = tokens
        else:
            values = [raw_val.strip()] if isinstance(raw_val, str) else [raw_val]

        matched = match_option(target, values, is_multi)
        if matched:
            payload[target] = matched

    # Company match
    company_id = find_matching_company(row, companies)
    if company_id:
        payload[COMPANY_LINK_FIELD] = [company_id]

    if not payload:
        print(f"⚠️ Nothing to update for row {row_id}")
        return

    resp = session.patch(f'{ROWS_URL}{row_id}/', json=payload)
    if resp.status_code == 200:
        print(f'✅ Updated row {row_id}')
    else:
        print(f'❌ Failed to update row {row_id}: {resp.status_code} - {resp.text}')

def main():
    print("🔄 Fetching valid select options...")
    get_field_options()

    print("🔄 Loading company records (table 782)...")
    companies = get_companies()

    print("🔄 Fetching all deal rows...")
    rows = get_all_deal_rows()

    # Process recent rows first
    rows = list(reversed(rows))

    print(f"✅ Starting full sync in DESC order ({len(rows)} rows)...\n")
    for row in rows:
        update_row(row['id'], row, companies)

    print("\n✅ Full sync complete.")

if __name__ == '__main__':
    main()
