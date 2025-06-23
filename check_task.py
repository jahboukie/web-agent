#!/usr/bin/env python3
"""
Quick script to check task status.
"""

import requests


def check_task_status(task_id):
    """Check the status of a specific task."""

    # First authenticate
    auth_response = requests.post(
        "http://localhost:8000/api/v1/auth/login",
        data={"username": "testuser", "password": "testpass123"},
    )

    if auth_response.status_code != 200:
        print(f"❌ Authentication failed: {auth_response.status_code}")
        return

    token = auth_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Check task status
    task_response = requests.get(
        f"http://localhost:8000/api/v1/web-pages/{task_id}", headers=headers
    )

    if task_response.status_code != 200:
        print(f"❌ Failed to get task status: {task_response.status_code}")
        return

    task_data = task_response.json()
    print(f"📊 Task {task_id} Status:")
    print(f"   Status: {task_data.get('status')}")
    print(f"   Progress: {task_data.get('progress_percentage', 0)}%")
    print(f"   Current Step: {task_data.get('current_step')}")
    print(f"   Error: {task_data.get('error_message')}")

    if task_data.get("result_data"):
        print("   Has Result Data: Yes")
    else:
        print("   Has Result Data: No")


if __name__ == "__main__":
    # Check the latest tasks
    for task_id in [22, 23]:
        check_task_status(task_id)
        print()
