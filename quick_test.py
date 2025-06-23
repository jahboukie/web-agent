#!/usr/bin/env python3
"""
Quick test to verify background task execution is working.
"""

import asyncio

import httpx


async def quick_test():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Login
        login_data = {"username": "testuser", "password": "Test123!"}
        response = await client.post(
            "http://localhost:8000/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code != 200:
            print(f"❌ Login failed: {response.status_code}")
            return

        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Start parsing task
        parse_request = {
            "url": "https://httpbin.org/html",
            "include_screenshot": False,
            "wait_for_load": 1,
            "wait_for_network_idle": False,
        }

        response = await client.post(
            "http://localhost:8000/api/v1/web-pages/parse",
            json=parse_request,
            headers=headers,
        )

        if response.status_code != 200:
            print(f"❌ Parse failed: {response.status_code}")
            return

        task_data = response.json()
        task_id = task_data["task_id"]
        print(f"✅ Task created: {task_id}")

        # Check status a few times
        for i in range(10):
            await asyncio.sleep(2)

            response = await client.get(
                f"http://localhost:8000/api/v1/web-pages/{task_id}", headers=headers
            )

            if response.status_code == 200:
                status_data = response.json()
                status = status_data["status"]
                progress = status_data.get("progress_percentage", 0)
                step = status_data.get("current_step", "unknown")

                print(f"   Check {i+1}: {status} | {progress}% | {step}")

                if status in ["completed", "failed"]:
                    break
            else:
                print(f"❌ Status check failed: {response.status_code}")
                break


if __name__ == "__main__":
    asyncio.run(quick_test())
