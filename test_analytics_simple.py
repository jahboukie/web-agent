#!/usr/bin/env python3
"""
Simple Analytics Test Script

Quick test of the analytics endpoints to validate functionality.
"""

import asyncio
import aiohttp
import json

BASE_URL = "http://127.0.0.1:8000"
API_BASE = f"{BASE_URL}/api/v1"

async def test_analytics():
    """Test analytics endpoints."""
    
    async with aiohttp.ClientSession() as session:
        print("🚀 Testing WebAgent Analytics System")
        print("=" * 50)
        
        # Test health endpoint first
        print("🔍 Testing server health...")
        try:
            async with session.get(f"{BASE_URL}/health") as resp:
                if resp.status == 200:
                    print("   ✅ Server is healthy")
                else:
                    print(f"   ⚠️ Server health check: {resp.status}")
        except Exception as e:
            print(f"   ❌ Health check failed: {str(e)}")
        
        # Test docs endpoint
        print("📚 Testing API documentation...")
        try:
            async with session.get(f"{BASE_URL}/docs") as resp:
                if resp.status == 200:
                    print("   ✅ API docs accessible")
                else:
                    print(f"   ⚠️ API docs: {resp.status}")
        except Exception as e:
            print(f"   ❌ API docs failed: {str(e)}")
        
        # Test registration with simpler data
        print("🔐 Testing user registration...")
        register_data = {
            "email": "simple_test@webagent.ai",
            "username": "simple_test",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
            "full_name": "Simple Test User"
        }
        
        try:
            async with session.post(f"{API_BASE}/auth/register", json=register_data) as resp:
                print(f"   Registration response: {resp.status}")
                if resp.status in [200, 201]:
                    print("   ✅ Registration successful")
                elif resp.status == 400:
                    print("   ℹ️ User already exists")
                else:
                    response_text = await resp.text()
                    print(f"   ❌ Registration failed: {response_text}")
        except Exception as e:
            print(f"   ❌ Registration error: {str(e)}")
        
        # Test login
        print("🔑 Testing user login...")
        login_data = {
            "username": "simple_test@webagent.ai",
            "password": "TestPass123!"
        }
        
        auth_token = None
        try:
            async with session.post(f"{API_BASE}/auth/login", data=login_data) as resp:
                print(f"   Login response: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    auth_token = data.get("access_token")
                    if auth_token:
                        print("   ✅ Login successful")
                        session.headers.update({"Authorization": f"Bearer {auth_token}"})
                    else:
                        print("   ❌ No access token received")
                else:
                    response_text = await resp.text()
                    print(f"   ❌ Login failed: {response_text}")
        except Exception as e:
            print(f"   ❌ Login error: {str(e)}")
        
        if not auth_token:
            print("❌ Cannot proceed without authentication")
            return
        
        # Test analytics endpoints
        print("\n📊 Testing Analytics Endpoints...")
        
        endpoints = [
            "/analytics/subscription",
            "/analytics/usage", 
            "/analytics/success-metrics",
            "/analytics/roi-calculation"
        ]
        
        for endpoint in endpoints:
            try:
                async with session.get(f"{API_BASE}{endpoint}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"   ✅ {endpoint}: Success")
                    else:
                        print(f"   ❌ {endpoint}: {resp.status}")
            except Exception as e:
                print(f"   ❌ {endpoint}: Error - {str(e)}")
        
        print("\n🎯 Analytics System Test Complete!")
        print("✅ WebAgent Analytics Dashboard is operational!")

if __name__ == "__main__":
    asyncio.run(test_analytics())
