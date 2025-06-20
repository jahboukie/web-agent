"""
Hardware Security Module (HSM) & Key Management Service (KMS) Integration

Enterprise-grade cryptographic key management with HSM support for
AWS CloudHSM, Azure Key Vault, Google Cloud HSM, and on-premises HSMs.
"""

import asyncio
import json
import base64
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import uuid
import hashlib
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, ec, ed25519, x25519
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import boto3
from azure.identity import DefaultAzureCredential
from azure.keyvault.keys import KeyClient
from google.cloud import kms

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class HSMProvider(str, Enum):
    """Supported HSM/KMS providers."""
    AWS_CLOUDHSM = "aws_cloudhsm"
    AWS_KMS = "aws_kms"
    AZURE_KEY_VAULT = "azure_key_vault"
    AZURE_MANAGED_HSM = "azure_managed_hsm"
    GOOGLE_CLOUD_HSM = "google_cloud_hsm"
    GOOGLE_CLOUD_KMS = "google_cloud_kms"
    THALES_LUNA = "thales_luna"
    SAFENET_PROTECTSERVER = "safenet_protectserver"
    UTIMACO_SECURITYSERVER = "utimaco_securityserver"
    SOFTWARE_ONLY = "software_only"


class KeyType(str, Enum):
    """Cryptographic key types."""
    AES_256 = "aes_256"
    RSA_2048 = "rsa_2048"
    RSA_3072 = "rsa_3072"
    RSA_4096 = "rsa_4096"
    ECC_P256 = "ecc_p256"
    ECC_P384 = "ecc_p384"
    ECC_P521 = "ecc_p521"
    ED25519 = "ed25519"
    X25519 = "x25519"
    CHACHA20 = "chacha20"


class KeyUsage(str, Enum):
    """Key usage purposes."""
    ENCRYPT_DECRYPT = "encrypt_decrypt"
    SIGN_VERIFY = "sign_verify"
    KEY_AGREEMENT = "key_agreement"
    KEY_DERIVATION = "key_derivation"
    MASTER_KEY = "master_key"
    DATA_ENCRYPTION_KEY = "data_encryption_key"
    KEY_ENCRYPTION_KEY = "key_encryption_key"


