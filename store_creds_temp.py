import os, requests
session = os.environ.get('CODEMEMORY_SESSION')
csrf = os.environ.get('CODEMEMORY_CSRF')
resp = requests.post('http://127.0.0.1:8001/api/v1/leetcode/auth/store', json={'session': session, 'csrf_token': csrf})
result = resp.json()
print(f'Status: {resp.status_code}')
print(f'Credentials stored: {result.get("credentialsStored")}')
