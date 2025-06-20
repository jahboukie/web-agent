from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "WebAgent"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True
    
    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./webagent.db",
        description="Database URL (SQLite for development, PostgreSQL for production)"
    )
    ASYNC_DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./webagent.db",
        description="Async database URL (SQLite for development, PostgreSQL for production)"
    )
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600  # 1 hour
    
    # Security
    SECRET_KEY: str = Field(
        default="your-secret-key-change-this-in-production",
        description="Secret key for JWT tokens"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # AI Services
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4-vision-preview"
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    
    # Browser Automation
    BROWSERBASE_API_KEY: Optional[str] = None
    BROWSERBASE_PROJECT_ID: Optional[str] = None
    DEFAULT_BROWSER: str = "chromium"
    HEADLESS: bool = True
    BROWSER_TIMEOUT: int = 30
    
    # File Storage
    UPLOAD_DIR: str = "uploads"
    SCREENSHOT_DIR: str = "screenshots"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = [".jpg", ".jpeg", ".png", ".pdf", ".txt"]
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_BURST: int = 200
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Monitoring
    SENTRY_DSN: Optional[str] = None
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    
    # Task Execution
    MAX_CONCURRENT_TASKS: int = 10
    TASK_TIMEOUT_SECONDS: int = 1800  # 30 minutes
    MAX_RETRY_ATTEMPTS: int = 3

    # Action Execution
    DISABLE_IMAGES_FOR_EXECUTION: bool = False
    EXECUTION_SCREENSHOT_QUALITY: int = 80  # JPEG quality 1-100

    # HTTP Client Configuration
    HTTP_CLIENT_TIMEOUT_TOTAL: int = 30  # Total timeout in seconds
    HTTP_CLIENT_TIMEOUT_CONNECT: int = 10  # Connection timeout in seconds
    HTTP_CLIENT_TIMEOUT_READ: int = 30  # Read timeout in seconds
    HTTP_CLIENT_CONNECTION_POOL_SIZE: int = 100  # Total connection pool size
    HTTP_CLIENT_CONNECTION_POOL_SIZE_PER_HOST: int = 30  # Per-host connection pool size
    
    # Security Policies
    ENABLE_RATE_LIMITING: bool = True
    REQUIRE_2FA_FOR_SENSITIVE: bool = False
    MAX_SESSION_DURATION_HOURS: int = 24
    
    # Additional environment variables for Docker and initialization
    POSTGRES_DB: Optional[str] = None
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    WEBAGENT_ADMIN_PASSWORD: Optional[str] = None
    WEBAGENT_TEST_PASSWORD: Optional[str] = None
    TRUSTED_HOSTS: Optional[str] = None
    
    # Enterprise Security Configuration
    
    # Zero-Knowledge Encryption
    ENABLE_ZERO_KNOWLEDGE: bool = True
    ZK_KEY_DERIVATION_ITERATIONS: int = 100000
    ZK_ENCRYPTION_ALGORITHM: str = "ChaCha20Poly1305"
    ZK_SIGNING_ALGORITHM: str = "Ed25519"
    
    # HSM/KMS Configuration
    HSM_PROVIDER: Optional[str] = None  # "aws_cloudhsm", "azure_keyvault", "google_hsm"
    HSM_CLUSTER_ID: Optional[str] = None
    AWS_KMS_KEY_ID: Optional[str] = None
    AZURE_KEY_VAULT_URL: Optional[str] = None
    GCP_KMS_PROJECT_ID: Optional[str] = None
    
    # Zero Trust Configuration
    ENABLE_ZERO_TRUST: bool = True
    ZERO_TRUST_POLICY: str = "standard_access"  # "critical_systems", "sensitive_data", "standard_access", "public_access"
    CONTINUOUS_VERIFICATION_INTERVAL: int = 1800  # seconds
    DEVICE_TRUST_REQUIRED: bool = True
    LOCATION_VERIFICATION_REQUIRED: bool = True
    
    # Multi-Factor Authentication
    REQUIRE_MFA: bool = True
    MFA_ISSUER: str = "WebAgent"
    MFA_BACKUP_CODES_COUNT: int = 10
    TOTP_VALIDITY_WINDOW: int = 1  # windows of 30 seconds
    
    # Cloud Security (CSPM)
    ENABLE_CSPM: bool = True
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_DEFAULT_REGION: str = "us-east-1"
    AZURE_CLIENT_ID: Optional[str] = None
    AZURE_CLIENT_SECRET: Optional[str] = None
    AZURE_TENANT_ID: Optional[str] = None
    GCP_PROJECT_ID: Optional[str] = None
    GCP_SERVICE_ACCOUNT_KEY: Optional[str] = None
    
    # Incident Response
    ENABLE_INCIDENT_RESPONSE: bool = True
    INCIDENT_RESPONSE_EMAIL: Optional[str] = None
    SLACK_WEBHOOK_URL: Optional[str] = None
    PAGERDUTY_INTEGRATION_KEY: Optional[str] = None
    AUTO_EXECUTE_PLAYBOOKS: bool = False
    INCIDENT_RETENTION_DAYS: int = 2555  # 7 years

    # SIEM Integration
    ENABLE_SIEM_INTEGRATION: bool = True
    SIEM_INTEGRATION_URL: Optional[str] = None
    SIEM_API_KEY: Optional[str] = None
    SIEM_USERNAME: Optional[str] = None
    SIEM_PASSWORD: Optional[str] = None
    SIEM_PROVIDER: str = "splunk"  # "splunk", "qradar", "microsoft_sentinel", "elastic_security"
    SIEM_BATCH_SIZE: int = 100
    SIEM_BATCH_TIMEOUT: int = 30
    SIEM_RETRY_ATTEMPTS: int = 3

    # Splunk Configuration
    SPLUNK_HEC_TOKEN: Optional[str] = None
    SPLUNK_INDEX: str = "security"

    # QRadar Configuration
    QRADAR_API_VERSION: str = "12.0"

    # Microsoft Sentinel Configuration
    AZURE_LOG_ANALYTICS_WORKSPACE_ID: Optional[str] = None
    AZURE_LOG_ANALYTICS_SHARED_KEY: Optional[str] = None

    # Compliance Framework
    COMPLIANCE_FRAMEWORKS: List[str] = ["SOC2", "GDPR"]
    ENABLE_SOC2_MONITORING: bool = True
    ENABLE_GDPR_COMPLIANCE: bool = True
    ENABLE_HIPAA_COMPLIANCE: bool = False
    ENABLE_FEDRAMP_COMPLIANCE: bool = False
    DATA_RETENTION_DAYS: int = 2555  # 7 years default
    
    # Enterprise SSO
    ENABLE_SSO: bool = False
    OKTA_DOMAIN: Optional[str] = None
    OKTA_CLIENT_ID: Optional[str] = None
    OKTA_CLIENT_SECRET: Optional[str] = None
    AZURE_AD_TENANT_ID: Optional[str] = None
    AZURE_AD_CLIENT_ID: Optional[str] = None
    AZURE_AD_CLIENT_SECRET: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        if not v.startswith(("postgresql://", "postgresql+psycopg2://", "sqlite:///")):
            raise ValueError("Database URL must be PostgreSQL or SQLite")
        return v

    @validator("SECRET_KEY")
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        return v
    
    @validator("ZK_KEY_DERIVATION_ITERATIONS")
    def validate_kdf_iterations(cls, v):
        if v < 100000:
            raise ValueError("Key derivation iterations must be at least 100,000 for security")
        return v
    
    @property
    def is_enterprise_mode(self) -> bool:
        """Check if running in enterprise security mode."""
        return (
            self.ENABLE_ZERO_KNOWLEDGE and
            self.ENABLE_ZERO_TRUST and
            self.REQUIRE_MFA
        )

    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL for migrations"""
        return self.DATABASE_URL

    @property
    def database_url_async(self) -> str:
        """Get asynchronous database URL for runtime"""
        return self.ASYNC_DATABASE_URL


# Global settings instance
settings = Settings()