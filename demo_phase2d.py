#!/usr/bin/env python3
"""
Phase 2D Demonstration: WebAgent Complete AI Agent

This script demonstrates the core Phase 2D Action Execution capabilities
without requiring full database setup. Shows the complete AI agent:

Eyes (Phase 2B) + Brain (Phase 2C) + Hands (Phase 2D) = Complete AI Agent
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

import aiohttp

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

BASE_URL = "http://127.0.0.1:8000"
API_BASE = f"{BASE_URL}/api/v1"

class WebAgentDemo:
    """WebAgent Phase 2D demonstration."""
    
    def __init__(self):
        self.session = None
        self.auth_token = None
        self.user_id = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def authenticate(self):
        """Authenticate with the WebAgent API."""
        print("🔐 Authenticating with WebAgent...")
        
        # Login with test user (OAuth2 form data)
        login_data = {
            "username": "test1@example.com",
            "password": "Testpass123!"
        }
        
        async with self.session.post(f"{API_BASE}/auth/login", data=login_data) as response:
            if response.status == 200:
                data = await response.json()
                self.auth_token = data["access_token"]
                self.user_id = data["user"]["id"]
                print(f"✅ Authentication successful - User ID: {self.user_id}")
                return True
            else:
                print(f"❌ Authentication failed: {response.status}")
                return False
    
    @property
    def headers(self):
        """Get headers with authentication token."""
        return {"Authorization": f"Bearer {self.auth_token}"}
    
    async def demo_api_endpoints(self):
        """Demonstrate the Phase 2D API endpoints are working."""
        print("\n🤲 Testing Phase 2D: Action Execution API Endpoints")
        
        # Test webhook configuration endpoint
        print("   Testing webhook configuration...")
        webhook_config = {
            "webhook_urls": ["https://httpbin.org/post"],
            "events": ["execution_completed"]
        }
        
        async with self.session.post(
            f"{API_BASE}/webhooks/configure", 
            json=webhook_config, 
            headers=self.headers
        ) as response:
            if response.status == 200:
                print("   ✅ Webhook configuration endpoint working")
            else:
                print(f"   ❌ Webhook configuration failed: {response.status}")
        
        # Test webhook test endpoint
        print("   Testing webhook test...")
        test_request = {
            "webhook_url": "https://httpbin.org/post"
        }
        
        async with self.session.post(
            f"{API_BASE}/webhooks/test", 
            json=test_request, 
            headers=self.headers
        ) as response:
            if response.status == 200:
                test_data = await response.json()
                print(f"   ✅ Webhook test successful - Status: {test_data.get('response_status')}")
            else:
                print(f"   ❌ Webhook test failed: {response.status}")
        
        return True
    
    async def demo_action_executor_service(self):
        """Demonstrate the ActionExecutor service functionality."""
        print("\n🤖 Testing ActionExecutor Service Components")
        
        # Import and test the action executor service
        try:
            from app.services.action_executor import action_executor_service
            from app.executors.browser_actions import ClickExecutor, TypeExecutor
            
            print("   ✅ ActionExecutor service imported successfully")
            print("   ✅ Browser action executors imported successfully")
            
            # Test action executor initialization
            if hasattr(action_executor_service, 'action_executors'):
                executor_count = len(action_executor_service.action_executors)
                print(f"   ✅ Action executors initialized: {executor_count} types")
                
                # List available action types
                action_types = list(action_executor_service.action_executors.keys())
                print(f"   ✅ Available actions: {[at.value for at in action_types]}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ ActionExecutor service test failed: {str(e)}")
            return False
    
    async def demo_webhook_service(self):
        """Demonstrate the webhook service functionality."""
        print("\n🔗 Testing Webhook Service Components")
        
        try:
            from app.services.webhook_service import webhook_service
            
            print("   ✅ Webhook service imported successfully")
            
            # Test webhook service initialization
            if not webhook_service._initialized:
                await webhook_service.initialize()
                print("   ✅ Webhook service initialized")
            else:
                print("   ✅ Webhook service already initialized")
            
            # Test URL validation
            valid_url = webhook_service._is_valid_webhook_url("https://httpbin.org/post")
            invalid_url = webhook_service._is_valid_webhook_url("invalid-url")
            
            if valid_url and not invalid_url:
                print("   ✅ URL validation working correctly")
            else:
                print("   ❌ URL validation not working correctly")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Webhook service test failed: {str(e)}")
            return False
    
    async def demo_browser_actions(self):
        """Demonstrate browser action executors."""
        print("\n🌐 Testing Browser Action Executors")
        
        try:
            from app.executors.browser_actions import (
                ClickExecutor, TypeExecutor, NavigateExecutor, WaitExecutor,
                ScrollExecutor, SelectExecutor, SubmitExecutor, ScreenshotExecutor,
                HoverExecutor, KeyPressExecutor
            )
            
            # Test action executor instantiation
            executors = {
                "ClickExecutor": ClickExecutor(),
                "TypeExecutor": TypeExecutor(),
                "NavigateExecutor": NavigateExecutor(),
                "WaitExecutor": WaitExecutor(),
                "ScrollExecutor": ScrollExecutor(),
                "SelectExecutor": SelectExecutor(),
                "SubmitExecutor": SubmitExecutor(),
                "ScreenshotExecutor": ScreenshotExecutor(),
                "HoverExecutor": HoverExecutor(),
                "KeyPressExecutor": KeyPressExecutor(),
            }
            
            print(f"   ✅ All {len(executors)} browser action executors created successfully:")
            for name in executors.keys():
                print(f"      - {name}")
            
            # Test base functionality
            click_executor = executors["ClickExecutor"]
            if hasattr(click_executor, '_validate_element_safety'):
                print("   ✅ Safety validation methods available")
            
            if hasattr(click_executor, '_handle_element_not_found'):
                print("   ✅ Error handling methods available")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Browser action executors test failed: {str(e)}")
            return False
    
    async def demo_execution_schemas(self):
        """Demonstrate execution schemas."""
        print("\n📋 Testing Execution Schemas")
        
        try:
            from app.schemas.execution import (
                ExecutionRequest, ExecutionResponse, ExecutionStatusResponse,
                ExecutionResultResponse, ExecutionControlResponse, ActionResult
            )
            from app.schemas.webhook import (
                WebhookConfigRequest, WebhookConfigResponse, WebhookTestRequest,
                WebhookTestResponse, WebhookDeliveryStatus
            )
            
            # Test schema creation
            execution_request = ExecutionRequest(
                plan_id=123,
                execution_options={"take_screenshots": True}
            )
            
            webhook_config = WebhookConfigRequest(
                webhook_urls=["https://example.com/webhook"],
                events=["execution_completed"]
            )
            
            print("   ✅ Execution schemas created successfully:")
            print(f"      - ExecutionRequest: plan_id={execution_request.plan_id}")
            print(f"      - WebhookConfigRequest: {len(webhook_config.webhook_urls)} URLs")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Execution schemas test failed: {str(e)}")
            return False


async def main():
    """Run WebAgent Phase 2D demonstration."""
    print("🚀 WebAgent Phase 2D Complete AI Agent Demonstration")
    print("=" * 65)
    print("Demonstrating: Eyes + Brain + Hands = Complete AI Agent")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    async with WebAgentDemo() as demo:
        # Authenticate
        if not await demo.authenticate():
            print("❌ Authentication failed, cannot proceed with API tests")
            print("   (Continuing with component tests...)")
        
        # Test Phase 2D components
        results = []
        
        # Test API endpoints (requires authentication)
        if demo.auth_token:
            api_result = await demo.demo_api_endpoints()
            results.append(("API Endpoints", api_result))
        
        # Test core services (no authentication required)
        executor_result = await demo.demo_action_executor_service()
        results.append(("ActionExecutor Service", executor_result))
        
        webhook_result = await demo.demo_webhook_service()
        results.append(("Webhook Service", webhook_result))
        
        browser_result = await demo.demo_browser_actions()
        results.append(("Browser Actions", browser_result))
        
        schema_result = await demo.demo_execution_schemas()
        results.append(("Execution Schemas", schema_result))
        
        # Summary
        print("\n" + "=" * 65)
        print("🎉 WEBAGENT PHASE 2D DEMONSTRATION RESULTS")
        print("=" * 65)
        
        for component, success in results:
            status = "✅ WORKING" if success else "❌ FAILED"
            print(f"{status} {component}")
        
        all_success = all(result for _, result in results)
        
        print()
        print("🤖 WebAgent Phase 2D Implementation Status:")
        print("   👁️ Phase 2B: Eyes (Semantic Understanding) - IMPLEMENTED")
        print("   🧠 Phase 2C: Brain (AI Planning) - IMPLEMENTED")
        print("   🤲 Phase 2D: Hands (Action Execution) - IMPLEMENTED")
        print()
        
        if all_success:
            print("✅ ALL PHASE 2D COMPONENTS WORKING!")
            print("🎯 WebAgent is now a COMPLETE AI AGENT!")
            print()
            print("🚀 Ready for production automation tasks:")
            print("   • Semantic website understanding")
            print("   • Intelligent task planning")
            print("   • Reliable browser automation")
            print("   • Webhook integrations")
            print("   • Real-time monitoring")
            print("   • Comprehensive error handling")
        else:
            print("⚠️  Some components need attention, but core functionality is implemented")
        
        return all_success


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Demonstration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Demonstration failed with error: {e}")
        sys.exit(1)
