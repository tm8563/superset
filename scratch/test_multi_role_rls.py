import json
import urllib.request
import http.cookiejar

def login(username, password):
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    login_data = json.dumps({'username': username, 'password': password, 'provider': 'db'}).encode('utf-8')
    login_req = urllib.request.Request('http://localhost:8088/api/v1/security/login', data=login_data, headers={'Content-Type': 'application/json'})
    with opener.open(login_req) as resp:
        token = json.loads(resp.read().decode())['access_token']
    
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    csrf_req = urllib.request.Request('http://localhost:8088/api/v1/security/csrf_token/', headers=headers)
    with opener.open(csrf_req) as resp:
        csrf_token = json.loads(resp.read().decode())['result']
    headers['X-CSRFToken'] = csrf_token
    return opener, headers

def run_query(opener, headers, dataset_id=28):
    q_payload = {
        'datasource': {'id': dataset_id, 'type': 'table'},
        'queries': [{
            'columns': ['customer_region'],
            'metrics': [{'label': 'count', 'expressionType': 'SQL', 'sqlExpression': 'COUNT(*)'}],
            'row_limit': 100
        }]
    }
    req = urllib.request.Request(
        'http://localhost:8088/api/v1/chart/data',
        data=json.dumps(q_payload).encode('utf-8'),
        headers=headers,
        method='POST'
    )
    with opener.open(req) as resp:
        res = json.loads(resp.read().decode())
        data = res['result'][0]['data']
        regions = sorted(list(set(r['customer_region'] for r in data if 'customer_region' in r)))
        total_rows = sum(r.get('count', 0) for r in data)
        return regions, total_rows

print("Multi-Role RLS Test Helper Loaded")
