import os

import requests


url = os.getenv("PING_URL", "http://localhost:8000/health")
response = requests.get(url, timeout=20)
print({"url": url, "status": response.status_code})
