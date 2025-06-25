#!/usr/bin/env python3
"""
Phase 2B Validation Test - Immediate validation of WebAgent's semantic understanding capabilities.

This script validates Claude Sonnet 4's requested test flow:
1. Parse Vercel.com with background task processing
2. Monitor real-time status updates
3. Retrieve semantic analysis results
"""

import asyncio
import time

import httpx

BASE_URL = "http://localhost:8000"


async def validate_phase2b():
    """Complete Phase 2B validation test."""

    print("🚀 PHASE 2B VALIDATION TEST")
    print("=" * 50)

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: Login to get token
        print("\n🔐 Step 1: Authentication")
        login_data = {"username": "testuser", "password": "Test123!"}

        response = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code != 200:
            print(f"❌ Login failed: {response.status_code}")
            return False

        token_data = response.json()
        token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        print(f"✅ Token acquired: {token[:20]}...")

        # Step 2: Parse Vercel.com (Claude's requested test)
        print("\n🌐 Step 2: Parse Vercel.com")
        parse_request = {
            "url": "https://vercel.com",
            "include_screenshot": True,
            "wait_for_load": 2,
            "wait_for_network_idle": True,
        }

        response = await client.post(
            f"{BASE_URL}/api/v1/web-pages/parse", json=parse_request, headers=headers
        )

        if response.status_code != 200:
            print(f"❌ Parse request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False

        parse_data = response.json()
        task_id = parse_data["task_id"]

        print("✅ Parse task created!")
        print(f"   Task ID: {task_id}")
        print(f"   Status: {parse_data['status']}")
        print(f"   Estimated duration: {parse_data['estimated_duration_seconds']}s")
        print(f"   Check status URL: {parse_data['check_status_url']}")

        # Step 3: Monitor real-time status
        print("\n📊 Step 3: Real-time Status Monitoring")
        print("Monitoring task progress...")

        max_wait = 120  # 2 minutes
        start_time = time.time()

        while time.time() - start_time < max_wait:
            response = await client.get(
                f"{BASE_URL}/api/v1/web-pages/{task_id}", headers=headers
            )

            if response.status_code != 200:
                print(f"❌ Status check failed: {response.status_code}")
                break

            status_data = response.json()
            status = status_data["status"]
            progress = status_data.get("progress_percentage", 0)
            current_step = status_data.get("current_step", "unknown")

            print(f"   Status: {status} | Progress: {progress}% | Step: {current_step}")

            if status == "completed":
                print("✅ Task completed successfully!")

                # Step 4: Get semantic analysis results
                print("\n🧠 Step 4: Semantic Analysis Results")

                response = await client.get(
                    f"{BASE_URL}/api/v1/web-pages/{task_id}/results", headers=headers
                )

                if response.status_code == 200:
                    results = response.json()

                    print("✅ Semantic analysis results retrieved!")
                    print("📋 Results Summary:")
                    print(f"   URL: {results.get('url', 'N/A')}")
                    print(f"   Title: {results.get('title', 'N/A')}")
                    print(f"   Domain: {results.get('domain', 'N/A')}")
                    print(
                        f"   Interactive Elements: {len(results.get('interactive_elements', []))}"
                    )
                    print(
                        f"   Content Blocks: {len(results.get('content_blocks', []))}"
                    )
                    print(
                        f"   Action Capabilities: {len(results.get('action_capabilities', []))}"
                    )
                    print(
                        f"   Screenshot: {'Yes' if results.get('screenshot_path') else 'No'}"
                    )
                    print(f"   Content Hash: {results.get('content_hash', 'N/A')}")
                    print(f"   Cached: {results.get('cached', False)}")

                    # Show sample interactive elements
                    elements = results.get("interactive_elements", [])
                    if elements:
                        print("\n🎯 Sample Interactive Elements:")
                        for i, element in enumerate(elements[:3]):  # Show first 3
                            print(
                                f"   {i + 1}. {element.get('tag_name', 'unknown')} - {element.get('semantic_role', 'unknown')}"
                            )
                            print(
                                f"      Text: {element.get('text_content', '')[:50]}..."
                            )
                            print(
                                f"      Confidence: {element.get('interaction_confidence', 0):.2f}"
                            )

                    # Show action capabilities
                    capabilities = results.get("action_capabilities", [])
                    if capabilities:
                        print("\n⚡ Action Capabilities:")
                        for cap in capabilities:
                            print(
                                f"   • {cap.get('action_name', 'unknown')}: {cap.get('description', 'N/A')}"
                            )
                            print(
                                f"     Feasibility: {cap.get('feasibility_score', 0):.2f}"
                            )

                    print("\n🎉 PHASE 2B VALIDATION SUCCESSFUL!")
                    print("✅ WebAgent now has semantic 'eyes' to understand websites!")
                    return True
                else:
                    print(f"❌ Failed to get results: {response.status_code}")
                    return False

            elif status == "failed":
                error_msg = status_data.get("error_message", "Unknown error")
                print(f"❌ Task failed: {error_msg}")
                return False

            # Wait before next check
            await asyncio.sleep(3)

        print("⏰ Task monitoring timeout")
        return False


if __name__ == "__main__":
    success = asyncio.run(validate_phase2b())
    if success:
        print("\n🎯 VALIDATION RESULT: SUCCESS! Phase 2B is fully operational!")
    else:
        print("\n❌ VALIDATION RESULT: Issues detected. Check logs for details.")
