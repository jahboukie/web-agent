#!/usr/bin/env python3

import requests

# Test authentication
print("Testing authentication...")

login_data = {"username": "testuser", "password": "Test123!"}

try:
    response = requests.post(
        "http://localhost:8000/api/v1/auth/login",
        data=login_data,  # Use data instead of json
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")

    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"Success! Token: {token[:20]}...")
    else:
        print("Authentication failed")

except Exception as e:
    print(f"Error: {e}")
