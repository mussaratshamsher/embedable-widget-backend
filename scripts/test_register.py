import urllib.request
import json

url = "http://127.0.0.1:8000/api/auth/register"
data = json.dumps({"email": "test123@example.com", "password": "testpass123"}).encode()
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
try:
    resp = urllib.request.urlopen(req)
    print("STATUS:", resp.status)
    print("BODY:", resp.read().decode())
except urllib.error.HTTPError as e:
    print("STATUS:", e.code)
    print("BODY:", e.read().decode())
