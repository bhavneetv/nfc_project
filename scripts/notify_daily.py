import os

import requests


api_base = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
user_id = os.getenv("USER_ID", "demo-user")

response = requests.post(
    f"{api_base}/api/notify/daily",
    params={"user_id": user_id},
    timeout=30,
)
print({"status": response.status_code, "body": response.text[:500]})
