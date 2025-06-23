"""
Enterprise Input Sanitization and Validation Module

Comprehensive input sanitization using industry-standard libraries
with XSS prevention, SQL injection protection, and data validation.
"""

import base64
import html
import json
import re
from typing import Any
from urllib.parse import quote, unquote

import bleach
import validators
from pydantic import BaseModel, validator

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SanitizationConfig:
    """Configuration for input sanitization."""

    # Allowed HTML tags for rich text content
    ALLOWED_TAGS = [
        "p",
        "br",
        "strong",
        "em",
        "u",
        "ol",
        "ul",
        "li",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "blockquote",
        "code",
        "pre",
        "a",
        "img",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
    ]

    # Allowed HTML attributes
    ALLOWED_ATTRIBUTES = {
        "a": ["href", "title"],
        "img": ["src", "alt", "title", "width", "height"],
        "table": ["class"],
        "th": ["scope"],
        "td": ["colspan", "rowspan"],
        "*": ["class", "id"],
    }

    # Allowed URL protocols
    ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

    # Dangerous patterns for additional filtering
    DANGEROUS_PATTERNS = [
        r"javascript:",
        r"vbscript:",
        r"data:",
        r"file:",
        r"ftp:",
        r"<script",
        r"</script>",
        r"<iframe",
        r"</iframe>",
        r"<object",
        r"</object>",
        r"<embed",
        r"</embed>",
        r"<link",
        r"<meta",
        r"<style",
        r"</style>",
        r"on\w+\s*=",
        r"expression\s*\(",
        r"@import",
        r"exec\s*\(",
        r"eval\s*\(",
        r"setTimeout\s*\(",
        r"setInterval\s*\(",
        r"Function\s*\(",
        r"ActiveXObject",
    ]

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(ALTER|CREATE|DELETE|DROP|EXEC(UTE)?|INSERT|SELECT|UNION|UPDATE)\b)",
        r"(\b(AND|OR)\b.*(=|<|>|\bLIKE\b))",
        r"(\'|\"|;|--|\*/|\*)",
        r"(\b(CHAR|NCHAR|VARCHAR|NVARCHAR)\s*\(\s*\d+\s*\))",
        r"(\b(CAST|CONVERT)\s*\()",
        r"(\bXP_\w+)",
        r"(\bSP_\w+)",
        r"(\bUTL_\w+)",
        r"(\bDBMS_\w+)",
    ]


