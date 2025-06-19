#!/usr/bin/env python3
"""
WebAgent Phase 2B Validation Test
Tests the complete semantic website understanding flow
"""

import requests
import json
import time
import sys

def main():
    print("🚀 Starting WebAgent Phase 2B Validation Test...")
    
    # Step 1: Authentication
    print("\n1. Authenticating...")
    login_data = {
        "username": "testuser",
        "password": "Test123!"
    }

    try:
        response = requests.post(
            "http://localhost:8000/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()
        token = response.json()["access_token"]
        print("✅ Authentication successful!")
        print(f"Token: {token[:20]}...")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False
    
    # Step 2: Submit webpage parsing request
    print("\n2. Submitting webpage parsing request for https://httpbin.org/html...")
    parse_data = {
        "url": "https://httpbin.org/html",
        "include_screenshot": False,
        "wait_for_load": 2,
        "wait_for_network_idle": True
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/web-pages/parse",
            json=parse_data,
            headers=headers
        )
        response.raise_for_status()
        task_id = response.json()["task_id"]
        print(f"✅ Parse request submitted! Task ID: {task_id}")
    except Exception as e:
        print(f"❌ Parse request failed: {e}")
        return False
    
    # Step 3: Monitor task progress
    print("\n3. Monitoring task progress...")
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        time.sleep(2)
        
        try:
            response = requests.get(
                f"http://localhost:8000/api/v1/web-pages/{task_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            data = response.json()
            
            status = data.get("status", "UNKNOWN")
            progress = data.get("progress_percentage", 0)
            step = data.get("current_step", "unknown")
            
            print(f"   Attempt {attempt}: {status} | {progress}% | {step}")
            
            if status == "completed":
                print("✅ Task completed successfully!")
                break
            elif status == "failed":
                print("❌ Task failed!")
                print(f"Error: {data.get('error_message', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"   Error checking status: {e}")
    
    if attempt >= max_attempts:
        print("⚠️ Task did not complete within timeout")
        print(f"Final status: {status} | {progress}% | {step}")
        return False
    
    # Step 4: Get results
    print("\n4. Retrieving semantic analysis results...")
    
    try:
        response = requests.get(
            f"http://localhost:8000/api/v1/web-pages/{task_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        results = response.json()
        
        print("✅ Results retrieved successfully!")
        print("\n📊 SEMANTIC ANALYSIS SUMMARY:")
        print(f"   URL: {results.get('url', 'N/A')}")
        print(f"   Title: {results.get('title', 'N/A')}")
        print(f"   Domain: {results.get('domain', 'N/A')}")
        print(f"   Interactive Elements: {len(results.get('interactive_elements', []))}")
        print(f"   Content Blocks: {len(results.get('content_blocks', []))}")
        print(f"   Action Capabilities: {len(results.get('action_capabilities', []))}")
        print(f"   Parsing Duration: {results.get('parsing_duration_ms', 0)}ms")
        print(f"   Content Hash: {results.get('content_hash', 'N/A')}")
        
        # Show first few interactive elements
        elements = results.get('interactive_elements', [])
        if elements:
            print("\n🎯 INTERACTIVE ELEMENTS (First 5):")
            for i, element in enumerate(elements[:5]):
                text = element.get('text_content', '')[:50]
                tag = element.get('tag_name', 'unknown')
                print(f"   - {tag}: {text}...")
        
        # Show action capabilities
        capabilities = results.get('action_capabilities', [])
        if capabilities:
            print("\n🧠 ACTION CAPABILITIES:")
            for cap in capabilities:
                action_type = cap.get('action_type', 'unknown')
                description = cap.get('description', 'No description')
                print(f"   - {action_type}: {description}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to retrieve results: {e}")
        return False

if __name__ == "__main__":
    success = main()
    print(f"\n🎉 WebAgent Phase 2B Validation Test {'PASSED' if success else 'FAILED'}!")
    sys.exit(0 if success else 1)
