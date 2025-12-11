import requests
import os

key = "sk_f3034b733a8119a19a9d58555b957df4"
base = "https://api.inceptionlabs.ai/v1"

print(f"Testing key: {key}")
try:
    resp = requests.post(
        f"{base}/chat/completions",
        json={
            "model": "mercury",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 10
        },
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        },
        timeout=10
    )
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
