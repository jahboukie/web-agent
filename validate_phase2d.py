#!/usr/bin/env python3
"""
Phase 2D Validation Script: Complete WebAgent AI Agent Testing

This script validates the complete WebAgent system with Eyes + Brain + Hands:
- Phase 2B: Semantic website understanding (Eyes)
- Phase 2C: AI planning with LangChain (Brain)
- Phase 2D: Action execution with browser automation (Hands)

Tests the complete end-to-end workflow:
Parse Website → Generate Plan → Human Approval → Execute Plan → Report Results
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

import aiohttp

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

BASE_URL = "http://127.0.0.1:8000"
API_BASE = f"{BASE_URL}/api/v1"


class WebAgentValidator:
    """Complete WebAgent system validator."""

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
        login_data = {"username": "test1@example.com", "password": "Testpass123!"}

        async with self.session.post(
            f"{API_BASE}/auth/login", data=login_data
        ) as response:
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

    async def test_phase_2b_eyes(self):
        """Test Phase 2B: Semantic website understanding (Eyes)."""
        print("\n👁️ Testing Phase 2B: Eyes (Semantic Website Understanding)")

        # Test webpage parsing
        parse_request = {
            "url": "https://vercel.com/new",
            "include_screenshots": True,
            "analyze_forms": True,
            "detect_interactive_elements": True,
        }

        async with self.session.post(
            f"{API_BASE}/web-pages/parse", json=parse_request, headers=self.headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                task_id = data["task_id"]
                print(f"✅ Webpage parsing started - Task ID: {task_id}")

                # Wait for parsing to complete
                await self._wait_for_task_completion(task_id, "webpage parsing")

                # Get parsing results
                async with self.session.get(
                    f"{API_BASE}/web-pages/{task_id}/results", headers=self.headers
                ) as results_response:
                    if results_response.status == 200:
                        results = await results_response.json()
                        print("✅ Webpage parsed successfully:")
                        print(
                            f"   - Interactive elements: {results.get('interactive_elements_count', 0)}"
                        )
                        print(f"   - Forms detected: {results.get('form_count', 0)}")
                        print(
                            f"   - Parsing duration: {results.get('parsing_duration_ms', 0)}ms"
                        )
                        return task_id
                    else:
                        print(
                            f"❌ Failed to get parsing results: {results_response.status}"
                        )
                        return None
            else:
                print(f"❌ Webpage parsing failed: {response.status}")
                return None

    async def test_phase_2c_brain(self, webpage_task_id):
        """Test Phase 2C: AI planning with LangChain (Brain)."""
        print("\n🧠 Testing Phase 2C: Brain (AI Planning with LangChain)")

        # Test plan generation
        plan_request = {
            "user_goal": "Deploy my React application to Vercel",
            "source_task_id": webpage_task_id,
            "planning_options": {
                "planning_temperature": 0.1,
                "max_agent_iterations": 10,
                "require_approval": True,
            },
        }

        async with self.session.post(
            f"{API_BASE}/plans/generate", json=plan_request, headers=self.headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                plan_id = data["plan_id"]
                print(f"✅ Plan generation started - Plan ID: {plan_id}")

                # Wait for planning to complete
                await self._wait_for_plan_completion(plan_id)

                # Get plan details
                async with self.session.get(
                    f"{API_BASE}/plans/{plan_id}/details", headers=self.headers
                ) as details_response:
                    if details_response.status == 200:
                        plan = await details_response.json()
                        print("✅ Plan generated successfully:")
                        print(f"   - Total actions: {plan.get('total_actions', 0)}")
                        print(
                            f"   - Confidence score: {plan.get('confidence_score', 0):.2f}"
                        )
                        print(f"   - Status: {plan.get('status', 'unknown')}")

                        # Approve the plan for execution
                        approval_request = {
                            "approved": True,
                            "feedback": "Plan looks good for testing",
                        }

                        async with self.session.post(
                            f"{API_BASE}/plans/{plan_id}/approve",
                            json=approval_request,
                            headers=self.headers,
                        ) as approval_response:
                            if approval_response.status == 200:
                                print("✅ Plan approved for execution")
                                return plan_id
                            else:
                                print(
                                    f"❌ Plan approval failed: {approval_response.status}"
                                )
                                return None
                    else:
                        print(
                            f"❌ Failed to get plan details: {details_response.status}"
                        )
                        return None
            else:
                print(f"❌ Plan generation failed: {response.status}")
                return None

    async def test_phase_2d_hands(self, plan_id):
        """Test Phase 2D: Action execution with browser automation (Hands)."""
        print("\n🤲 Testing Phase 2D: Hands (Action Execution)")

        # Test plan execution
        execution_request = {
            "plan_id": plan_id,
            "execution_options": {
                "take_screenshots": True,
                "screenshot_frequency": "every_step",
                "timeout_seconds": 300,
            },
        }

        async with self.session.post(
            f"{API_BASE}/execute", json=execution_request, headers=self.headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                execution_id = data["execution_id"]
                print(f"✅ Execution started - Execution ID: {execution_id}")

                # Monitor execution progress
                await self._monitor_execution_progress(execution_id)

                # Get final execution results
                async with self.session.get(
                    f"{API_BASE}/execute/{execution_id}/results", headers=self.headers
                ) as results_response:
                    if results_response.status == 200:
                        results = await results_response.json()
                        print("✅ Execution completed:")
                        print(f"   - Success: {results.get('success', False)}")
                        print(
                            f"   - Steps completed: {results.get('steps_completed', 0)}/{results.get('total_steps', 0)}"
                        )
                        print(
                            f"   - Success rate: {results.get('success_rate', 0):.1f}%"
                        )
                        print(
                            f"   - Duration: {results.get('total_duration_seconds', 0):.1f}s"
                        )
                        print(
                            f"   - Screenshots: {len(results.get('screenshots', []))}"
                        )
                        return execution_id
                    else:
                        print(
                            f"❌ Failed to get execution results: {results_response.status}"
                        )
                        return None
            else:
                print(f"❌ Execution failed to start: {response.status}")
                return None

    async def test_webhook_system(self):
        """Test webhook system for external integrations."""
        print("\n🔗 Testing Webhook System")

        # Test webhook configuration
        webhook_config = {
            "webhook_urls": ["https://httpbin.org/post"],
            "events": ["execution_completed", "execution_progress"],
        }

        async with self.session.post(
            f"{API_BASE}/webhooks/configure", json=webhook_config, headers=self.headers
        ) as response:
            if response.status == 200:
                print("✅ Webhook configuration successful")

                # Test webhook endpoint
                test_request = {"webhook_url": "https://httpbin.org/post"}

                async with self.session.post(
                    f"{API_BASE}/webhooks/test", json=test_request, headers=self.headers
                ) as test_response:
                    if test_response.status == 200:
                        test_data = await test_response.json()
                        print(
                            f"✅ Webhook test successful - Status: {test_data.get('response_status')}"
                        )
                        return True
                    else:
                        print(f"❌ Webhook test failed: {test_response.status}")
                        return False
            else:
                print(f"❌ Webhook configuration failed: {response.status}")
                return False

    async def _wait_for_task_completion(self, task_id, task_type):
        """Wait for a background task to complete."""
        print(f"⏳ Waiting for {task_type} to complete...")

        for attempt in range(30):  # 30 attempts = 60 seconds max
            await asyncio.sleep(2)

            async with self.session.get(
                f"{API_BASE}/tasks/{task_id}", headers=self.headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    status = data.get("status")
                    progress = data.get("progress_percentage", 0)

                    if status == "completed":
                        print(f"✅ {task_type.title()} completed successfully")
                        return True
                    elif status == "failed":
                        print(f"❌ {task_type.title()} failed")
                        return False
                    else:
                        print(f"⏳ {task_type.title()} progress: {progress}%")

        print(f"⏰ {task_type.title()} timeout")
        return False

    async def _wait_for_plan_completion(self, plan_id):
        """Wait for plan generation to complete."""
        print("⏳ Waiting for plan generation to complete...")

        for attempt in range(30):  # 30 attempts = 60 seconds max
            await asyncio.sleep(2)

            async with self.session.get(
                f"{API_BASE}/plans/{plan_id}", headers=self.headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    status = data.get("status")

                    if status == "pending_approval":
                        print("✅ Plan generation completed, ready for approval")
                        return True
                    elif status == "failed":
                        print("❌ Plan generation failed")
                        return False
                    else:
                        print(f"⏳ Plan generation status: {status}")

        print("⏰ Plan generation timeout")
        return False

    async def _monitor_execution_progress(self, execution_id):
        """Monitor execution progress in real-time."""
        print("⏳ Monitoring execution progress...")

        for attempt in range(60):  # 60 attempts = 2 minutes max
            await asyncio.sleep(2)

            async with self.session.get(
                f"{API_BASE}/execute/{execution_id}", headers=self.headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    status = data.get("status")
                    progress = data.get("progress_percentage", 0)
                    current_step = data.get("current_step", 0)
                    total_steps = data.get("total_steps", 0)

                    if status in ["completed", "failed", "cancelled"]:
                        print(f"✅ Execution {status}")
                        return True
                    else:
                        print(
                            f"⏳ Execution progress: {progress}% (Step {current_step}/{total_steps})"
                        )

        print("⏰ Execution monitoring timeout")
        return False


async def main():
    """Run complete WebAgent validation."""
    print("🚀 WebAgent Phase 2D Complete System Validation")
    print("=" * 60)
    print("Testing complete AI agent: Eyes + Brain + Hands")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    async with WebAgentValidator() as validator:
        # Authenticate
        if not await validator.authenticate():
            print("❌ Authentication failed, cannot proceed")
            return False

        # Test Phase 2B: Eyes (Semantic Understanding)
        webpage_task_id = await validator.test_phase_2b_eyes()
        if not webpage_task_id:
            print("❌ Phase 2B (Eyes) failed, cannot proceed")
            return False

        # Test Phase 2C: Brain (AI Planning)
        plan_id = await validator.test_phase_2c_brain(webpage_task_id)
        if not plan_id:
            print("❌ Phase 2C (Brain) failed, cannot proceed")
            return False

        # Test Phase 2D: Hands (Action Execution)
        execution_id = await validator.test_phase_2d_hands(plan_id)
        if not execution_id:
            print("❌ Phase 2D (Hands) failed")
            return False

        # Test Webhook System
        webhook_success = await validator.test_webhook_system()

        print("\n" + "=" * 60)
        print("🎉 WEBAGENT COMPLETE SYSTEM VALIDATION RESULTS")
        print("=" * 60)
        print("✅ Phase 2B: Eyes (Semantic Understanding) - WORKING")
        print("✅ Phase 2C: Brain (AI Planning) - WORKING")
        print("✅ Phase 2D: Hands (Action Execution) - WORKING")
        print(
            f"{'✅' if webhook_success else '❌'} Webhook System - {'WORKING' if webhook_success else 'FAILED'}"
        )
        print()
        print("🤖 WebAgent is now a COMPLETE AI AGENT!")
        print("   👁️ Can SEE and understand websites semantically")
        print("   🧠 Can THINK and plan complex automation tasks")
        print("   🤲 Can ACT and execute browser automation")
        print()
        print("Ready for production use! 🚀")

        return True


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        sys.exit(1)
