import json
import urllib.request
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

def run_phase_4_chart_e2e_test():
    print("=== PHASE 4 LIVE ENTERPRISE_TABLE CHART & RLS VALIDATION ===")
    
    # 1. Login Admin
    opener_admin, headers_admin = login('admin', 'admin')
    print("1. Admin Login: SUCCESS")

    # 2. Create actual enterprise_table viz_type chart slice
    chart_payload = {
        "slice_name": "Phase 4 Enterprise Table Advanced Chart",
        "viz_type": "enterprise_table",
        "datasource_id": 28,
        "datasource_type": "table",
        "params": json.dumps({
            "viz_type": "enterprise_table",
            "datasource": "28__table",
            "groupby": ["customer_region"],
            "metrics": [
                {"label": "Total Revenue", "expressionType": "SQL", "sqlExpression": "SUM(sales_amount)"},
                {"label": "Avg Margin", "expressionType": "SQL", "sqlExpression": "AVG(profit_margin)"},
                {"label": "Order Count", "expressionType": "SQL", "sqlExpression": "COUNT(*)"}
            ],
            "row_limit": 100,
            "page_size": 20,
            "include_search": True,
            "enable_column_sort": True,
            "enable_column_resize": True,
            "enable_column_reorder": True,
            "enable_column_pinning": True,
            "enable_column_filters": True,
            "enable_saved_layouts": True,
            "enable_cell_bars": True,
            "enable_value_coloring": True,
            "enable_hyperlinks": True,
            "enable_export_excel": True
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
        print(f"2. Created enterprise_table Chart (Chart ID: {chart_id}, viz_type: 'enterprise_table'): HTTP {resp.status} SUCCESS")

    # 3. Create Regular RLS rule for Subject 7 (Regional_Analyst_Role)
    rls_payload = {
        "name": "Phase 4 Regional Analyst North America RLS",
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
        print(f"3. Created Regular RLS Rule (RLS ID: {rls_id}): HTTP {resp.status} SUCCESS")

    # 4. Query under regional_user via /api/v1/chart/data
    opener_reg, headers_reg = login('regional_user', 'regional_pass123')
    query_payload = {
        "datasource": {"id": 28, "type": "table"},
        "queries": [{
            "columns": ["customer_region"],
            "metrics": [
                {"label": "Total Revenue", "expressionType": "SQL", "sqlExpression": "SUM(sales_amount)"},
                {"label": "Avg Margin", "expressionType": "SQL", "sqlExpression": "AVG(profit_margin)"},
                {"label": "Order Count", "expressionType": "SQL", "sqlExpression": "COUNT(*)"}
            ],
            "row_limit": 100
        }],
        "form_data": {
            "viz_type": "enterprise_table",
            "slice_id": chart_id,
            "datasource": "28__table"
        }
    }

    req_query_reg = urllib.request.Request(
        'http://localhost:8088/api/v1/chart/data',
        data=json.dumps(query_payload).encode('utf-8'),
        headers=headers_reg,
        method='POST'
    )
    with opener_reg.open(req_query_reg) as resp:
        q_res = json.loads(resp.read().decode())
        data_reg = q_res['result'][0]['data']
        regions_reg = [r['customer_region'] for r in data_reg]
        row_count_reg = sum(r.get('Order Count', 0) for r in data_reg)
        print(f"4. Regional User Query Result (RLS Applied):")
        print(f"   HTTP Status: {resp.status}")
        print(f"   Returned Regions: {regions_reg}")
        print(f"   Order Count: {row_count_reg}")
        print(f"   Sample Record: {data_reg[0] if data_reg else None}")
        assert regions_reg == ['North America'], f"Expected only North America, got {regions_reg}"
        assert row_count_reg == 3125, f"Expected 3125 orders, got {row_count_reg}"

    # 5. Cross-Role Query under Admin simultaneously
    req_query_admin = urllib.request.Request(
        'http://localhost:8088/api/v1/chart/data',
        data=json.dumps(query_payload).encode('utf-8'),
        headers=headers_admin,
        method='POST'
    )
    with opener_admin.open(req_query_admin) as resp:
        q_res_admin = json.loads(resp.read().decode())
        data_admin = q_res_admin['result'][0]['data']
        regions_admin = sorted([r['customer_region'] for r in data_admin])
        row_count_admin = sum(r.get('Order Count', 0) for r in data_admin)
        print(f"5. Admin Cross-Role Query Result (Unrestricted):")
        print(f"   HTTP Status: {resp.status}")
        print(f"   Returned Regions: {regions_admin}")
        print(f"   Order Count: {row_count_admin}")
        assert regions_admin == ['APAC', 'EMEA', 'LATAM', 'North America'], f"Unexpected admin regions: {regions_admin}"
        assert row_count_admin == 12500, f"Expected 12500 orders, got {row_count_admin}"

    # 6. Cleanup RLS Rule
    req_del_rls = urllib.request.Request(
        f'http://localhost:8088/api/v1/rowlevelsecurity/{rls_id}',
        headers=headers_admin,
        method='DELETE'
    )
    with opener_admin.open(req_del_rls) as resp:
        print(f"6. Cleaned up RLS Rule (ID: {rls_id}): HTTP {resp.status} SUCCESS")

    print("\nALL PHASE 4 LIVE CHART & RLS SECURITY TESTS PASSED PERFECTLY!\n")

if __name__ == '__main__':
    run_phase_4_chart_e2e_test()
