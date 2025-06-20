"""
Enterprise Single Sign-On (SSO) Integration

Comprehensive SSO integration supporting SAML 2.0, OpenID Connect,
and major enterprise identity providers with automated user provisioning.
"""

import asyncio
import json
import base64
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import hashlib
import uuid
import jwt
import aiohttp
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509 import load_pem_x509_certificate

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.user import EnterpriseUserCreate, SecurityRole
from app.security.rbac_engine import enterprise_access_control

logger = get_logger(__name__)


class SSOProtocol(str, Enum):
    """Supported SSO protocols."""
    SAML2 = "saml2"
    OPENID_CONNECT = "oidc"
    OAUTH2 = "oauth2"


class SSOProvider(str, Enum):
    """Supported SSO providers."""
    OKTA = "okta"
    AZURE_AD = "azure_ad"
    GOOGLE_WORKSPACE = "google_workspace"
    PING_IDENTITY = "ping_identity"
    AUTH0 = "auth0"
    ONELOGIN = "onelogin"
    ADFS = "adfs"
    GENERIC_SAML = "generic_saml"
    GENERIC_OIDC = "generic_oidc"


@dataclass
class SSOConfiguration:
    """SSO provider configuration."""
    
    provider: SSOProvider
    protocol: SSOProtocol
    name: str
    enabled: bool = True
    
    # SAML Configuration
    entity_id: Optional[str] = None
    sso_url: Optional[str] = None
    slo_url: Optional[str] = None
    x509_cert: Optional[str] = None
    metadata_url: Optional[str] = None
    
    # OIDC Configuration
    authorization_endpoint: Optional[str] = None
    token_endpoint: Optional[str] = None
    userinfo_endpoint: Optional[str] = None
    jwks_uri: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    
    # Attribute Mapping
    attribute_mapping: Dict[str, str] = field(default_factory=dict)
    role_mapping: Dict[str, SecurityRole] = field(default_factory=dict)
    
    # Provisioning Settings
    auto_provision_users: bool = True
    auto_assign_roles: bool = True
    default_role: SecurityRole = SecurityRole.END_USER
    require_group_membership: List[str] = field(default_factory=list)
    
    # Security Settings
    require_signed_assertions: bool = True
    require_encrypted_assertions: bool = False
    session_timeout_minutes: int = 480  # 8 hours
    
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SSOUser:
    """SSO user information."""
    
    provider_user_id: str
    email: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    department: Optional[str] = None
    title: Optional[str] = None
    manager_email: Optional[str] = None
    groups: List[str] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    # Security Attributes
    clearance_level: Optional[str] = None
    employee_id: Optional[str] = None
    location: Optional[str] = None
    
    authenticated_at: datetime = field(default_factory=datetime.utcnow)
    session_expires_at: Optional[datetime] = None


@dataclass
class SSOAuthResult:
    """SSO authentication result."""
    
    success: bool
    user: Optional[SSOUser] = None
    webagent_user_id: Optional[int] = None
    error_message: Optional[str] = None
    requires_provisioning: bool = False
    session_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None


class SAMLHandler:
    """SAML 2.0 authentication handler."""
    
    def __init__(self, config: SSOConfiguration):
        self.config = config
        self.sp_entity_id = settings.SAML_SP_ENTITY_ID or f"https://webagent.ai/saml/metadata"
        self.sp_acs_url = f"https://webagent.ai/auth/saml/{config.provider.value}/acs"
    
    async def initiate_login(self, relay_state: Optional[str] = None) -> str:
        """Initiate SAML login by generating AuthnRequest."""
        
        try:
            request_id = f"saml_req_{uuid.uuid4().hex}"
            timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            
            # Create SAML AuthnRequest
            authn_request = f"""
            <samlp:AuthnRequest 
                xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
                ID="{request_id}"
                Version="2.0"
                IssueInstant="{timestamp}"
                Destination="{self.config.sso_url}"
                AssertionConsumerServiceURL="{self.sp_acs_url}"
                ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
                <saml:Issuer>{self.sp_entity_id}</saml:Issuer>
                <samlp:NameIDPolicy 
                    Format="urn:oasis:names:tc:SAML:2.0:nameid-format:emailAddress"
                    AllowCreate="true"/>
            </samlp:AuthnRequest>
            """
            
            # Base64 encode the request
            encoded_request = base64.b64encode(authn_request.encode('utf-8')).decode('utf-8')
            
            # Build SSO URL with parameters
            sso_url = f"{self.config.sso_url}?SAMLRequest={encoded_request}"
            if relay_state:
                sso_url += f"&RelayState={relay_state}"
            
            logger.info(
                "SAML login initiated",
                provider=self.config.provider.value,
                request_id=request_id
            )
            
            return sso_url
            
        except Exception as e:
            logger.error(f"SAML login initiation failed: {str(e)}")
            raise
    
    async def handle_response(self, saml_response: str, relay_state: Optional[str] = None) -> SSOAuthResult:
        """Handle SAML response and extract user information."""
        
        try:
            # Decode base64 response
            decoded_response = base64.b64decode(saml_response).decode('utf-8')
            
            # Parse XML
            root = ET.fromstring(decoded_response)
            
            # Extract namespace
            ns = {
                'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
                'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol'
            }
            
            # Verify response status
            status = root.find('.//samlp:StatusCode', ns)
            if status is None or status.get('Value') != 'urn:oasis:names:tc:SAML:2.0:status:Success':
                return SSOAuthResult(
                    success=False,
                    error_message="SAML authentication failed"
                )

            # Extract assertion
            assertion = root.find('.//saml:Assertion', ns)
            if assertion is None:
                return SSOAuthResult(
                    success=False,
                    error_message="No SAML assertion found"
                )

            # Verify signature if required
            if self.config.require_signed_assertions:
                if not await self._verify_signature(assertion):
                    return SSOAuthResult(
                        success=False,
                        error_message="SAML assertion signature verification failed"
                    )

            # Extract user attributes
            user = await self._extract_user_from_assertion(assertion, ns)

            logger.info(
                "SAML response processed successfully",
                provider=self.config.provider.value,
                user_email=user.email
            )

            return SSOAuthResult(
                success=True,
                user=user
            )

        except Exception as e:
            logger.error(f"SAML response handling failed: {str(e)}")
            return SSOAuthResult(
                success=False,
                error_message=f"SAML processing error: {str(e)}"
            )


# Global enterprise SSO instance
enterprise_sso = EnterpriseSSO()