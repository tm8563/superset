import json
import urllib.request
import http.cookiejar

BASE_URL = "http://localhost:8088"

def login(username, password):
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    login_data = json.dumps({'username': username, 'password': password, 'provider': 'db'}).encode('utf-8')
    login_req = urllib.request.Request(
        f'{BASE_URL}/api/v1/security/login',
        data=login_data,
        headers={'Content-Type': 'application/json'}
    )
    with opener.open(login_req) as resp:
        token = json.loads(resp.read().decode())['access_token']
    
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    csrf_req = urllib.request.Request(f'{BASE_URL}/api/v1/security/csrf_token/', headers=headers)
    with opener.open(csrf_req) as resp:
        csrf_token = json.loads(resp.read().decode())['result']
    headers['X-CSRFToken'] = csrf_token
    return opener, headers

def run_test():
    print("================================================================================")
    print("PHASE 10: MULTI-ROLE RLS CROSS-ROLE PRESET VERIFICATION TEST")
    print("================================================================================")
    print("Test Setup:")
    print("- Dataset ID: 28 (enterprise_table_test_data, 12,500 total rows, 4 regions)")
    print("- Admin User: admin (Role: Admin, Subject ID: 1)")
    print("- Non-Admin User: regional_user (Role: Regional_Analyst_Role, Subject ID: 2)")
    print("- Active RLS Filter: RLS 7 ('customer_region = \\'North America\\'') on Dataset 28")
    print("- Target Dashboard: Dashboard 17 (Tables / Enterprise Table Dashboard)")
    print("--------------------------------------------------------------------------------")
    
    # 1. Admin login
    admin_opener, admin_headers = login('admin', 'admin')
    print("1. Admin Login: SUCCESS")
    
    # 2. Admin creates a Shared Filter Preset selecting all 4 regions
    all_regions = ["APAC", "EMEA", "LATAM", "North America"]
    create_preset_payload = {
        "name": "Global 4-Region Enterprise View (Shared)",
        "description": "Shared executive filter preset selecting all 4 global regions",
        "is_shared": True,
        "filter_config_checksum": "preset_sha256_checksum_all_regions",
        "filter_summary": {
            "Customer Region": "APAC, EMEA, LATAM, North America"
        },
        "data_mask": {
            "NATIVE_FILTER-customer_region": {
                "id": "NATIVE_FILTER-customer_region",
                "filterState": {
                    "value": all_regions
                },
                "extraFormData": {
                    "filters": [
                        {
                            "col": "customer_region",
                            "op": "IN",
                            "val": all_regions
                        }
                    ]
                }
            }
        }
    }
    
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/dashboard/17/filter_preset",
        data=json.dumps(create_preset_payload).encode('utf-8'),
        headers=admin_headers,
        method='POST'
    )
    resp = admin_opener.open(req)
    assert resp.status == 201, f"Expected 201 Created, got {resp.status}"
    preset_response = json.loads(resp.read().decode('utf-8'))
    preset_data = preset_response['result']
    preset_id = preset_data['id']
    print(f"2. Admin Created Shared Filter Preset:")
    print(f"   - Preset ID: {preset_id}")
    print(f"   - Name: '{preset_data['name']}'")
    print(f"   - is_shared: {preset_data['is_shared']}")
    print(f"   - Transported Filter Selection: {preset_data['data_mask']['NATIVE_FILTER-customer_region']['filterState']['value']}")
    print(f"   - HTTP Response: 201 Created")
    
    # 3. Query chart data as Admin with this preset's filter selection
    chart_payload_admin = {
        "datasource": {"id": 28, "type": "table"},
        "queries": [
            {
                "columns": ["customer_region"],
                "metrics": [
                    {"label": "Total Sales", "expressionType": "SQL", "sqlExpression": "SUM(sales_amount)"},
                    {"label": "Order Count", "expressionType": "SQL", "sqlExpression": "COUNT(*)"}
                ],
                "filters": [
                    {
                        "col": "customer_region",
                        "op": "IN",
                        "val": all_regions
                    }
                ],
                "row_limit": 100
            }
        ],
        "result_format": "json",
        "result_type": "full"
    }
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/chart/data",
        data=json.dumps(chart_payload_admin).encode('utf-8'),
        headers=admin_headers,
        method='POST'
    )
    resp = admin_opener.open(req)
    admin_chart_res = json.loads(resp.read().decode('utf-8'))
    admin_data = admin_chart_res['result'][0]['data']
    admin_regions = sorted([row['customer_region'] for row in admin_data])
    admin_total_orders = sum(row['Order Count'] for row in admin_data)
    print(f"\n3. Admin Chart Data Execution (Unrestricted Role):")
    print(f"   - POST /api/v1/chart/data -> HTTP 200 OK")
    print(f"   - Filter Applied from Preset: customer_region IN {all_regions}")
    print(f"   - Returned Regions: {admin_regions}")
    print(f"   - Total Rows / Orders: {admin_total_orders}")
    assert admin_regions == ["APAC", "EMEA", "LATAM", "North America"], f"Admin expected 4 regions, got {admin_regions}"
    assert admin_total_orders == 12500, f"Expected 12,500 rows for admin, got {admin_total_orders}"
    
    # 4. Regional User Login
    reg_opener, reg_headers = login('regional_user', 'regional_pass123')
    print(f"\n4. Regional User Login (regional_user): SUCCESS")
    
    # 5. Regional User reads the Shared Preset
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/dashboard/17/filter_preset/{preset_id}",
        headers=reg_headers,
        method='GET'
    )
    resp = reg_opener.open(req)
    assert resp.status == 200, f"Expected 200 OK, got {resp.status}"
    reg_preset = json.loads(resp.read().decode('utf-8'))['result']
    print(f"5. Regional User Loaded Shared Preset:")
    print(f"   - GET /api/v1/dashboard/17/filter_preset/{preset_id} -> HTTP 200 OK")
    print(f"   - Preset Loaded: '{reg_preset['name']}' (Shared by {reg_preset['created_by']['username']})")
    print(f"   - Transported Filter Selection: {reg_preset['data_mask']['NATIVE_FILTER-customer_region']['filterState']['value']}")
    
    # 6. Regional User executes chart query with the Shared Preset's filter selection (all 4 regions)
    chart_payload_regional = {
        "datasource": {"id": 28, "type": "table"},
        "queries": [
            {
                "columns": ["customer_region"],
                "metrics": [
                    {"label": "Total Sales", "expressionType": "SQL", "sqlExpression": "SUM(sales_amount)"},
                    {"label": "Order Count", "expressionType": "SQL", "sqlExpression": "COUNT(*)"}
                ],
                "filters": [
                    {
                        "col": "customer_region",
                        "op": "IN",
                        "val": reg_preset['data_mask']['NATIVE_FILTER-customer_region']['filterState']['value']
                    }
                ],
                "row_limit": 100
            }
        ],
        "result_format": "json",
        "result_type": "full"
    }
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/chart/data",
        data=json.dumps(chart_payload_regional).encode('utf-8'),
        headers=reg_headers,
        method='POST'
    )
    resp = reg_opener.open(req)
    reg_chart_res = json.loads(resp.read().decode('utf-8'))
    reg_data = reg_chart_res['result'][0]['data']
    reg_regions = [row['customer_region'] for row in reg_data]
    reg_total_orders = sum(row['Order Count'] for row in reg_data)
    
    print(f"\n6. Regional User Chart Data Execution (RLS-Restricted Role):")
    print(f"   - POST /api/v1/chart/data with Preset Filters -> HTTP 200 OK")
    print(f"   - Filter Applied from Preset: customer_region IN {reg_preset['data_mask']['NATIVE_FILTER-customer_region']['filterState']['value']}")
    print(f"   - Returned Regions: {reg_regions}")
    print(f"   - Total Rows / Orders: {reg_total_orders}")
    print(f"   - Data Leakage Check: 0 rows leaked from APAC, EMEA, or LATAM")
    print(f"   - Strict RLS Enforcement: Confirmed (100% scoped to 'North America')")
    
    assert reg_regions == ["North America"], f"Expected ['North America'] only under RLS, got {reg_regions}"
    assert reg_total_orders == 3125, f"Expected 3,125 rows for regional_user under RLS, got {reg_total_orders}"
    
    # 7. Cleanup preset
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/dashboard/17/filter_preset/{preset_id}",
        headers=admin_headers,
        method='DELETE'
    )
    resp = admin_opener.open(req)
    assert resp.status == 200, f"Expected 200 OK on cleanup, got {resp.status}"
    print(f"\n7. Cleanup Verification:")
    print(f"   - DELETE /api/v1/dashboard/17/filter_preset/{preset_id} -> HTTP 200 OK")
    print("================================================================================")
    print("RESULT: CROSS-ROLE RLS TEST FOR SHARED PRESETS PASSED WITH ZERO LEAKAGE")
    print("================================================================================")

if __name__ == "__main__":
    run_test()
