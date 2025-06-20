"""
Enterprise SSO Database Service

Database-backed SSO configuration and user provisioning service that
integrates Claude Code's SSO implementation with enterprise database models.
"""

import json
import secrets
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.core.security import encrypt_credential, decrypt_credential
from app.models.security import SSOConfiguration, EnterpriseTenant, user_tenant_roles
from app.models.user import User
from app.schemas.enterprise import (
    SSOConfigurationCreate, SSOConfigurationUpdate
)
from app.schemas.user import EnterpriseUserCreate, UserTenantRoleAssignment
from app.security.sso_integration import enterprise_sso, SSOUser, SSOAuthResult
from app.services.rbac_service import enterprise_rbac_service
from app.services.tenant_service import enterprise_tenant_service
from app.core.config import settings

logger = get_logger(__name__)


class EnterpriseSSOManagedService:
    """
    Enterprise SSO Database Service
    
    Manages SSO configurations in database and handles user provisioning
    with integration to Claude Code's SSO implementation.
    """
    
    async def create_sso_configuration(
        self,
        db: AsyncSession,
        config_data: SSOConfigurationCreate,
        created_by: int
    ) -> SSOConfiguration:
        """Create a new SSO configuration for tenant."""
        
        try:
            # Verify tenant exists
            tenant = await enterprise_tenant_service.get_tenant(db, tenant_id=config_data.tenant_id)
            if not tenant:
                raise ValueError(f"Tenant {config_data.tenant_id} not found")
            
            # Check if configuration already exists for this tenant/provider
            existing_result = await db.execute(
                select(SSOConfiguration).where(
                    and_(
                        SSOConfiguration.tenant_id == config_data.tenant_id,
                        SSOConfiguration.provider == config_data.provider.value
                    )
                )
            )
            if existing_result.scalar_one_or_none():
                raise ValueError(f"SSO configuration for {config_data.provider.value} already exists for this tenant")
            
            # Encrypt sensitive configuration data
            encryption_key_id = f"sso_key_{secrets.token_hex(8)}"
            encrypted_config = await self._encrypt_sso_config(config_data.configuration, encryption_key_id)
            
            # Create SSO configuration
            db_config = SSOConfiguration(
                tenant_id=config_data.tenant_id,
                provider=config_data.provider.value,
                protocol=config_data.protocol.value,
                name=config_data.name,
                display_name=config_data.display_name,
                is_active=config_data.is_active,
                is_primary=config_data.is_primary,
                auto_provision_users=config_data.auto_provision_users,
                configuration=encrypted_config,
                encryption_key_id=encryption_key_id,
                attribute_mapping=config_data.attribute_mapping,
                role_mapping=config_data.role_mapping,
                require_signed_assertions=config_data.require_signed_assertions,
                require_encrypted_assertions=config_data.require_encrypted_assertions,
                session_timeout_minutes=config_data.session_timeout_minutes
            )
            
            # If this is set as primary, unset other primary configs for tenant
            if config_data.is_primary:
                await db.execute(
                    SSOConfiguration.__table__.update().where(
                        SSOConfiguration.tenant_id == config_data.tenant_id
                    ).values(is_primary=False)
                )
            
            db.add(db_config)
            await db.commit()
            await db.refresh(db_config)
            
            logger.info(f"Created SSO configuration for {config_data.provider.value} in tenant {config_data.tenant_id}")
            return db_config
            
        except Exception as e:
            logger.error(f"Failed to create SSO configuration: {str(e)}")
            await db.rollback()
            raise
    
    async def get_sso_configuration(
        self,
        db: AsyncSession,
        tenant_id: int,
        provider: Optional[str] = None,
        is_primary: bool = False
    ) -> Optional[SSOConfiguration]:
        """Get SSO configuration for tenant."""
        
        try:
            query = select(SSOConfiguration).where(
                and_(
                    SSOConfiguration.tenant_id == tenant_id,
                    SSOConfiguration.is_active == True
                )
            )
            
            if provider:
                query = query.where(SSOConfiguration.provider == provider)
            
            if is_primary:
                query = query.where(SSOConfiguration.is_primary == True)
            
            result = await db.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Failed to get SSO configuration: {str(e)}")
            return None
    
    async def list_sso_configurations(
        self,
        db: AsyncSession,
        tenant_id: int
    ) -> List[SSOConfiguration]:
        """List all SSO configurations for tenant."""
        
        try:
            result = await db.execute(
                select(SSOConfiguration).where(
                    SSOConfiguration.tenant_id == tenant_id
                ).order_by(SSOConfiguration.created_at.desc())
            )
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Failed to list SSO configurations: {str(e)}")
            return []
    
    async def authenticate_sso_user(
        self,
        db: AsyncSession,
        tenant_id: int,
        provider: str,
        sso_auth_result: SSOAuthResult
    ) -> Dict[str, Any]:
        """Authenticate and provision SSO user."""
        
        try:
            if not sso_auth_result.success or not sso_auth_result.user:
                return {
                    "success": False,
                    "error": sso_auth_result.error_message or "SSO authentication failed"
                }
            
            sso_user = sso_auth_result.user
            
            # Get SSO configuration
            sso_config = await self.get_sso_configuration(db, tenant_id, provider)
            if not sso_config:
                return {
                    "success": False,
                    "error": f"SSO configuration not found for provider {provider}"
                }
            
            # Find or create user
            user = await self._find_or_create_user(db, sso_user, sso_config, tenant_id)
            if not user:
                return {
                    "success": False,
                    "error": "Failed to provision user"
                }
            
            # Create access session
            session = await enterprise_rbac_service.create_access_session(
                db, 
                user.id, 
                tenant_id,
                {
                    "is_sso": True,
                    "sso_session_id": sso_auth_result.session_id,
                    "sso_provider": provider,
                    "device_fingerprint": None,  # Would be provided by client
                    "ip_address": None,  # Would be provided by client
                    "user_agent": None,  # Would be provided by client
                    "requires_mfa": sso_config.require_signed_assertions,
                    "requires_device_trust": False
                }
            )
            
            # Update SSO configuration last used timestamp
            sso_config.last_used_at = datetime.utcnow()
            await db.commit()
            
            return {
                "success": True,
                "user_id": user.id,
                "session_id": session.session_id,
                "access_token": sso_auth_result.access_token,
                "refresh_token": sso_auth_result.refresh_token,
                "expires_in": sso_auth_result.expires_in
            }
            
        except Exception as e:
            logger.error(f"SSO user authentication failed: {str(e)}")
            return {
                "success": False,
                "error": f"Authentication error: {str(e)}"
            }
    
    async def _find_or_create_user(
        self,
        db: AsyncSession,
        sso_user: SSOUser,
        sso_config: SSOConfiguration,
        tenant_id: int
    ) -> Optional[User]:
        """Find existing user or create new one from SSO data."""
        
        try:
            # Try to find user by email first
            result = await db.execute(
                select(User).where(User.email == sso_user.email)
            )
            user = result.scalar_one_or_none()
            
            if user:
                # Update existing user with SSO data
                await self._update_user_from_sso(db, user, sso_user, sso_config)
                
                # Ensure user is associated with tenant
                await self._ensure_user_tenant_association(db, user.id, tenant_id, sso_config)
                
                return user
            
            elif sso_config.auto_provision_users:
                # Create new user
                return await self._create_user_from_sso(db, sso_user, sso_config, tenant_id)
            
            else:
                logger.warning(f"User {sso_user.email} not found and auto-provisioning disabled")
                return None
                
        except Exception as e:
            logger.error(f"Failed to find or create user: {str(e)}")
            return None
    
    async def _create_user_from_sso(
        self,
        db: AsyncSession,
        sso_user: SSOUser,
        sso_config: SSOConfiguration,
        tenant_id: int
    ) -> Optional[User]:
        """Create new user from SSO data."""
        
        try:
            # Create user
            user = User(
                email=sso_user.email,
                username=sso_user.username or sso_user.email.split('@')[0],
                hashed_password="",  # SSO users don't have passwords
                full_name=f"{sso_user.first_name or ''} {sso_user.last_name or ''}".strip() or None,
                is_active=True,
                employee_id=sso_user.employee_id,
                department=sso_user.department,
                job_title=sso_user.title,
                sso_provider=sso_config.provider,
                sso_user_id=sso_user.provider_user_id,
                sso_attributes=sso_user.attributes,
                mfa_enabled=True,  # SSO users should have MFA enabled
                data_classification="internal",
                gdpr_consent=True  # Assume consent for SSO users
            )
            
            db.add(user)
            await db.flush()  # Get user ID
            
            # Associate user with tenant and assign roles
            await self._ensure_user_tenant_association(db, user.id, tenant_id, sso_config)
            
            await db.commit()
            await db.refresh(user)
            
            logger.info(f"Created user {user.email} from SSO provider {sso_config.provider}")
            return user
            
        except Exception as e:
            logger.error(f"Failed to create user from SSO: {str(e)}")
            await db.rollback()
            return None
    
    async def _update_user_from_sso(
        self,
        db: AsyncSession,
        user: User,
        sso_user: SSOUser,
        sso_config: SSOConfiguration
    ) -> None:
        """Update existing user with SSO data."""
        
        try:
            # Update user attributes
            if sso_user.first_name or sso_user.last_name:
                user.full_name = f"{sso_user.first_name or ''} {sso_user.last_name or ''}".strip()
            
            if sso_user.employee_id:
                user.employee_id = sso_user.employee_id
            
            if sso_user.department:
                user.department = sso_user.department
            
            if sso_user.title:
                user.job_title = sso_user.title
            
            # Update SSO attributes
            user.sso_provider = sso_config.provider
            user.sso_user_id = sso_user.provider_user_id
            user.sso_attributes = sso_user.attributes
            user.last_login_at = datetime.utcnow()
            
            logger.info(f"Updated user {user.email} from SSO provider {sso_config.provider}")
            
        except Exception as e:
            logger.error(f"Failed to update user from SSO: {str(e)}")
            raise
    
    async def _ensure_user_tenant_association(
        self,
        db: AsyncSession,
        user_id: int,
        tenant_id: int,
        sso_config: SSOConfiguration
    ) -> None:
        """Ensure user is associated with tenant and has appropriate roles."""
        
        try:
            # Check if user is already associated with tenant
            result = await db.execute(
                select(user_tenant_roles).where(
                    and_(
                        user_tenant_roles.c.user_id == user_id,
                        user_tenant_roles.c.tenant_id == tenant_id
                    )
                )
            )
            existing_association = result.first()
            
            if not existing_association:
                # Determine default role based on SSO role mapping
                default_role_id = await self._get_default_role_id(db, sso_config)
                
                if default_role_id:
                    # Create user-tenant-role association
                    await db.execute(
                        user_tenant_roles.insert().values(
                            user_id=user_id,
                            tenant_id=tenant_id,
                            role_id=default_role_id,
                            assigned_by=None,  # System assignment
                            expires_at=None
                        )
                    )
                    
                    logger.info(f"Associated user {user_id} with tenant {tenant_id} and role {default_role_id}")
            
        except Exception as e:
            logger.error(f"Failed to ensure user-tenant association: {str(e)}")
            raise
    
    async def _get_default_role_id(self, db: AsyncSession, sso_config: SSOConfiguration) -> Optional[int]:
        """Get default role ID for SSO users."""
        
        try:
            from app.models.security import EnterpriseRole
            
            # Look for "end_user" role as default
            result = await db.execute(
                select(EnterpriseRole).where(EnterpriseRole.role_id == "end_user")
            )
            role = result.scalar_one_or_none()
            
            return role.id if role else None
            
        except Exception as e:
            logger.error(f"Failed to get default role ID: {str(e)}")
            return None
    
    async def _encrypt_sso_config(self, config: Dict[str, Any], key_id: str) -> Dict[str, Any]:
        """Encrypt sensitive SSO configuration data."""
        
        try:
            # Identify sensitive fields that should be encrypted
            sensitive_fields = {
                'client_secret', 'private_key', 'certificate', 'signing_key',
                'encryption_key', 'shared_secret', 'api_key', 'token'
            }
            
            encrypted_config = {}
            for key, value in config.items():
                if key.lower() in sensitive_fields and value:
                    # Encrypt sensitive values
                    encrypted_config[key] = encrypt_credential(str(value), key_id)
                else:
                    encrypted_config[key] = value
            
            return encrypted_config
            
        except Exception as e:
            logger.error(f"Failed to encrypt SSO config: {str(e)}")
            return config
    
    async def _decrypt_sso_config(self, encrypted_config: Dict[str, Any], key_id: str) -> Dict[str, Any]:
        """Decrypt SSO configuration data."""
        
        try:
            sensitive_fields = {
                'client_secret', 'private_key', 'certificate', 'signing_key',
                'encryption_key', 'shared_secret', 'api_key', 'token'
            }
            
            decrypted_config = {}
            for key, value in encrypted_config.items():
                if key.lower() in sensitive_fields and value:
                    # Decrypt sensitive values
                    decrypted_config[key] = decrypt_credential(value, key_id)
                else:
                    decrypted_config[key] = value
            
            return decrypted_config
            
        except Exception as e:
            logger.error(f"Failed to decrypt SSO config: {str(e)}")
            return encrypted_config
    
    async def test_sso_configuration(
        self,
        db: AsyncSession,
        config_id: int
    ) -> Dict[str, Any]:
        """Test SSO configuration connectivity."""
        
        try:
            result = await db.execute(
                select(SSOConfiguration).where(SSOConfiguration.id == config_id)
            )
            config = result.scalar_one_or_none()
            
            if not config:
                return {"success": False, "error": "Configuration not found"}
            
            # Decrypt configuration for testing
            decrypted_config = await self._decrypt_sso_config(config.configuration, config.encryption_key_id)
            
            # Test based on protocol
            if config.protocol == "oidc":
                return await self._test_oidc_config(decrypted_config)
            elif config.protocol == "saml2":
                return await self._test_saml_config(decrypted_config)
            else:
                return {"success": False, "error": f"Unsupported protocol: {config.protocol}"}
                
        except Exception as e:
            logger.error(f"SSO configuration test failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _test_oidc_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test OIDC configuration."""
        
        try:
            import aiohttp
            
            # Test discovery endpoint or individual endpoints
            discovery_url = config.get('discovery_url')
            if discovery_url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(discovery_url) as response:
                        if response.status == 200:
                            return {"success": True, "message": "OIDC discovery endpoint accessible"}
                        else:
                            return {"success": False, "error": f"Discovery endpoint returned {response.status}"}
            
            # Test individual endpoints
            auth_endpoint = config.get('authorization_endpoint')
            if auth_endpoint:
                async with aiohttp.ClientSession() as session:
                    async with session.get(auth_endpoint) as response:
                        if response.status in [200, 400]:  # 400 is expected for missing parameters
                            return {"success": True, "message": "OIDC authorization endpoint accessible"}
                        else:
                            return {"success": False, "error": f"Authorization endpoint returned {response.status}"}
            
            return {"success": False, "error": "No testable endpoints configured"}
            
        except Exception as e:
            return {"success": False, "error": f"OIDC test failed: {str(e)}"}
    
    async def _test_saml_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test SAML configuration."""
        
        try:
            import aiohttp
            
            # Test metadata URL if available
            metadata_url = config.get('metadata_url')
            if metadata_url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(metadata_url) as response:
                        if response.status == 200:
                            content = await response.text()
                            if 'EntityDescriptor' in content:
                                return {"success": True, "message": "SAML metadata accessible and valid"}
                            else:
                                return {"success": False, "error": "Invalid SAML metadata format"}
                        else:
                            return {"success": False, "error": f"Metadata endpoint returned {response.status}"}
            
            # Test SSO URL
            sso_url = config.get('sso_url')
            if sso_url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(sso_url) as response:
                        if response.status in [200, 400, 405]:  # Various expected responses
                            return {"success": True, "message": "SAML SSO endpoint accessible"}
                        else:
                            return {"success": False, "error": f"SSO endpoint returned {response.status}"}
            
            return {"success": False, "error": "No testable endpoints configured"}
            
        except Exception as e:
            return {"success": False, "error": f"SAML test failed: {str(e)}"}


# Global instance
enterprise_sso_service = EnterpriseSSOManagedService()
