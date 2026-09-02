import json
import urllib.request
import urllib.error
import http.cookiejar

def login(username, password):
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    login_data = json.dumps({'username': username, 'password': password, 'provider': 'db'}).encode('utf-8')
    login_req = urllib.request.Request(
        'http://localhost:8088/api/v1/security/login',
        data=login_data,
        headers={'Content-Type': 'application/json'}
    )
    with opener.open(login_req) as resp:
        token = json.loads(resp.read().decode())['access_token']
    
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    csrf_req = urllib.request.Request('http://localhost:8088/api/v1/security/csrf_token/', headers=headers)
    with opener.open(csrf_req) as resp:
        csrf_token = json.loads(resp.read().decode())['result']
    headers['X-CSRFToken'] = csrf_token
    return opener, headers

def run_phase_6_handlebars_validation():
    print("=================================================================")
    print("PHASE 6: SAFE TEMPLATE CHART (HANDLEBARS) & RLS VALIDATION")
    print("=================================================================")

    # 1. Admin login
    opener_admin, headers_admin = login('admin', 'admin')
    print("1. Admin Login: SUCCESS")

    # 2. Create Handlebars Chart Slice
    handlebars_template = """
<div class="kpi-dashboard">
  {{#each data}}
    <div class="metric-card">
      <span class="region-badge">{{customer_region}}</span>
      <h4 class="dept-title">{{department_code}}</h4>
      <div class="metric-value">${{formatNumber total_revenue}}</div>
      <div class="metric-sub">Avg Margin: {{formatNumber avg_margin}}% | Txns: {{formatNumber txn_count}}</div>
    </div>
  {{/each}}
</div>
""".strip()

    style_template = """
.kpi-dashboard { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; font-family: Inter, sans-serif; }
.metric-card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.region-badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; background: #e0f2fe; color: #0369a1; text-transform: uppercase; }
.dept-title { font-size: 16px; font-weight: 600; margin: 8px 0 4px 0; color: #1e293b; }
.metric-value { font-size: 22px; font-weight: 700; color: #0f172a; margin-bottom: 4px; }
.metric-sub { font-size: 12px; color: #64748b; }
""".strip()

    chart_payload = {
        "slice_name": "Phase 6 Safe Template Handlebars KPI Cards",
        "viz_type": "handlebars",
        "datasource_id": 28,
        "datasource_type": "table",
        "params": json.dumps({
            "viz_type": "handlebars",
            "datasource": "28__table",
            "groupby": ["customer_region", "department_code"],
            "metrics": [
                {"label": "total_revenue", "expressionType": "SQL", "sqlExpression": "SUM(sales_amount)"},
                {"label": "avg_margin", "expressionType": "SQL", "sqlExpression": "AVG(profit_margin)"},
                {"label": "txn_count", "expressionType": "SQL", "sqlExpression": "COUNT(*)"}
            ],
            "handlebars_template": handlebars_template,
            "style_template": style_template,
            "row_limit": 500
        })
    }

    req_create = urllib.request.Request(
        'http://localhost:8088/api/v1/chart/',
        data=json.dumps(chart_payload).encode('utf-8'),
        headers=headers_admin,
        method='POST'
    )
    with opener_admin.open(req_create) as resp:
        create_res = json.loads(resp.read().decode())
        chart_id = create_res['id']
        print(f"2. Created Handlebars Chart Slice (ID: {chart_id}, viz_type: 'handlebars'): HTTP {resp.status} SUCCESS")

    # 3. Query Dataset via Chart Data API as Admin (Unrestricted Dataset)
    admin_query_payload = {
        "datasource": {"id": 28, "type": "table"},
        "queries": [{
            "columns": ["customer_region", "department_code"],
            "metrics": [
                {"label": "total_revenue", "expressionType": "SQL", "sqlExpression": "SUM(sales_amount)"},
                {"label": "avg_margin", "expressionType": "SQL", "sqlExpression": "AVG(profit_margin)"},
                {"label": "txn_count", "expressionType": "SQL", "sqlExpression": "COUNT(*)"}
            ],
            "orderby": [["total_revenue", False]],
            "row_limit": 500
        }]
    }

    req_admin_data = urllib.request.Request(
        'http://localhost:8088/api/v1/chart/data',
        data=json.dumps(admin_query_payload).encode('utf-8'),
        headers=headers_admin,
        method='POST'
    )
    with opener_admin.open(req_admin_data) as resp:
        admin_data_res = json.loads(resp.read().decode())
        admin_rows = admin_data_res['result'][0]['data']
        admin_sql = admin_data_res['result'][0]['query']
        total_admin_txns = sum(r['txn_count'] for r in admin_rows)
        total_admin_revenue = sum(r['total_revenue'] for r in admin_rows)
        admin_regions = sorted(list(set(r['customer_region'] for r in admin_rows)))
        print(f"3. Admin Query Results:")
        print(f"   - Grouped Card Rows: {len(admin_rows)}")
        print(f"   - Distinct Regions Present: {admin_regions}")
        print(f"   - Total Aggregated Transactions: {total_admin_txns:,}")
        print(f"   - Total Aggregated Revenue: ${total_admin_revenue:,.2f}")
        print(f"   - Sample Card Record: {admin_rows[0]}")
        print(f"   - SQL Query Snippet:\n     {admin_sql.strip()[:200]}...")

    # 4. Create RLS Rule for Subject 7 (Regional_Analyst_Role)
    rls_payload = {
        "name": "Phase 6 Regional Analyst Handlebars RLS",
        "filter_type": "Regular",
        "clause": "customer_region = 'North America'",
        "tables": [28],
        "subjects": [7]
    }
    req_rls = urllib.request.Request(
        'http://localhost:8088/api/v1/rowlevelsecurity/',
        data=json.dumps(rls_payload).encode('utf-8'),
        headers=headers_admin,
        method='POST'
    )
    with opener_admin.open(req_rls) as resp:
        rls_res = json.loads(resp.read().decode())
        rls_id = rls_res['id']
        print(f"4. Created Regular RLS Rule (ID: {rls_id}): HTTP {resp.status} SUCCESS")

    # 5. Query Dataset via Chart Data API as Regional User (RLS Restricted: 'North America')
    opener_reg, headers_reg = login('regional_user', 'regional_pass123')
    print("5. Regional User Login: SUCCESS")

    req_reg_data = urllib.request.Request(
        'http://localhost:8088/api/v1/chart/data',
        data=json.dumps(admin_query_payload).encode('utf-8'),
        headers=headers_reg,
        method='POST'
    )
    with opener_reg.open(req_reg_data) as resp:
        reg_data_res = json.loads(resp.read().decode())
        reg_rows = reg_data_res['result'][0]['data']
        reg_sql = reg_data_res['result'][0]['query']
        total_reg_txns = sum(r['txn_count'] for r in reg_rows)
        total_reg_revenue = sum(r['total_revenue'] for r in reg_rows)
        reg_regions = sorted(list(set(r['customer_region'] for r in reg_rows)))
        print(f"6. Regional User Query Results (RLS Enforced):")
        print(f"   - Grouped Card Rows: {len(reg_rows)}")
        print(f"   - Distinct Regions Present: {reg_regions}")
        print(f"   - Total Aggregated Transactions: {total_reg_txns:,}")
        print(f"   - Total Aggregated Revenue: ${total_reg_revenue:,.2f}")
        print(f"   - Non-North-America Rows Leaked: {sum(1 for r in reg_rows if r['customer_region'] != 'North America')}")
        print(f"   - SQL WHERE Clause Contains RLS: {'customer_region = ' in reg_sql}")
        print(f"   - SQL Snippet:\n     {reg_sql.strip()[:250]}...")

    # 7. Cleanup RLS Rule
    req_del_rls = urllib.request.Request(
        f'http://localhost:8088/api/v1/rowlevelsecurity/{rls_id}',
        headers=headers_admin,
        method='DELETE'
    )
    with opener_admin.open(req_del_rls) as resp:
        print(f"7. Deleted RLS Rule (ID: {rls_id}): HTTP {resp.status} SUCCESS")

    # 8. Verify Exact Non-Round Counts & Metrics
    print("\n--- Non-Round RLS Verification Checks ---")
    assert len(admin_rows) == 120, f"Expected 120 department-region groups in Admin, got {len(admin_rows)}"
    assert len(reg_rows) == 30, f"Expected 30 department groups in North America for Regional User, got {len(reg_rows)}"
    assert total_admin_txns == 12500, f"Expected 12,500 total txns in Admin, got {total_admin_txns}"
    assert total_reg_txns == 3125, f"Expected 3,125 txns in North America, got {total_reg_txns}"
    assert reg_regions == ['North America'], f"Expected only North America, got {reg_regions}"
    assert round(total_admin_revenue, 2) == 167236831.75, f"Expected $167,236,831.75 in Admin revenue, got {total_admin_revenue}"
    assert round(total_reg_revenue, 2) == 41199313.50, f"Expected $41,199,313.50 in Regional revenue, got {total_reg_revenue}"
    print("ALL RLS SECURITY & METRIC ASSERTIONS PASSED PERFECTLY!")

    return chart_id

if __name__ == '__main__':
    run_phase_6_handlebars_validation()