class KeyState(str, Enum):
    """Key lifecycle states."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    COMPROMISED = "compromised"
    DESTROYED = "destroyed"
    PENDING_DELETION = "pending_deletion"
    PENDING_IMPORT = "pending_import"


@dataclass
class KeyMetadata:
    """Cryptographic key metadata."""
    
    key_id: str
    alias: Optional[str]
    key_type: KeyType
    key_usage: List[KeyUsage]
    key_size: int
    state: KeyState
    
    # HSM Information
    hsm_provider: HSMProvider
    hsm_key_id: Optional[str] = None
    hsm_partition: Optional[str] = None
    
    # Lifecycle Management
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    rotation_schedule: Optional[str] = None  # Cron expression
    next_rotation_at: Optional[datetime] = None
    
    # Access Control
    tenant_id: Optional[str] = None
    owner_id: Optional[int] = None
    authorized_users: List[int] = field(default_factory=list)
    authorized_services: List[str] = field(default_factory=list)
    
    # Compliance
    fips_140_2_level: Optional[int] = None
    common_criteria_level: Optional[str] = None
    export_restricted: bool = False
    audit_required: bool = True
    
    # Key Hierarchy
    parent_key_id: Optional[str] = None
    derived_from: Optional[str] = None
    derivation_path: Optional[str] = None
    
    # Metadata
    description: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    custom_attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KeyOperation:
    """Cryptographic operation record."""
    
    operation_id: str
    key_id: str
    operation_type: str  # "encrypt", "decrypt", "sign", "verify", "derive"
    user_id: Optional[int]
    service_id: Optional[str]
    
    # Operation Details
    algorithm: Optional[str] = None
    mode: Optional[str] = None
    padding: Optional[str] = None
    data_size: Optional[int] = None
    
    # Security Context
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # Results
    success: bool = False
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    
    # Timestamps
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Compliance
    audit_logged: bool = False
    compliance_checked: bool = False


class HSMInterface:
    """Base interface for HSM/KMS providers."""
    
    async def generate_key(self, key_type: KeyType, key_usage: List[KeyUsage], **kwargs) -> str:
        """Generate a new cryptographic key."""
        raise NotImplementedError
    
    async def import_key(self, key_material: bytes, key_type: KeyType, **kwargs) -> str:
        """Import key material into HSM."""
        raise NotImplementedError
    
    async def delete_key(self, key_id: str) -> bool:
        """Delete key from HSM."""
        raise NotImplementedError
    
    async def encrypt(self, key_id: str, plaintext: bytes, **kwargs) -> bytes:
        """Encrypt data using HSM key."""
        raise NotImplementedError
    
    async def decrypt(self, key_id: str, ciphertext: bytes, **kwargs) -> bytes:
        """Decrypt data using HSM key."""
        raise NotImplementedError
    
    async def sign(self, key_id: str, data: bytes, **kwargs) -> bytes:
        """Sign data using HSM key."""
        raise NotImplementedError
    
    async def verify(self, key_id: str, data: bytes, signature: bytes, **kwargs) -> bool:
        """Verify signature using HSM key."""
        raise NotImplementedError
    
    async def derive_key(self, master_key_id: str, derivation_data: bytes, **kwargs) -> str:
        """Derive key from master key."""
        raise NotImplementedError
    
    async def get_public_key(self, key_id: str) -> bytes:
        """Get public key for asymmetric key pair."""
        raise NotImplementedError


class AWSCloudHSMInterface(HSMInterface):
    """AWS CloudHSM integration."""
    
    def __init__(self):
        self.cluster_id = settings.HSM_CLUSTER_ID
        self.region = settings.AWS_DEFAULT_REGION
        self.session = boto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=self.region
        )
        self.cloudhsm_client = self.session.client('cloudhsm')
    
    async def generate_key(self, key_type: KeyType, key_usage: List[KeyUsage], **kwargs) -> str:
        """Generate key in AWS CloudHSM."""
        
        try:
            # Map key type to CloudHSM parameters
            key_spec = self._map_key_type_to_aws_spec(key_type)
            
            # Generate key using CloudHSM API
            response = self.cloudhsm_client.create_key(
                ClusterId=self.cluster_id,
                KeySpec=key_spec,
                KeyUsage=self._map_usage_to_aws(key_usage),
                Description=kwargs.get('description', 'WebAgent encryption key')
            )
            
            key_id = response['Key']['KeyId']
            
            logger.info(
                "Key generated in AWS CloudHSM",
                key_id=key_id,
                key_type=key_type.value,
                cluster_id=self.cluster_id
            )
            
            return key_id
            
        except Exception as e:
            logger.error(f"AWS CloudHSM key generation failed: {str(e)}")
            raise
    
    async def encrypt(self, key_id: str, plaintext: bytes, **kwargs) -> bytes:
        """Encrypt using AWS CloudHSM."""
        
        try:
            algorithm = kwargs.get('algorithm', 'AES_GCM')
            
            response = self.cloudhsm_client.encrypt(
                ClusterId=self.cluster_id,
                KeyId=key_id,
                Plaintext=plaintext,
                EncryptionAlgorithm=algorithm
            )
            
            return response['CiphertextBlob']
            
        except Exception as e:
            logger.error(f"AWS CloudHSM encryption failed: {str(e)}")
            raise
    
    async def decrypt(self, key_id: str, ciphertext: bytes, **kwargs) -> bytes:
        """Decrypt using AWS CloudHSM."""
        
        try:
            algorithm = kwargs.get('algorithm', 'AES_GCM')
            
            response = self.cloudhsm_client.decrypt(
                ClusterId=self.cluster_id,
                KeyId=key_id,
                CiphertextBlob=ciphertext,
                EncryptionAlgorithm=algorithm
            )
            
            return response['Plaintext']
            
        except Exception as e:
            logger.error(f"AWS CloudHSM decryption failed: {str(e)}")
            raise
    
    def _map_key_type_to_aws_spec(self, key_type: KeyType) -> str:
        """Map KeyType to AWS CloudHSM key specification."""
        
        mapping = {
            KeyType.AES_256: 'AES_256',
            KeyType.RSA_2048: 'RSA_2048',
            KeyType.RSA_3072: 'RSA_3072',
            KeyType.RSA_4096: 'RSA_4096',
            KeyType.ECC_P256: 'ECC_NIST_P256',
            KeyType.ECC_P384: 'ECC_NIST_P384',
            KeyType.ECC_P521: 'ECC_NIST_P521'
        }
        
        return mapping.get(key_type, 'AES_256')
    
    def _map_usage_to_aws(self, key_usage: List[KeyUsage]) -> str:
        """Map KeyUsage to AWS CloudHSM usage."""
        
        if KeyUsage.ENCRYPT_DECRYPT in key_usage:
            return 'ENCRYPT_DECRYPT'
        elif KeyUsage.SIGN_VERIFY in key_usage:
            return 'SIGN_VERIFY'
        else:
            return 'ENCRYPT_DECRYPT'


class AWSKMSInterface(HSMInterface):
    """AWS KMS integration."""
    
    def __init__(self):
        self.region = settings.AWS_DEFAULT_REGION
        self.session = boto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=self.region
        )
        self.kms_client = self.session.client('kms')
    
    async def generate_key(self, key_type: KeyType, key_usage: List[KeyUsage], **kwargs) -> str:
        """Generate key in AWS KMS."""
        
        try:
            # Map key type to KMS parameters
            key_spec = self._map_key_type_to_kms_spec(key_type)
            key_usage_kms = self._map_usage_to_kms(key_usage)
            
            response = self.kms_client.create_key(
                KeyUsage=key_usage_kms,
                KeySpec=key_spec,
                Description=kwargs.get('description', 'WebAgent encryption key'),
                Tags=[
                    {'TagKey': 'Application', 'TagValue': 'WebAgent'},
                    {'TagKey': 'Environment', 'TagValue': settings.ENVIRONMENT}
                ]
            )
            
            key_id = response['KeyMetadata']['KeyId']
            
            # Create alias if provided
            alias = kwargs.get('alias')
            if alias:
                self.kms_client.create_alias(
                    AliasName=f"alias/webagent-{alias}",
                    TargetKeyId=key_id
                )
            
            logger.info(
                "Key generated in AWS KMS",
                key_id=key_id,
                key_type=key_type.value,
                alias=alias
            )
            
            return key_id
            
        except Exception as e:
            logger.error(f"AWS KMS key generation failed: {str(e)}")
            raise
    
    async def encrypt(self, key_id: str, plaintext: bytes, **kwargs) -> bytes:
        """Encrypt using AWS KMS."""
        
        try:
            encryption_context = kwargs.get('encryption_context', {})
            
            response = self.kms_client.encrypt(
                KeyId=key_id,
                Plaintext=plaintext,
                EncryptionContext=encryption_context
            )
            
            return response['CiphertextBlob']
            
        except Exception as e:
            logger.error(f"AWS KMS encryption failed: {str(e)}")
            raise
    
    async def decrypt(self, key_id: str, ciphertext: bytes, **kwargs) -> bytes:
        """Decrypt using AWS KMS."""
        
        try:
            encryption_context = kwargs.get('encryption_context', {})
            
            response = self.kms_client.decrypt(
                CiphertextBlob=ciphertext,
                EncryptionContext=encryption_context
            )
            
            return response['Plaintext']
            
        except Exception as e:
            logger.error(f"AWS KMS decryption failed: {str(e)}")
            raise
    
    def _map_key_type_to_kms_spec(self, key_type: KeyType) -> str:
        """Map KeyType to AWS KMS key specification."""
        
        mapping = {
            KeyType.AES_256: 'SYMMETRIC_DEFAULT',
            KeyType.RSA_2048: 'RSA_2048',
            KeyType.RSA_3072: 'RSA_3072',
            KeyType.RSA_4096: 'RSA_4096',
            KeyType.ECC_P256: 'ECC_NIST_P256',
            KeyType.ECC_P384: 'ECC_NIST_P384',
            KeyType.ECC_P521: 'ECC_NIST_P521'
        }
        
        return mapping.get(key_type, 'SYMMETRIC_DEFAULT')
    
    def _map_usage_to_kms(self, key_usage: List[KeyUsage]) -> str:
        """Map KeyUsage to AWS KMS usage."""
        
        if KeyUsage.ENCRYPT_DECRYPT in key_usage:
            return 'ENCRYPT_DECRYPT'
        elif KeyUsage.SIGN_VERIFY in key_usage:
            return 'SIGN_VERIFY'
        else:
            return 'ENCRYPT_DECRYPT'


class AzureKeyVaultInterface(HSMInterface):
    """Azure Key Vault integration."""
    
    def __init__(self):
        self.vault_url = settings.AZURE_KEY_VAULT_URL
        self.credential = DefaultAzureCredential()
        self.key_client = KeyClient(vault_url=self.vault_url, credential=self.credential)
    
    async def generate_key(self, key_type: KeyType, key_usage: List[KeyUsage], **kwargs) -> str:
        """Generate key in Azure Key Vault."""
        
        try:
            from azure.keyvault.keys import KeyType as AzureKeyType, KeyOperation
            
            # Map key type to Azure parameters
            azure_key_type = self._map_key_type_to_azure(key_type)
            key_ops = self._map_usage_to_azure(key_usage)
            
            key_name = kwargs.get('alias', f"webagent-key-{uuid.uuid4().hex[:8]}")
            
            key = self.key_client.create_key(
                name=key_name,
                key_type=azure_key_type,
                key_operations=key_ops,
                tags={
                    'application': 'WebAgent',
                    'environment': settings.ENVIRONMENT,
                    'key_type': key_type.value
                }
            )
            
            key_id = key.id
            
            logger.info(
                "Key generated in Azure Key Vault",
                key_id=key_id,
                key_name=key_name,
                key_type=key_type.value
            )
            
            return key_id
            
        except Exception as e:
            logger.error(f"Azure Key Vault key generation failed: {str(e)}")
            raise
    
    async def encrypt(self, key_id: str, plaintext: bytes, **kwargs) -> bytes:
        """Encrypt using Azure Key Vault."""
        
        try:
            from azure.keyvault.keys.crypto import CryptographyClient, EncryptionAlgorithm
            
            crypto_client = CryptographyClient(key_id, credential=self.credential)
            
            algorithm = kwargs.get('algorithm', EncryptionAlgorithm.rsa_oaep)
            
            result = crypto_client.encrypt(algorithm, plaintext)
            
            return result.ciphertext
            
        except Exception as e:
            logger.error(f"Azure Key Vault encryption failed: {str(e)}")
            raise
    
    async def decrypt(self, key_id: str, ciphertext: bytes, **kwargs) -> bytes:
        """Decrypt using Azure Key Vault."""
        
        try:
            from azure.keyvault.keys.crypto import CryptographyClient, EncryptionAlgorithm
            
            crypto_client = CryptographyClient(key_id, credential=self.credential)
            
            algorithm = kwargs.get('algorithm', EncryptionAlgorithm.rsa_oaep)
            
            result = crypto_client.decrypt(algorithm, ciphertext)
            
            return result.plaintext
            
        except Exception as e:
            logger.error(f"Azure Key Vault decryption failed: {str(e)}")
            raise
    
    def _map_key_type_to_azure(self, key_type: KeyType):
        """Map KeyType to Azure Key Vault key type."""
        
        from azure.keyvault.keys import KeyType as AzureKeyType
        
        mapping = {
            KeyType.RSA_2048: AzureKeyType.rsa,
            KeyType.RSA_3072: AzureKeyType.rsa,
            KeyType.RSA_4096: AzureKeyType.rsa,
            KeyType.ECC_P256: AzureKeyType.ec,
            KeyType.ECC_P384: AzureKeyType.ec,
            KeyType.ECC_P521: AzureKeyType.ec
        }
        
        return mapping.get(key_type, AzureKeyType.rsa)
    
    def _map_usage_to_azure(self, key_usage: List[KeyUsage]):
        """Map KeyUsage to Azure Key Vault operations."""
        
        from azure.keyvault.keys import KeyOperation
        
        ops = []
        if KeyUsage.ENCRYPT_DECRYPT in key_usage:
            ops.extend([KeyOperation.encrypt, KeyOperation.decrypt])
        if KeyUsage.SIGN_VERIFY in key_usage:
            ops.extend([KeyOperation.sign, KeyOperation.verify])
        
        return ops if ops else [KeyOperation.encrypt, KeyOperation.decrypt]


class GoogleCloudKMSInterface(HSMInterface):
    """Google Cloud KMS integration."""
    
    def __init__(self):
        self.project_id = settings.GCP_PROJECT_ID
        self.location = 'global'
        self.client = kms.KeyManagementServiceClient()
    
    async def generate_key(self, key_type: KeyType, key_usage: List[KeyUsage], **kwargs) -> str:
        """Generate key in Google Cloud KMS."""
        
        try:
            # Create key ring if it doesn't exist
            key_ring_id = kwargs.get('key_ring_id', 'webagent-keyring')
            key_ring_path = self.client.key_ring_path(self.project_id, self.location, key_ring_id)
            
            try:
                self.client.create_key_ring(
                    request={
                        "parent": f"projects/{self.project_id}/locations/{self.location}",
                        "key_ring_id": key_ring_id
                    }
                )
            except Exception:
                # Key ring already exists
                pass
            
            # Create crypto key
            key_id = kwargs.get('alias', f"webagent-key-{uuid.uuid4().hex[:8]}")
            
            purpose, algorithm = self._map_key_type_to_gcp(key_type, key_usage)
            
            crypto_key = {
                "purpose": purpose,
                "version_template": {
                    "algorithm": algorithm,
                },
                "labels": {
                    "application": "webagent",
                    "environment": settings.ENVIRONMENT
                }
            }
            
            request = {
                "parent": key_ring_path,
                "crypto_key_id": key_id,
                "crypto_key": crypto_key
            }
            
            response = self.client.create_crypto_key(request=request)
            
            key_path = response.name
            
            logger.info(
                "Key generated in Google Cloud KMS",
                key_path=key_path,
                key_type=key_type.value
            )
            
            return key_path
            
        except Exception as e:
            logger.error(f"Google Cloud KMS key generation failed: {str(e)}")
            raise
    
    async def encrypt(self, key_id: str, plaintext: bytes, **kwargs) -> bytes:
        """Encrypt using Google Cloud KMS."""
        
        try:
            response = self.client.encrypt(
                request={
                    "name": key_id,
                    "plaintext": plaintext
                }
            )
            
            return response.ciphertext
            
        except Exception as e:
            logger.error(f"Google Cloud KMS encryption failed: {str(e)}")
            raise
    
    async def decrypt(self, key_id: str, ciphertext: bytes, **kwargs) -> bytes:
        """Decrypt using Google Cloud KMS."""
        
        try:
            response = self.client.decrypt(
                request={
                    "name": key_id,
                    "ciphertext": ciphertext
                }
            )
            
            return response.plaintext
            
        except Exception as e:
            logger.error(f"Google Cloud KMS decryption failed: {str(e)}")
            raise
    
    def _map_key_type_to_gcp(self, key_type: KeyType, key_usage: List[KeyUsage]):
        """Map KeyType and usage to Google Cloud KMS parameters."""
        
        if KeyUsage.ENCRYPT_DECRYPT in key_usage:
            purpose = kms.CryptoKey.CryptoKeyPurpose.ENCRYPT_DECRYPT
            if key_type == KeyType.AES_256:
                algorithm = kms.CryptoKeyVersion.CryptoKeyVersionAlgorithm.GOOGLE_SYMMETRIC_ENCRYPTION
            else:
                algorithm = kms.CryptoKeyVersion.CryptoKeyVersionAlgorithm.RSA_DECRYPT_OAEP_2048_SHA256
        elif KeyUsage.SIGN_VERIFY in key_usage:
            purpose = kms.CryptoKey.CryptoKeyPurpose.ASYMMETRIC_SIGN
            algorithm = kms.CryptoKeyVersion.CryptoKeyVersionAlgorithm.RSA_SIGN_PKCS1_2048_SHA256
        else:
            purpose = kms.CryptoKey.CryptoKeyPurpose.ENCRYPT_DECRYPT
            algorithm = kms.CryptoKeyVersion.CryptoKeyVersionAlgorithm.GOOGLE_SYMMETRIC_ENCRYPTION
        
        return purpose, algorithm


class SoftwareHSMInterface(HSMInterface):
    """Software-only HSM implementation for development/testing."""
    
    def __init__(self):
        self.keys = {}  # In-memory key storage
    
    async def generate_key(self, key_type: KeyType, key_usage: List[KeyUsage], **kwargs) -> str:
        """Generate key in software."""
        
        try:
            key_id = f"soft_key_{uuid.uuid4().hex}"
            
            # Generate key material based on type
            if key_type == KeyType.AES_256:
                key_material = self._generate_aes_key(256)
            elif key_type == KeyType.RSA_2048:
                key_material = self._generate_rsa_key(2048)
            elif key_type == KeyType.ECC_P256:
                key_material = self._generate_ec_key('secp256r1')
            elif key_type == KeyType.ED25519:
                key_material = self._generate_ed25519_key()
            else:
                key_material = self._generate_aes_key(256)  # Default
            
            # Store key
            self.keys[key_id] = {
                'key_material': key_material,
                'key_type': key_type,
                'key_usage': key_usage,
                'created_at': datetime.utcnow()
            }
            
            logger.info(
                "Key generated in software HSM",
                key_id=key_id,
                key_type=key_type.value
            )
            
            return key_id
            
        except Exception as e:
            logger.error(f"Software HSM key generation failed: {str(e)}")
            raise
    
    async def encrypt(self, key_id: str, plaintext: bytes, **kwargs) -> bytes:
        """Encrypt using software HSM."""
        
        try:
            if key_id not in self.keys:
                raise ValueError(f"Key not found: {key_id}")
            
            key_info = self.keys[key_id]
            key_material = key_info['key_material']
            key_type = key_info['key_type']
            
            if key_type == KeyType.AES_256:
                return self._aes_encrypt(key_material, plaintext)
            elif key_type.startswith('RSA'):
                return self._rsa_encrypt(key_material, plaintext)
            else:
                raise ValueError(f"Encryption not supported for key type: {key_type}")
            
        except Exception as e:
            logger.error(f"Software HSM encryption failed: {str(e)}")
            raise
    
    async def decrypt(self, key_id: str, ciphertext: bytes, **kwargs) -> bytes:
        """Decrypt using software HSM."""
        
        try:
            if key_id not in self.keys:
                raise ValueError(f"Key not found: {key_id}")
            
            key_info = self.keys[key_id]
            key_material = key_info['key_material']
            key_type = key_info['key_type']
            
            if key_type == KeyType.AES_256:
                return self._aes_decrypt(key_material, ciphertext)
            elif key_type.startswith('RSA'):
                return self._rsa_decrypt(key_material, ciphertext)
            else:
                raise ValueError(f"Decryption not supported for key type: {key_type}")
            
        except Exception as e:
            logger.error(f"Software HSM decryption failed: {str(e)}")
            raise
    
    def _generate_aes_key(self, key_size: int) -> bytes:
        """Generate AES key."""
        import os
        return os.urandom(key_size // 8)
    
    def _generate_rsa_key(self, key_size: int):
        """Generate RSA key pair."""
        return rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size
        )
    
    def _generate_ec_key(self, curve_name: str):
        """Generate EC key pair."""
        if curve_name == 'secp256r1':
            curve = ec.SECP256R1()
        elif curve_name == 'secp384r1':
            curve = ec.SECP384R1()
        elif curve_name == 'secp521r1':
            curve = ec.SECP521R1()
        else:
            curve = ec.SECP256R1()
        
        return ec.generate_private_key(curve)
    
    def _generate_ed25519_key(self):
        """Generate Ed25519 key pair."""
        return ed25519.Ed25519PrivateKey.generate()
    
    def _aes_encrypt(self, key: bytes, plaintext: bytes) -> bytes:
        """AES-GCM encryption."""
        import os
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)  # 96-bit nonce for GCM
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        
        # Return nonce + ciphertext
        return nonce + ciphertext
    
    def _aes_decrypt(self, key: bytes, ciphertext: bytes) -> bytes:
        """AES-GCM decryption."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        
        # Extract nonce and ciphertext
        nonce = ciphertext[:12]
        encrypted_data = ciphertext[12:]
        
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, encrypted_data, None)
    
    def _rsa_encrypt(self, private_key, plaintext: bytes) -> bytes:
        """RSA encryption using public key."""
        from cryptography.hazmat.primitives import padding as crypto_padding
        
        public_key = private_key.public_key()
        
        # Use OAEP padding
        ciphertext = public_key.encrypt(
            plaintext,
            crypto_padding.OAEP(
                mgf=crypto_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return ciphertext
    
    def _rsa_decrypt(self, private_key, ciphertext: bytes) -> bytes:
        """RSA decryption using private key."""
        from cryptography.hazmat.primitives import padding as crypto_padding
        
        # Use OAEP padding
        plaintext = private_key.decrypt(
            ciphertext,
            crypto_padding.OAEP(
                mgf=crypto_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return plaintext


class EnterpriseKeyManager:
    """
    Enterprise Key Management System
    
    Unified interface for HSM/KMS operations with key lifecycle management,
    audit logging, and compliance enforcement.
    """
    
    def __init__(self):
        self.hsm_interface = self._initialize_hsm_interface()
        self.key_metadata = {}  # Key metadata storage
        self.key_operations_log = []  # Operation audit log
        
    def _initialize_hsm_interface(self) -> HSMInterface:
        """Initialize HSM interface based on configuration."""
        
        provider = HSMProvider(settings.HSM_PROVIDER or "software_only")
        
        if provider == HSMProvider.AWS_CLOUDHSM:
            return AWSCloudHSMInterface()
        elif provider == HSMProvider.AWS_KMS:
            return AWSKMSInterface()
        elif provider == HSMProvider.AZURE_KEY_VAULT:
            return AzureKeyVaultInterface()
        elif provider == HSMProvider.GOOGLE_CLOUD_KMS:
            return GoogleCloudKMSInterface()
        elif provider == HSMProvider.SOFTWARE_ONLY:
            return SoftwareHSMInterface()
        else:
            logger.warning(f"Unsupported HSM provider: {provider}, falling back to software")
            return SoftwareHSMInterface()
    
    async def generate_master_key(
        self,
        tenant_id: Optional[str] = None,
        key_type: KeyType = KeyType.AES_256,
        description: Optional[str] = None
    ) -> str:
        """Generate master encryption key."""
        
        try:
            # Generate key in HSM
            hsm_key_id = await self.hsm_interface.generate_key(
                key_type=key_type,
                key_usage=[KeyUsage.MASTER_KEY, KeyUsage.KEY_ENCRYPTION_KEY],
                alias=f"master-{tenant_id or 'global'}-{uuid.uuid4().hex[:8]}",
                description=description or f"Master key for tenant {tenant_id}"
            )
            
            # Create metadata
            key_id = f"master_{uuid.uuid4().hex}"
            metadata = KeyMetadata(
                key_id=key_id,
                alias=f"master-{tenant_id or 'global'}",
                key_type=key_type,
                key_usage=[KeyUsage.MASTER_KEY, KeyUsage.KEY_ENCRYPTION_KEY],
                key_size=self._get_key_size(key_type),
                state=KeyState.ACTIVE,
                hsm_provider=HSMProvider(settings.HSM_PROVIDER or "software_only"),
                hsm_key_id=hsm_key_id,
                tenant_id=tenant_id,
                description=description,
                fips_140_2_level=self._get_fips_level(),
                audit_required=True,
                tags={
                    'key_class': 'master',
                    'tenant_id': tenant_id or 'global'
                }
            )
            
            self.key_metadata[key_id] = metadata
            
            # Log operation
            await self._log_key_operation(
                operation_type="generate",
                key_id=key_id,
                success=True
            )
            
            logger.info(
                "Master key generated",
                key_id=key_id,
                tenant_id=tenant_id,
                hsm_provider=metadata.hsm_provider.value
            )
            
            return key_id
            
        except Exception as e:
            logger.error(f"Master key generation failed: {str(e)}")
            raise
    
    async def derive_data_encryption_key(
        self,
        master_key_id: str,
        purpose: str,
        key_type: KeyType = KeyType.AES_256
    ) -> str:
        """Derive data encryption key from master key."""
        
        try:
            # Get master key metadata
            if master_key_id not in self.key_metadata:
                raise ValueError(f"Master key not found: {master_key_id}")
            
            master_metadata = self.key_metadata[master_key_id]
            
            # Create derivation data
            derivation_data = f"{purpose}:{key_type.value}:{datetime.utcnow().isoformat()}".encode()
            
            # Derive key in HSM
            hsm_key_id = await self.hsm_interface.derive_key(
                master_key_id=master_metadata.hsm_key_id,
                derivation_data=derivation_data,
                key_type=key_type
            )
            
            # Create metadata for derived key
            key_id = f"dek_{uuid.uuid4().hex}"
            metadata = KeyMetadata(
                key_id=key_id,
                alias=f"dek-{purpose}",
                key_type=key_type,
                key_usage=[KeyUsage.DATA_ENCRYPTION_KEY, KeyUsage.ENCRYPT_DECRYPT],
                key_size=self._get_key_size(key_type),
                state=KeyState.ACTIVE,
                hsm_provider=master_metadata.hsm_provider,
                hsm_key_id=hsm_key_id,
                tenant_id=master_metadata.tenant_id,
                parent_key_id=master_key_id,
                derived_from=master_key_id,
                derivation_path=purpose,
                description=f"Data encryption key for {purpose}",
                fips_140_2_level=master_metadata.fips_140_2_level,
                audit_required=True,
                tags={
                    'key_class': 'dek',
                    'purpose': purpose,
                    'parent_key': master_key_id
                }
            )
            
            self.key_metadata[key_id] = metadata
            
            # Log operation
            await self._log_key_operation(
                operation_type="derive",
                key_id=key_id,
                success=True
            )
            
            logger.info(
                "Data encryption key derived",
                key_id=key_id,
                master_key_id=master_key_id,
                purpose=purpose
            )
            
            return key_id
            
        except Exception as e:
            logger.error(f"Key derivation failed: {str(e)}")
            raise
    
    async def encrypt_data(
        self,
        key_id: str,
        plaintext: bytes,
        user_id: Optional[int] = None,
        encryption_context: Optional[Dict[str, str]] = None
    ) -> bytes:
        """Encrypt data using specified key."""
        
        try:
            # Get key metadata
            if key_id not in self.key_metadata:
                raise ValueError(f"Key not found: {key_id}")
            
            metadata = self.key_metadata[key_id]
            
            # Check key state
            if metadata.state != KeyState.ACTIVE:
                raise ValueError(f"Key is not active: {metadata.state}")
            
            # Check usage authorization
            if not await self._check_key_usage_authorization(key_id, user_id, "encrypt"):
                raise PermissionError("Unauthorized key usage")
            
            # Perform encryption
            ciphertext = await self.hsm_interface.encrypt(
                key_id=metadata.hsm_key_id,
                plaintext=plaintext,
                encryption_context=encryption_context
            )
            
            # Update key usage
            metadata.last_used_at = datetime.utcnow()
            
            # Log operation
            await self._log_key_operation(
                operation_type="encrypt",
                key_id=key_id,
                user_id=user_id,
                data_size=len(plaintext),
                success=True
            )
            
            return ciphertext
            
        except Exception as e:
            await self._log_key_operation(
                operation_type="encrypt",
                key_id=key_id,
                user_id=user_id,
                success=False,
                error_message=str(e)
            )
            logger.error(f"Data encryption failed: {str(e)}")
            raise
    
    async def decrypt_data(
        self,
        key_id: str,
        ciphertext: bytes,
        user_id: Optional[int] = None,
        encryption_context: Optional[Dict[str, str]] = None
    ) -> bytes:
        """Decrypt data using specified key."""
        
        try:
            # Get key metadata
            if key_id not in self.key_metadata:
                raise ValueError(f"Key not found: {key_id}")
            
            metadata = self.key_metadata[key_id]
            
            # Check key state
            if metadata.state != KeyState.ACTIVE:
                raise ValueError(f"Key is not active: {metadata.state}")
            
            # Check usage authorization
            if not await self._check_key_usage_authorization(key_id, user_id, "decrypt"):
                raise PermissionError("Unauthorized key usage")
            
            # Perform decryption
            plaintext = await self.hsm_interface.decrypt(
                key_id=metadata.hsm_key_id,
                ciphertext=ciphertext,
                encryption_context=encryption_context
            )
            
            # Update key usage
            metadata.last_used_at = datetime.utcnow()
            
            # Log operation
            await self._log_key_operation(
                operation_type="decrypt",
                key_id=key_id,
                user_id=user_id,
                data_size=len(ciphertext),
                success=True
            )
            
            return plaintext
            
        except Exception as e:
            await self._log_key_operation(
                operation_type="decrypt",
                key_id=key_id,
                user_id=user_id,
                success=False,
                error_message=str(e)
            )
            logger.error(f"Data decryption failed: {str(e)}")
            raise
    
    async def rotate_key(self, key_id: str) -> str:
        """Rotate encryption key."""
        
        try:
            # Get current key metadata
            if key_id not in self.key_metadata:
                raise ValueError(f"Key not found: {key_id}")
            
            old_metadata = self.key_metadata[key_id]
            
            # Generate new key
            new_hsm_key_id = await self.hsm_interface.generate_key(
                key_type=old_metadata.key_type,
                key_usage=old_metadata.key_usage,
                alias=f"{old_metadata.alias}-rotated-{uuid.uuid4().hex[:8]}"
            )
            
            # Create new key metadata
            new_key_id = f"rotated_{uuid.uuid4().hex}"
            new_metadata = KeyMetadata(
                key_id=new_key_id,
                alias=f"{old_metadata.alias}-rotated",
                key_type=old_metadata.key_type,
                key_usage=old_metadata.key_usage,
                key_size=old_metadata.key_size,
                state=KeyState.ACTIVE,
                hsm_provider=old_metadata.hsm_provider,
                hsm_key_id=new_hsm_key_id,
                tenant_id=old_metadata.tenant_id,
                owner_id=old_metadata.owner_id,
                parent_key_id=old_metadata.parent_key_id,
                description=f"Rotated from {key_id}",
                fips_140_2_level=old_metadata.fips_140_2_level,
                audit_required=True,
                tags={
                    **old_metadata.tags,
                    'rotated_from': key_id,
                    'rotation_date': datetime.utcnow().isoformat()
                }
            )
            
            # Update old key state
            old_metadata.state = KeyState.INACTIVE
            old_metadata.next_rotation_at = None
            
            # Store new key
            self.key_metadata[new_key_id] = new_metadata
            
            # Schedule next rotation
            if old_metadata.rotation_schedule:
                new_metadata.next_rotation_at = self._calculate_next_rotation(
                    old_metadata.rotation_schedule
                )
            
            # Log operation
            await self._log_key_operation(
                operation_type="rotate",
                key_id=key_id,
                success=True
            )
            
            logger.info(
                "Key rotated successfully",
                old_key_id=key_id,
                new_key_id=new_key_id
            )
            
            return new_key_id
            
        except Exception as e:
            logger.error(f"Key rotation failed: {str(e)}")
            raise
    
    async def _check_key_usage_authorization(self, key_id: str, user_id: Optional[int], operation: str) -> bool:
        """Check if user is authorized to use the key."""
        
        if key_id not in self.key_metadata:
            return False
        
        metadata = self.key_metadata[key_id]
        
        # System operations are always allowed
        if user_id is None:
            return True
        
        # Check if user is key owner
        if metadata.owner_id == user_id:
            return True
        
        # Check if user is in authorized users list
        if user_id in metadata.authorized_users:
            return True
        
        # Additional authorization checks would go here
        # (integrate with RBAC system)
        
        return False
    
    async def _log_key_operation(
        self,
        operation_type: str,
        key_id: str,
        user_id: Optional[int] = None,
        success: bool = False,
        error_message: Optional[str] = None,
        data_size: Optional[int] = None
    ) -> None:
        """Log key operation for audit trail."""
        
        operation = KeyOperation(
            operation_id=f"op_{uuid.uuid4().hex}",
            key_id=key_id,
            operation_type=operation_type,
            user_id=user_id,
            data_size=data_size,
            success=success,
            error_message=error_message,
            completed_at=datetime.utcnow()
        )
        
        self.key_operations_log.append(operation)
        
        # In production, this would be written to a secure audit database
        logger.info(
            "Key operation logged",
            operation_id=operation.operation_id,
            operation_type=operation_type,
            key_id=key_id,
            success=success
        )
    
    def _get_key_size(self, key_type: KeyType) -> int:
        """Get key size in bits for key type."""
        
        size_mapping = {
            KeyType.AES_256: 256,
            KeyType.RSA_2048: 2048,
            KeyType.RSA_3072: 3072,
            KeyType.RSA_4096: 4096,
            KeyType.ECC_P256: 256,
            KeyType.ECC_P384: 384,
            KeyType.ECC_P521: 521,
            KeyType.ED25519: 256,
            KeyType.X25519: 256,
            KeyType.CHACHA20: 256
        }
        
        return size_mapping.get(key_type, 256)
    
    def _get_fips_level(self) -> Optional[int]:
        """Get FIPS 140-2 level based on HSM provider."""
        
        provider = HSMProvider(settings.HSM_PROVIDER or "software_only")
        
        fips_levels = {
            HSMProvider.AWS_CLOUDHSM: 3,
            HSMProvider.AZURE_MANAGED_HSM: 3,
            HSMProvider.GOOGLE_CLOUD_HSM: 3,
            HSMProvider.THALES_LUNA: 3,
            HSMProvider.SAFENET_PROTECTSERVER: 3,
            HSMProvider.AWS_KMS: 2,
            HSMProvider.AZURE_KEY_VAULT: 2,
            HSMProvider.GOOGLE_CLOUD_KMS: 1,
            HSMProvider.SOFTWARE_ONLY: None
        }
        
        return fips_levels.get(provider)
    
    def _calculate_next_rotation(self, schedule: str) -> datetime:
        """Calculate next rotation time from cron schedule."""
        
        # This would use a cron parser to calculate the next execution time
        # For now, we'll default to 90 days
        return datetime.utcnow() + timedelta(days=90)


# Global enterprise key manager instance
enterprise_key_manager = EnterpriseKeyManager()