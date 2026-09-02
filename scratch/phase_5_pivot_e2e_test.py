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

def run_phase_5_pivot_validation():
    print("=================================================================")
    print("PHASE 5: INTERACTIVE PIVOT TABLE & DATABASE-SIDE ROLLUP EVALUATION")
    print("=================================================================")

    # 1. Admin login
    opener_admin, headers_admin = login('admin', 'admin')
    print("1. Admin Login: SUCCESS")

    # 2. Create Pivot Table V2 Chart Slice
    chart_payload = {
        "slice_name": "Phase 5 Pivot Table V2 Live Evaluation",
        "viz_type": "pivot_table_v2",
        "datasource_id": 28,
        "datasource_type": "table",
        "params": json.dumps({
            "viz_type": "pivot_table_v2",
            "datasource": "28__table",
            "groupbyRows": ["customer_region", "department_code"],
            "groupbyColumns": ["product_category"],
            "metrics": [
                {"label": "Total Revenue", "expressionType": "SQL", "sqlExpression": "SUM(sales_amount)"},
                {"label": "Avg Margin", "expressionType": "SQL", "sqlExpression": "AVG(profit_margin)"}
            ],
            "rowTotals": True,
            "rowSubTotals": True,
            "colTotals": True,
            "colSubTotals": True,
            "rowSubtotalPosition": False,
            "colSubtotalPosition": False,
            "transposePivot": False,
            "combineMetric": False,
            "valueFormat": "SMART_NUMBER"
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
        print(f"2. Created Pivot Table V2 Chart Slice (ID: {chart_id}, viz_type: 'pivot_table_v2'): HTTP {resp.status} SUCCESS")

    # 3. Test Additive Full-Detail Query (SUM + COUNT)
    additive_payload = {
        "datasource": {"id": 28, "type": "table"},
        "queries": [{
            "columns": ["customer_region", "department_code", "product_category"],
            "metrics": [
                {"label": "Total Revenue", "expressionType": "SQL", "sqlExpression": "SUM(sales_amount)"},
                {"label": "Order Count", "expressionType": "SQL", "sqlExpression": "COUNT(*)"}
            ],
            "row_limit": 1000
        }]
    }
    req_add = urllib.request.Request(
        'http://localhost:8088/api/v1/chart/data',
        data=json.dumps(additive_payload).encode('utf-8'),
        headers=headers_admin,
        method='POST'
    )
    with opener_admin.open(req_add) as resp:
        add_res = json.loads(resp.read().decode())
        leaf_rows = add_res['result'][0]['data']
        sql_query = add_res['result'][0]['query']
        print(f"3. Additive Metric Pivot Query: HTTP {resp.status} SUCCESS")
        print(f"   - Detail Leaf Groups: {len(leaf_rows)}")
        print(f"   - Sample Leaf Group: {leaf_rows[0]}")
        print(f"   - Generated SQL Sample:\n     {sql_query.strip()[:200]}...")

    # 4. Test Database-Side Rollup Query with GROUPING SETS (Non-Additive AVG/COUNT_DISTINCT)
    grouping_sets = [
        # Full leaf level
        ["customer_region", "department_code", "product_category"],
        # Subtotal level 1: region + category (collapsed department)
        ["customer_region", "product_category"],
        # Subtotal level 2: region + department (collapsed category)
        ["customer_region", "department_code"],
        # Row total: region alone
        ["customer_region"],
        # Column total: category alone
        ["product_category"],
        # Grand total
        []
    ]
    grouping_payload = {
        "datasource": {"id": 28, "type": "table"},
        "queries": [{
            "columns": ["customer_region", "department_code", "product_category"],
            "grouping_sets": grouping_sets,
            "metrics": [
                {"label": "Avg Margin", "expressionType": "SQL", "sqlExpression": "AVG(profit_margin)"},
                {"label": "Distinct Transactions", "expressionType": "SQL", "sqlExpression": "COUNT(DISTINCT transaction_id)"}
            ],
            "row_limit": 5000
        }]
    }
    req_grp = urllib.request.Request(
        'http://localhost:8088/api/v1/chart/data',
        data=json.dumps(grouping_payload).encode('utf-8'),
        headers=headers_admin,
        method='POST'
    )
    with opener_admin.open(req_grp) as resp:
        grp_res = json.loads(resp.read().decode())
        grp_rows = grp_res['result'][0]['data']
        grp_sql = grp_res['result'][0]['query']
        print(f"4. DB-Side Rollup (GROUPING SETS) Query: HTTP {resp.status} SUCCESS")
        print(f"   - Total Rollup Rows (Leaf + Subtotals + Grand Total): {len(grp_rows)}")
        print(f"   - Executed SQL containing 'GROUPING SETS': {'GROUPING SETS' in grp_sql}")
        print(f"   - Generated SQL Snippet:\n     {grp_sql.strip()[:300]}...")

    # 5. Row-Level Security (RLS) Multi-Role Pivot Verification
    # Create RLS rule for Regional Analyst Role (Subject ID 7)
    rls_payload = {
        "name": "Phase 5 Regional Analyst Pivot RLS",
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
        rls_id = json.loads(resp.read().decode())['id']
        print(f"5. Created Regular RLS Rule (ID: {rls_id}): HTTP {resp.status} SUCCESS")

    # Query under regional_user (Subject 7)
    opener_reg, headers_reg = login('regional_user', 'regional_pass123')
    req_reg = urllib.request.Request(
        'http://localhost:8088/api/v1/chart/data',
        data=json.dumps(grouping_payload).encode('utf-8'),
        headers=headers_reg,
        method='POST'
    )
    with opener_reg.open(req_reg) as resp:
        reg_res = json.loads(resp.read().decode())
        reg_rows = reg_res['result'][0]['data']
        reg_regions = set(r.get('customer_region') for r in reg_rows if r.get('customer_region') is not None)
        print(f"6. Regional User Pivot Query with RLS: HTTP {resp.status} SUCCESS")
        print(f"   - Returned Distinct Non-Null Regions: {reg_regions}")
        print(f"   - Rows Returned: {len(reg_rows)}")
        assert reg_regions == {'North America'}, f"RLS LEAKAGE DETECTED! Found: {reg_regions}"
        print("   - RLS Boundary Check: STRICTLY ISOLATED TO 'North America' (0 rows leaked)")

    # Cleanup RLS Rule
    req_del_rls = urllib.request.Request(
        f'http://localhost:8088/api/v1/rowlevelsecurity/{rls_id}',
        headers=headers_admin,
        method='DELETE'
    )
    with opener_admin.open(req_del_rls) as resp:
        print(f"7. Deleted RLS Rule (ID: {rls_id}): HTTP {resp.status} SUCCESS")

    print("\n=================================================================")
    print("PHASE 5 LIVE DATABASE-SIDE ROLLUP VALIDATION COMPLETED SUCCESSFULLY")
    print("=================================================================")

if __name__ == '__main__':
    run_phase_5_pivot_validation()