class InputValidator:
    """Comprehensive input validation."""

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email address format."""
        try:
            return validators.email(email)
        except Exception:
            return False

    @staticmethod
    def validate_url(url: str, allowed_protocols: list[str] = None) -> bool:
        """Validate URL format and protocol."""
        try:
            if not validators.url(url):
                return False

            if allowed_protocols:
                for protocol in allowed_protocols:
                    if url.startswith(f"{protocol}://"):
                        return True
                return False

            return True
        except Exception:
            return False

    @staticmethod
    def validate_ip_address(ip: str) -> bool:
        """Validate IP address format."""
        try:
            return validators.ipv4(ip) or validators.ipv6(ip)
        except Exception:
            return False

    @staticmethod
    def validate_domain(domain: str) -> bool:
        """Validate domain name format."""
        try:
            return validators.domain(domain)
        except Exception:
            return False

    @staticmethod
    def validate_filename(filename: str) -> bool:
        """Validate filename for security."""
        if not filename:
            return False

        # Check for directory traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            return False

        # Check for reserved names (Windows)
        reserved_names = [
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        ]

        if filename.upper().split(".")[0] in reserved_names:
            return False

        # Check for dangerous characters
        dangerous_chars = ["<", ">", ":", '"', "|", "?", "*", "\x00"]
        if any(char in filename for char in dangerous_chars):
            return False

        return True

    @staticmethod
    def validate_json(data: str) -> bool:
        """Validate JSON format."""
        try:
            json.loads(data)
            return True
        except (json.JSONDecodeError, TypeError):
            return False


class InputSanitizer:
    """Comprehensive input sanitization."""

    def __init__(self, config: SanitizationConfig = None):
        self.config = config or SanitizationConfig()
        self.validator = InputValidator()

        # Compile regex patterns for performance
        self._dangerous_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.config.DANGEROUS_PATTERNS
        ]
        self._sql_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.config.SQL_INJECTION_PATTERNS
        ]

    def sanitize_html(self, html_content: str, allow_tags: bool = True) -> str:
        """Sanitize HTML content using bleach."""
        try:
            if not html_content:
                return ""

            if not allow_tags:
                # Strip all HTML tags
                return bleach.clean(html_content, tags=[], strip=True)

            # Clean with allowed tags and attributes
            cleaned = bleach.clean(
                html_content,
                tags=self.config.ALLOWED_TAGS,
                attributes=self.config.ALLOWED_ATTRIBUTES,
                protocols=self.config.ALLOWED_PROTOCOLS,
                strip=True,
            )

            # Additional dangerous pattern filtering
            for pattern in self._dangerous_patterns:
                cleaned = pattern.sub("", cleaned)

            return cleaned

        except Exception as e:
            logger.error(f"HTML sanitization failed: {str(e)}")
            return ""

    def sanitize_text(self, text: str, max_length: int = None) -> str:
        """Sanitize plain text input."""
        try:
            if not text:
                return ""

            # HTML escape
            sanitized = html.escape(text)

            # Remove null bytes and control characters
            sanitized = "".join(
                char
                for char in sanitized
                if ord(char) >= 32 or char in ["\n", "\r", "\t"]
            )

            # Truncate if needed
            if max_length and len(sanitized) > max_length:
                sanitized = sanitized[:max_length]

            return sanitized

        except Exception as e:
            logger.error(f"Text sanitization failed: {str(e)}")
            return ""

    def sanitize_sql_input(self, sql_input: str) -> str:
        """Sanitize input to prevent SQL injection."""
        try:
            if not sql_input:
                return ""

            # Escape single quotes
            sanitized = sql_input.replace("'", "''")

            # Check for SQL injection patterns
            for pattern in self._sql_patterns:
                if pattern.search(sanitized):
                    logger.warning(
                        f"Potential SQL injection attempt detected: {sql_input[:100]}"
                    )
                    raise ValueError("Invalid input detected")

            return sanitized

        except Exception as e:
            logger.error(f"SQL input sanitization failed: {str(e)}")
            raise ValueError("Input sanitization failed")

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe filesystem operations."""
        try:
            if not filename:
                return ""

            # Validate first
            if not self.validator.validate_filename(filename):
                raise ValueError("Invalid filename")

            # Remove dangerous characters
            sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", filename)

            # Limit length
            if len(sanitized) > 255:
                name, ext = (
                    sanitized.rsplit(".", 1) if "." in sanitized else (sanitized, "")
                )
                sanitized = name[:250] + ("." + ext if ext else "")

            return sanitized

        except Exception as e:
            logger.error(f"Filename sanitization failed: {str(e)}")
            return "sanitized_file"

    def sanitize_url(self, url: str) -> str:
        """Sanitize URL input."""
        try:
            if not url:
                return ""

            # Basic validation
            if not self.validator.validate_url(url, self.config.ALLOWED_PROTOCOLS):
                raise ValueError("Invalid URL")

            # URL encode dangerous characters
            sanitized = quote(url, safe=":/?#[]@!$&'()*+,;=")

            return sanitized

        except Exception as e:
            logger.error(f"URL sanitization failed: {str(e)}")
            return ""

    def sanitize_json(self, json_data: str, max_depth: int = 10) -> dict[str, Any]:
        """Sanitize JSON input with depth limiting."""
        try:
            if not json_data:
                return {}

            # Parse JSON
            data = json.loads(json_data)

            # Recursively sanitize values
            return self._sanitize_json_recursive(data, max_depth)

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"JSON sanitization failed: {str(e)}")
            return {}

    def _sanitize_json_recursive(
        self, obj: Any, max_depth: int, current_depth: int = 0
    ) -> Any:
        """Recursively sanitize JSON object values."""
        if current_depth > max_depth:
            return None

        if isinstance(obj, dict):
            return {
                self.sanitize_text(str(k)): self._sanitize_json_recursive(
                    v, max_depth, current_depth + 1
                )
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [
                self._sanitize_json_recursive(item, max_depth, current_depth + 1)
                for item in obj[:100]  # Limit array size
            ]
        elif isinstance(obj, str):
            return self.sanitize_text(obj, max_length=10000)
        elif isinstance(obj, (int, float, bool)) or obj is None:
            return obj
        else:
            return str(obj)

    def detect_malicious_patterns(self, input_data: str) -> list[str]:
        """Detect potentially malicious patterns in input."""
        detected_patterns = []

        try:
            # Check dangerous patterns
            for i, pattern in enumerate(self._dangerous_patterns):
                if pattern.search(input_data):
                    detected_patterns.append(f"dangerous_pattern_{i}")

            # Check SQL injection patterns
            for i, pattern in enumerate(self._sql_patterns):
                if pattern.search(input_data):
                    detected_patterns.append(f"sql_injection_{i}")

            # Check for suspicious encodings
            try:
                decoded = base64.b64decode(input_data)
                if any(
                    pattern.search(decoded.decode("utf-8", errors="ignore"))
                    for pattern in self._dangerous_patterns
                ):
                    detected_patterns.append("base64_encoded_malicious")
            except Exception:
                pass

            # Check for URL encoding
            try:
                decoded = unquote(input_data)
                if decoded != input_data:
                    if any(
                        pattern.search(decoded) for pattern in self._dangerous_patterns
                    ):
                        detected_patterns.append("url_encoded_malicious")
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Malicious pattern detection failed: {str(e)}")

        return detected_patterns


class SanitizedInput(BaseModel):
    """Pydantic model for sanitized input validation."""

    def __init__(self, **data):
        # Sanitize all string fields before validation
        sanitizer = InputSanitizer()

        for field_name, field_value in data.items():
            if isinstance(field_value, str):
                data[field_name] = sanitizer.sanitize_text(field_value)

        super().__init__(**data)


class SecureTextInput(SanitizedInput):
    """Secure text input with validation."""

    text: str
    max_length: int | None = 1000

    @validator("text")
    def validate_text(cls, v, values):
        sanitizer = InputSanitizer()

        # Check for malicious patterns
        patterns = sanitizer.detect_malicious_patterns(v)
        if patterns:
            raise ValueError(f"Malicious patterns detected: {patterns}")

        # Check length
        max_len = values.get("max_length", 1000)
        if len(v) > max_len:
            raise ValueError(f"Text exceeds maximum length of {max_len}")

        return v


class SecureHtmlInput(SanitizedInput):
    """Secure HTML input with sanitization."""

    html: str
    allow_tags: bool = True

    @validator("html")
    def validate_html(cls, v, values):
        sanitizer = InputSanitizer()

        # Sanitize HTML
        allow_tags = values.get("allow_tags", True)
        sanitized = sanitizer.sanitize_html(v, allow_tags)

        return sanitized


class SecureUrlInput(SanitizedInput):
    """Secure URL input with validation."""

    url: str

    @validator("url")
    def validate_url(cls, v):
        validator = InputValidator()
        sanitizer = InputSanitizer()

        # Validate URL format
        if not validator.validate_url(v, SanitizationConfig.ALLOWED_PROTOCOLS):
            raise ValueError("Invalid URL format or protocol")

        # Sanitize URL
        return sanitizer.sanitize_url(v)


class SecureFileInput(SanitizedInput):
    """Secure file input with validation."""

    filename: str
    content_type: str
    size: int

    @validator("filename")
    def validate_filename(cls, v):
        validator = InputValidator()
        sanitizer = InputSanitizer()

        # Validate filename
        if not validator.validate_filename(v):
            raise ValueError("Invalid filename")

        # Sanitize filename
        return sanitizer.sanitize_filename(v)

    @validator("content_type")
    def validate_content_type(cls, v):
        allowed_types = [
            "text/plain",
            "text/csv",
            "application/json",
            "application/pdf",
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
        ]

        if v not in allowed_types:
            raise ValueError(f"Content type {v} not allowed")

        return v

    @validator("size")
    def validate_size(cls, v):
        max_size = getattr(settings, "MAX_FILE_SIZE", 10 * 1024 * 1024)  # 10MB default

        if v > max_size:
            raise ValueError(f"File size {v} exceeds maximum {max_size}")

        return v


# Global sanitizer instance
enterprise_sanitizer = InputSanitizer()


def sanitize_browser_input(input_value: str) -> str:
    """Enhanced sanitization for browser automation inputs."""
    try:
        if not input_value:
            return ""

        # Use comprehensive sanitization instead of basic pattern matching
        sanitized = enterprise_sanitizer.sanitize_text(input_value, max_length=10000)

        # Additional checks for browser automation
        malicious_patterns = enterprise_sanitizer.detect_malicious_patterns(sanitized)
        if malicious_patterns:
            logger.warning(
                f"Malicious patterns detected in browser input: {malicious_patterns}"
            )
            raise ValueError("Potentially unsafe input detected")

        return sanitized

    except Exception as e:
        logger.error(f"Browser input sanitization failed: {str(e)}")
        raise ValueError("Input sanitization failed")


def validate_automation_target(selector: str) -> bool:
    """Validate browser automation target selectors."""
    try:
        if not selector:
            return False

        # Check for dangerous selector patterns
        dangerous_selectors = [
            "javascript:",
            "data:",
            "vbscript:",
            "expression(",
            "eval(",
            "setTimeout(",
            "setInterval(",
            "Function(",
        ]

        selector_lower = selector.lower()
        if any(danger in selector_lower for danger in dangerous_selectors):
            return False

        # Validate CSS selector format (basic)
        if selector.startswith(("script", 'link[rel="stylesheet"]', "meta")):
            return False

        return True

    except Exception:
        return False
