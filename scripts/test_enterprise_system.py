#!/usr/bin/env python3
"""
Enterprise System Test Runner

Comprehensive test runner for the enterprise RBAC/ABAC system
with setup, validation, and reporting capabilities.
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, Any, List
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_async_session
from app.core.logging import get_logger
from app.services.tenant_service import enterprise_tenant_service
from app.services.rbac_service import enterprise_rbac_service
from app.services.abac_service import enterprise_abac_service
from app.services.sso_service import enterprise_sso_service
from app.schemas.enterprise import (
    EnterpriseTenantCreate, EnterpriseRoleCreate, ABACPolicyCreate,
    SSOConfigurationCreate
)
from app.schemas.user import UserTenantRoleAssignment
from app.models.user import User

logger = get_logger(__name__)


class EnterpriseSystemTester:
    """Comprehensive enterprise system tester."""
    
    def __init__(self):
        self.test_results = []
        self.test_data = {}
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all enterprise system tests."""
        
        logger.info("Starting enterprise system tests")
        
        async for db in get_async_session():
            try:
                # Initialize system
                await self.test_system_initialization(db)
                
                # Test tenant management
                await self.test_tenant_operations(db)
                
                # Test RBAC system
                await self.test_rbac_system(db)
                
                # Test ABAC system
                await self.test_abac_system(db)
                
                # Test SSO integration
                await self.test_sso_integration(db)
                
                # Test security validation
                await self.test_security_features(db)
                
                # Test performance
                await self.test_performance(db)
                
                break
                
            except Exception as e:
                logger.error(f"Test execution failed: {str(e)}")
                self.add_test_result("SYSTEM", "FAILED", str(e))
                return self.generate_report()
        
        return self.generate_report()
    
    async def test_system_initialization(self, db: AsyncSession):
        """Test enterprise system initialization."""
        
        try:
            logger.info("Testing system initialization")
            
            # Initialize system permissions
            await enterprise_rbac_service.initialize_system_permissions(db)
            self.add_test_result("System Permissions", "PASSED", "System permissions initialized")
            
            # Initialize system roles
            await enterprise_rbac_service.initialize_system_roles(db)
            self.add_test_result("System Roles", "PASSED", "System roles initialized")
            
            # Verify initialization
            from sqlalchemy import select, func
            from app.models.security import EnterprisePermission, EnterpriseRole
            
            perm_count = await db.execute(select(func.count(EnterprisePermission.id)))
            role_count = await db.execute(select(func.count(EnterpriseRole.id)))
            
            perm_total = perm_count.scalar()
            role_total = role_count.scalar()
            
            if perm_total > 0 and role_total > 0:
                self.add_test_result(
                    "System Verification", 
                    "PASSED", 
                    f"Created {perm_total} permissions and {role_total} roles"
                )
            else:
                self.add_test_result("System Verification", "FAILED", "No permissions or roles created")
                
        except Exception as e:
            self.add_test_result("System Initialization", "FAILED", str(e))
    
    async def test_tenant_operations(self, db: AsyncSession):
        """Test tenant management operations."""
        
        try:
            logger.info("Testing tenant operations")
            
            # Create test tenant
            tenant_data = EnterpriseTenantCreate(
                tenant_id="test_enterprise",
                name="Test Enterprise",
                display_name="Test Enterprise Corp",
                domain="test-enterprise.com",
                admin_email="admin@test-enterprise.com",
                compliance_level="confidential",
                max_users=100,
                enforce_sso=True,
                require_mfa=True
            )
            
            tenant = await enterprise_tenant_service.create_tenant(db, tenant_data, 1)
            self.test_data["tenant"] = tenant
            self.add_test_result("Tenant Creation", "PASSED", f"Created tenant: {tenant.tenant_id}")
            
            # Test tenant stats
            stats = await enterprise_tenant_service.get_tenant_stats(db, tenant.id)
            if stats and "tenant_id" in stats:
                self.add_test_result("Tenant Stats", "PASSED", f"Retrieved stats for {stats['tenant_id']}")
            else:
                self.add_test_result("Tenant Stats", "FAILED", "Failed to retrieve tenant stats")
            
            # Test tenant limits
            limits = await enterprise_tenant_service.check_tenant_limits(db, tenant.id, "users")
            if limits and "maximum" in limits:
                self.add_test_result("Tenant Limits", "PASSED", f"User limit: {limits['maximum']}")
            else:
                self.add_test_result("Tenant Limits", "FAILED", "Failed to check tenant limits")
                
        except Exception as e:
            self.add_test_result("Tenant Operations", "FAILED", str(e))
    
    async def test_rbac_system(self, db: AsyncSession):
        """Test RBAC system functionality."""
        
        try:
            logger.info("Testing RBAC system")
            
            # Create test user
            user = User(
                email="rbac.test@test-enterprise.com",
                username="rbactest",
                hashed_password="test_hash",
                full_name="RBAC Test User",
                is_active=True,
                employee_id="RBAC001",
                department="Testing"
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            self.test_data["user"] = user
            
            # Create test role
            role_data = EnterpriseRoleCreate(
                role_id="test_analyst",
                name="Test Analyst",
                display_name="Test Data Analyst",
                description="Test role for data analysis",
                is_system_role=False,
                is_tenant_scoped=True,
                permission_ids=[]
            )
            
            role = await enterprise_rbac_service.create_role(db, role_data, 1)
            self.test_data["role"] = role
            self.add_test_result("Role Creation", "PASSED", f"Created role: {role.role_id}")
            
            # Assign role to user
            if "tenant" in self.test_data:
                assignment = UserTenantRoleAssignment(
                    user_id=user.id,
                    tenant_id=self.test_data["tenant"].id,
                    role_ids=[role.id]
                )
                
                success = await enterprise_rbac_service.assign_user_roles(db, assignment, 1)
                if success:
                    self.add_test_result("Role Assignment", "PASSED", "User role assigned successfully")
                else:
                    self.add_test_result("Role Assignment", "FAILED", "Failed to assign role")
                
                # Test permission check
                permissions = await enterprise_rbac_service.get_user_permissions(
                    db, user.id, self.test_data["tenant"].id
                )
                self.add_test_result(
                    "Permission Retrieval", 
                    "PASSED", 
                    f"Retrieved {len(permissions)} permissions"
                )
            
        except Exception as e:
            self.add_test_result("RBAC System", "FAILED", str(e))
    
    async def test_abac_system(self, db: AsyncSession):
        """Test ABAC policy system."""
        
        try:
            logger.info("Testing ABAC system")
            
            # Create test policy
            policy_data = ABACPolicyCreate(
                policy_id="test_data_access",
                tenant_id=self.test_data.get("tenant", {}).id if "tenant" in self.test_data else None,
                name="Test Data Access Policy",
                description="Test policy for data access control",
                effect="ALLOW",
                priority=100,
                conditions={
                    "user.department": {"eq": "Testing"},
                    "resource.classification": {"in": ["internal", "public"]},
                    "env.is_business_hours": {"eq": True}
                },
                resources=["data", "report"],
                actions=["read", "analyze"]
            )
            
            policy = await enterprise_abac_service.create_policy(db, policy_data, 1)
            self.test_data["policy"] = policy
            self.add_test_result("ABAC Policy Creation", "PASSED", f"Created policy: {policy.policy_id}")
            
            # Test policy evaluation
            if "user" in self.test_data and "tenant" in self.test_data:
                decision = await enterprise_abac_service.evaluate_access(
                    db,
                    user_id=self.test_data["user"].id,
                    resource_type="data",
                    resource_id="test_dataset_123",
                    action="read",
                    tenant_id=self.test_data["tenant"].id,
                    context={"is_business_hours": True}
                )
                
                if hasattr(decision, 'decision'):
                    self.add_test_result(
                        "ABAC Evaluation", 
                        "PASSED", 
                        f"Policy evaluation result: {decision.decision}"
                    )
                else:
                    self.add_test_result("ABAC Evaluation", "FAILED", "Invalid decision object")
            
        except Exception as e:
            self.add_test_result("ABAC System", "FAILED", str(e))
    
    async def test_sso_integration(self, db: AsyncSession):
        """Test SSO integration functionality."""
        
        try:
            logger.info("Testing SSO integration")
            
            if "tenant" not in self.test_data:
                self.add_test_result("SSO Integration", "SKIPPED", "No tenant available")
                return
            
            # Create SSO configuration
            sso_data = SSOConfigurationCreate(
                tenant_id=self.test_data["tenant"].id,
                provider="test_provider",
                protocol="oidc",
                name="Test SSO",
                display_name="Test SSO Provider",
                configuration={
                    "client_id": "test_client_123",
                    "client_secret": "test_secret_456",
                    "authorization_endpoint": "https://test.example.com/auth",
                    "token_endpoint": "https://test.example.com/token"
                },
                attribute_mapping={
                    "email": "email",
                    "given_name": "first_name",
                    "family_name": "last_name"
                }
            )
            
            config = await enterprise_sso_service.create_sso_configuration(db, sso_data, 1)
            self.test_data["sso_config"] = config
            self.add_test_result("SSO Configuration", "PASSED", f"Created SSO config: {config.name}")
            
            # Test configuration listing
            configs = await enterprise_sso_service.list_sso_configurations(db, self.test_data["tenant"].id)
            if len(configs) > 0:
                self.add_test_result("SSO Listing", "PASSED", f"Found {len(configs)} SSO configurations")
            else:
                self.add_test_result("SSO Listing", "FAILED", "No SSO configurations found")
            
        except Exception as e:
            self.add_test_result("SSO Integration", "FAILED", str(e))
    
    async def test_security_features(self, db: AsyncSession):
        """Test security features and validation."""
        
        try:
            logger.info("Testing security features")
            
            # Test encryption of sensitive data
            test_config = {"client_secret": "sensitive_data", "api_key": "secret_key"}
            encrypted = await enterprise_sso_service._encrypt_sso_config(test_config, "test_key")
            
            if encrypted["client_secret"] != "sensitive_data":
                self.add_test_result("Data Encryption", "PASSED", "Sensitive data encrypted")
            else:
                self.add_test_result("Data Encryption", "FAILED", "Sensitive data not encrypted")
            
            # Test access session creation with trust scoring
            if "user" in self.test_data:
                session = await enterprise_rbac_service.create_access_session(
                    db,
                    user_id=self.test_data["user"].id,
                    session_data={
                        "device_fingerprint": "unknown_device",
                        "ip_address": "192.168.1.100",
                        "is_sso": False
                    }
                )
                
                if 0.0 <= session.initial_trust_score <= 1.0:
                    self.add_test_result(
                        "Trust Scoring", 
                        "PASSED", 
                        f"Trust score: {session.initial_trust_score}"
                    )
                else:
                    self.add_test_result("Trust Scoring", "FAILED", "Invalid trust score")
            
        except Exception as e:
            self.add_test_result("Security Features", "FAILED", str(e))
    
    async def test_performance(self, db: AsyncSession):
        """Test system performance."""
        
        try:
            logger.info("Testing performance")
            
            import time
            
            if "user" in self.test_data and "tenant" in self.test_data:
                # Test permission check performance
                start_time = time.time()
                
                for _ in range(50):
                    await enterprise_rbac_service.check_user_permission(
                        db, 
                        self.test_data["user"].id, 
                        "tasks:read", 
                        self.test_data["tenant"].id
                    )
                
                end_time = time.time()
                total_time = end_time - start_time
                avg_time = total_time / 50
                
                if avg_time < 0.1:  # Less than 100ms per check
                    self.add_test_result(
                        "Permission Check Performance", 
                        "PASSED", 
                        f"Average time: {avg_time:.3f}s"
                    )
                else:
                    self.add_test_result(
                        "Permission Check Performance", 
                        "WARNING", 
                        f"Slow performance: {avg_time:.3f}s"
                    )
            
        except Exception as e:
            self.add_test_result("Performance Testing", "FAILED", str(e))
    
    def add_test_result(self, test_name: str, status: str, details: str):
        """Add test result to results list."""
        self.test_results.append({
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Log result
        if status == "PASSED":
            logger.info(f"✓ {test_name}: {details}")
        elif status == "FAILED":
            logger.error(f"✗ {test_name}: {details}")
        elif status == "WARNING":
            logger.warning(f"⚠ {test_name}: {details}")
        else:
            logger.info(f"- {test_name}: {details}")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        
        passed = len([r for r in self.test_results if r["status"] == "PASSED"])
        failed = len([r for r in self.test_results if r["status"] == "FAILED"])
        warnings = len([r for r in self.test_results if r["status"] == "WARNING"])
        skipped = len([r for r in self.test_results if r["status"] == "SKIPPED"])
        total = len(self.test_results)
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        report = {
            "summary": {
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "warnings": warnings,
                "skipped": skipped,
                "success_rate": f"{success_rate:.1f}%",
                "overall_status": "PASSED" if failed == 0 else "FAILED"
            },
            "results": self.test_results,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return report


async def main():
    """Main test runner function."""
    
    print("🚀 Starting Enterprise RBAC/ABAC System Tests")
    print("=" * 60)
    
    tester = EnterpriseSystemTester()
    report = await tester.run_all_tests()
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    summary = report["summary"]
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Warnings: {summary['warnings']}")
    print(f"Skipped: {summary['skipped']}")
    print(f"Success Rate: {summary['success_rate']}")
    print(f"Overall Status: {summary['overall_status']}")
    
    # Save detailed report
    report_file = project_root / "test_reports" / f"enterprise_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_file.parent.mkdir(exist_ok=True)
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: {report_file}")
    
    # Exit with appropriate code
    sys.exit(0 if summary["overall_status"] == "PASSED" else 1)


if __name__ == "__main__":
    asyncio.run(main())
